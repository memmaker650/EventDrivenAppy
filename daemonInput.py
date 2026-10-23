import time
import shutil
import os
import io
import sys
import json
import contextlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging

import domain
import gestionDatos

# Nombre fijo: igual en el log tanto si se lanza como script como desde la app.
logger = logging.getLogger("daemonInput")

# Por defecto <proyecto>/datos; se puede cambiar con la variable de entorno EBD_DATOS.
carpeta_datos = Path(os.environ.get("EBD_DATOS", Path(__file__).resolve().parent / "datos"))
carpeta_entrada = carpeta_datos / "input"
carpeta_tratados = carpeta_datos / "tratados"
carpeta_error = carpeta_datos / "error"

fichero = str

# Tipo de operación del fichero -> acción de gestionDatos.ejecutarAccion.
# Se admiten los nombres de evento del catálogo, los de la UI y los del fichero antiguo.
ACCIONES_FICHERO = {
    "AccountCreated": "crear", "crear": "crear",
    "MoneyDeposited": "depositar", "depositar": "depositar",
    "Moneywithdraw": "retirar", "MoneyWithDraw": "retirar", "retirar": "retirar",
    "CardPayment": "pago_tarjeta", "PaymentCard": "pago_tarjeta", "pago_tarjeta": "pago_tarjeta",
    "MoneyTransfer": "transferencia", "transferencia": "transferencia",
    "demandMortgage": "pedir_hipoteca", "DemandMortgage": "pedir_hipoteca", "pedir_hipoteca": "pedir_hipoteca",
    "mortgagePayment": "pago_hipoteca", "MortgagePayment": "pago_hipoteca", "pago_hipoteca": "pago_hipoteca",
    "demandCredit": "pedir_crédito", "DemandCredit": "pedir_crédito", "pedir_crédito": "pedir_crédito",
    "CreditPayment": "pago_crédito", "pago_crédito": "pago_crédito",
    "CloseAccount": "cerrar", "AccountClosed": "cerrar", "cerrar": "cerrar",
}


def _primero(datos, *claves):
    for clave in claves:
        if datos.get(clave) not in (None, ""):
            return datos[clave]
    return None


def _operacion(evento):
    """Operación del fichero -> (tipo, cuenta, kwargs para ejecutarAccion)."""
    tipo = evento.get("event_type")
    datos = evento.get("event_data") or {}
    cuenta = datos.get("account_id") or evento.get("aggregate_id")
    kwargs = dict(
        accion=ACCIONES_FICHERO.get(tipo),
        origen=cuenta,
        cantidad=datos.get("amount"),
        destino=_primero(datos, "To", "destiny"),
        tienda=datos.get("shop"),
        propietario=datos.get("owner"),
        apellidos=datos.get("family_name"),
        doc_id=_primero(datos, "doc_id", "id_doc"),
        email=datos.get("email"),
        address=datos.get("address"),
        city=datos.get("city"),
        nationality=datos.get("nationality"),
        rate=_primero(datos, "interest_Rate", "interest_rate"),
        return_period=_primero(datos, "return_Period", "return_period"),
        dateInicio=_primero(datos, "initialDate", "initial_date", "payment_date"),
    )
    return tipo, cuenta, kwargs


def _mover(ruta, carpeta):
    """Mueve el fichero sin pisar uno con el mismo nombre (añade fecha y hora)."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / os.path.basename(ruta)
    if destino.exists():
        destino = carpeta / f"{destino.stem}_{datetime.now():%Y%m%d-%H%M%S}{destino.suffix}"
    shutil.move(str(ruta), str(destino))
    return destino


@dataclass
class ResultadoOperacion:
    fichero: str
    numero: int
    tipo: str
    cuenta: str
    ok: bool
    mensaje: str

    def linea(self):
        estado = "OK   " if self.ok else "ERROR"
        return f"[{self.fichero} #{self.numero}] {estado} {self.tipo} {self.cuenta}: {self.mensaje}"


@dataclass
class ResumenBatch:
    """Resultado global de un batch: ficheros, operaciones y recálculo de saldos."""
    inicio: datetime = field(default_factory=datetime.now)
    ficheros: list = field(default_factory=list)          # (nombre, ruta destino)
    ficheros_error: list = field(default_factory=list)    # (nombre, motivo)
    operaciones: list = field(default_factory=list)       # ResultadoOperacion
    proyeccion: object = None                             # domain.Projection

    @property
    def tratadas(self):
        return len(self.operaciones)

    @property
    def correctas(self):
        return sum(1 for o in self.operaciones if o.ok)

    @property
    def errores(self):
        return self.tratadas - self.correctas

    @property
    def hay_avisos(self):
        p = self.proyeccion
        return bool(self.errores or self.ficheros_error or (p and (p.skipped or p.loans_without_account)))

    def _linea_saldos(self):
        p = self.proyeccion
        if p is None:
            return "movimientos NO recalculados"
        texto = f"movimientos ({p.processed} eventos, {len(p.skipped)} ignorados"
        if p.loans_without_account:
            texto += f", {len(p.loans_without_account)} préstamos sin cuenta"
        return texto + ")"

    def linea(self):
        """Resumen en una línea para la barra de estado."""
        if not self.ficheros and not self.ficheros_error:
            return f"Batch: sin ficheros pendientes · {self._linea_saldos()}"
        texto = (f"Batch: {self.tratadas} operaciones tratadas, {self.correctas} correctas, "
                 f"{self.errores} en error")
        if self.ficheros_error:
            texto += f", {len(self.ficheros_error)} ficheros ilegibles"
        return f"{texto} · {self._linea_saldos()}"

    def texto(self):
        """Resumen completo (log, consola y ventana de la app)."""
        lineas = [f"===== RESUMEN BATCH {self.inicio:%Y-%m-%d %H:%M:%S} ====="]
        if not self.ficheros and not self.ficheros_error:
            lineas.append(f"Sin ficheros pendientes en {carpeta_entrada}")
        for nombre, destino in self.ficheros:
            lineas.append(f"Fichero tratado: {nombre} -> {destino}")
        for nombre, motivo in self.ficheros_error:
            lineas.append(f"Fichero ilegible: {nombre} -> {carpeta_error} ({motivo})")
        lineas += [
            f"Operaciones tratadas: {self.tratadas}",
            f"  Correctas: {self.correctas}",
            f"  En error:  {self.errores}",
        ]
        if self.operaciones:
            ok = Counter(o.tipo for o in self.operaciones if o.ok)
            ko = Counter(o.tipo for o in self.operaciones if not o.ok)
            lineas.append("Por tipo de operación:")
            for tipo in sorted(set(ok) | set(ko), key=str):
                lineas.append(f"  {str(tipo):<16} {ok[tipo] + ko[tipo]:>3}  (ok {ok[tipo]}, error {ko[tipo]})")
        errores = [o for o in self.operaciones if not o.ok]
        if errores:
            lineas.append("Operaciones en error:")
            lineas += [f"  {o.linea()}" for o in errores]
        movimientos = self._linea_saldos()
        lineas.append(movimientos[0].upper() + movimientos[1:])
        lineas.append("=" * 40)
        return "\n".join(lineas)

    def registrar_en_log(self):
        for linea in self.texto().splitlines():
            logger.info(linea)


class _Recolector:
    """Hace de 'app' para gestionDatos: guarda el último mensaje en vez de pintarlo."""
    def __init__(self):
        self.ultimo = None

    def actualizar_estado(self, mensaje, tipo):
        self.ultimo = (mensaje, tipo)

class MiHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"Nuevo fichero: {event.src_path}")
            print(f"Nuevo fichero: {event.src_path}")
            if event.src_path.endswith(".json"):
                resumen = ProcesadoDatosDemonio().procesar_fichero(event.src_path)
                completar_batch(resumen)

class ProcesadoDatosDemonio():
    aggregate_id = str()
    event_type = str()
    event_data = {}
    account = str()
    amount = float()
    destiny = str()
    owner = str()
    shop = str()
    family_name = str()
    address = str()
    doc_id = str()
    city = str()
    email = str()
    nationality = str()
    mortgage_id = str()
    credit_id = str()
    interest_rate = str()
    return_period = str()
    initial_date = str()

    # Reconstruye accounts/hipotecas desde event_store sin volver a grabar eventos.
    def procesar_EventosDB(self):
        logger.info(f"Procesar Eventos en DB")

        proyeccion = domain.rebuild_read_model()

        logger.info(f"Total Eventos tratados : {proyeccion.processed}, ignorados: {len(proyeccion.skipped)}")
        print(f"Total Eventos tratados : {proyeccion.processed}, ignorados: {len(proyeccion.skipped)}")

        return True

    def procesar_fichero(self, ruta, resumen=None):
        """Ejecuta cada operación del fichero; una operación en error no para las demás."""
        resumen = resumen if resumen is not None else ResumenBatch()
        nombre = os.path.basename(ruta)
        logger.info(f"Procesando fichero {ruta}")

        try:
            with open(ruta, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if not isinstance(datos, list):
                raise ValueError("el fichero debe contener una lista de operaciones")
        except (OSError, ValueError) as e:
            logger.error(f"Fichero {nombre} ilegible, se mueve a {carpeta_error}: {e}")
            resumen.ficheros_error.append((nombre, str(e)))
            _mover(ruta, carpeta_error)
            return resumen

        recolector = _Recolector()
        gDd = gestionDatos.gestionDatos(app=recolector)
        for numero, evento in enumerate(datos, 1):
            resultado = self._ejecutar_operacion(gDd, recolector, nombre, numero, evento)
            resumen.operaciones.append(resultado)
            if resultado.ok:
                logger.info(resultado.linea())
            else:
                logger.warning(resultado.linea())

        destino = _mover(ruta, carpeta_tratados)
        resumen.ficheros.append((nombre, destino))
        logger.info(f"Fin procesado fichero {nombre} -> {destino}")
        return resumen

    def _ejecutar_operacion(self, gDd, recolector, nombre, numero, evento):
        tipo = cuenta = None
        salida = io.StringIO()  # los print() de la lógica de negocio van al log, no a la consola
        try:
            if not isinstance(evento, dict):
                raise ValueError("la operación no es un objeto JSON")
            tipo, cuenta, kwargs = _operacion(evento)
            if kwargs["accion"] is None:
                ok, mensaje = False, f"Tipo de operación desconocido: {tipo}"
            else:
                recolector.ultimo = None
                with contextlib.redirect_stdout(salida):
                    ok = bool(gDd.ejecutarAccion(None, **kwargs))
                mensaje = recolector.ultimo[0] if recolector.ultimo else ("OK" if ok else "Error sin detalle")
        except Exception as e:  # una operación rota no debe parar el resto del fichero
            logger.exception(f"[{nombre} #{numero}] excepción")
            ok, mensaje = False, f"Excepción: {e}"
        for linea in salida.getvalue().splitlines():
            logger.debug(linea)
        return ResultadoOperacion(nombre, numero, tipo, cuenta, ok, mensaje)

    def procesar_json(self, datos):
        logger.info("procesar_json")
        print("procesar_json")

        self.aggregate_id = datos.get("aggregate_id")
        self.event_type = datos.get("event_type") 

        
        self.event_data = datos.get("event_data", {})
        self.account = self.event_data.get("account")
        self.amount = float(self.event_data.get("amount", 0))
        self.owner = self.event_data.get("owner")
        self.destiny = self.event_data.get("destiny")

        print("FIN procesar_json")

    def procesar_json_hypCred(self, datos):
        logger.info("procesar_json hyp_Cred")
        print("procesar_json hyp_Cred")


        self.mortgage_id = datos.get("account")
        self.amount = float(datos.get("amount", 0))
        self.PaymentDate = datos.get("payment_date")
        print("Amount:", self.amount, " PayD: ", self.PaymentDate)

        return self.amount, self.PaymentDate

    def leerDatosJSON(self, input):
        logger.info("LEer_JSON hyp_Cred")
        return json.loads(input)

def procesar_carpeta_entrada():
    """Procesa todos los .json pendientes de la carpeta de entrada (sin recalcular saldos)."""
    resumen = ResumenBatch()
    carpeta = Path(carpeta_entrada)
    carpeta.mkdir(parents=True, exist_ok=True)
    for ruta in sorted(carpeta.glob("*.json")):
        ProcesadoDatosDemonio().procesar_fichero(ruta, resumen)
    return resumen


def completar_batch(resumen):
    """Recalcula saldos desde los eventos y deja el resumen global en el log."""
    resumen.proyeccion = domain.rebuild_read_model()
    resumen.registrar_en_log()
    return resumen


def ejecutar_batch():
    """Batch completo: ficheros de entrada + recálculo de saldos + resumen en el log."""
    return completar_batch(procesar_carpeta_entrada())


def configurar_log():
    """Mismo fichero de log que la app (log/EbAPy_AAAAMMDD.log); EBD_LOG cambia la carpeta.
    Además, las líneas de este módulo (operaciones y resumen) salen por consola."""
    carpeta = Path(os.environ.get("EBD_LOG", Path(__file__).resolve().parent / "log"))
    carpeta.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=carpeta / f"EbAPy_{datetime.now():%Y%m%d}.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s -  %(message)s",
        force=True,
    )
    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(consola)


if __name__ == "__main__":
    # python daemonInput.py            -> procesa lo pendiente y se queda vigilando la carpeta
    # python daemonInput.py --una-vez  -> procesa lo pendiente y termina
    configurar_log()

    for carpeta in (carpeta_entrada, carpeta_tratados, carpeta_error):
        carpeta.mkdir(parents=True, exist_ok=True)

    with contextlib.redirect_stdout(io.StringIO()):
        resumen = procesar_carpeta_entrada()
    completar_batch(resumen)

    if "--una-vez" in sys.argv:
        sys.exit(1 if resumen.errores or resumen.ficheros_error else 0)

    observer = Observer()
    observer.schedule(MiHandler(), str(carpeta_entrada), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
