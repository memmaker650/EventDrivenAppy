import os
import logging
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta
from email_validator import validate_email, EmailNotValidError

import database
import commands 
import domain
import hypotekas
import daemonInput

logger = logging.getLogger(__name__)

class gestionDatos():
    def __init__(self, app=None):
        self.app = app
        self.manager = hypotekas.HipotecaManager()

    def _actualizar_estado(self, mensaje, tipo):
        if self.app is not None:
            self.app.actualizar_estado(mensaje, tipo)

    def initBusiness(self):
        database.init_db()
        return f"ACC-{database.loadMaxAccountID()+1:03d}"

    def load_accounts(self):
        return database.load_accounts()   

    def load_accountInfo(self, cuentaSelec):
        return database.load_accountInfo(cuentaSelec)    

    def cargaEventosCompletos(self, cuentaSelec):
        return database.load_eventsCuenta(cuentaSelec)

    def domainAccount(self, account):
        return domain.load_account(account)  

    def traer_listaNacionalidades(self):
        return database.traer_listaNacionalidades()

    def validar_email(email: str) -> tuple[bool, str]:
        try:
            info = validate_email(email, check_deliverability=False)
            return True, info.normalized
        except EmailNotValidError as e:
            return False, str(e)

    def create_account(self, widget, id_input, ow_input, family=None, idcardnumber=None, email=None, address=None, city=None, nationality=None, desde_eventos=False):
        logging.info("Dentro de create_account.")

        print("Crear cuenta, Email: ", email)
        print("Crear cuenta, City: ", city)
        print("Crear cuenta, Nation: ", nationality)

        if not desde_eventos:
            campos = {
                "NOMBRE": ow_input,
                "APELLIDOS": family,
                "DNI": idcardnumber,
                "EMAIL":email,
                "DIRECCIÓN": address,
                "CIUDAD": city,
                "NACIONALIDAD": nationality
                }

            for nombre, valor in campos.items():
                if valor is None or valor == "":
                    self._actualizar_estado(f"Error!!! Cuenta NO creada, {nombre} NO rellenado.", "Error")
                    return False
        elif not ow_input:
            self._actualizar_estado("Error!!! Cuenta NO creada, NOMBRE NO rellenado.", "Error")
            return False

        # Alta desde la UI o un fichero: se registra el evento. Desde eventos ya existe.
        if not desde_eventos:
            cmd = commands.CreateAccount(
                id_input,
                ow_input,
                family or "",
                idcardnumber or "",
            )
            domain.handle_create_account(cmd)

        flag = database.crearCuenta(
            id_input,
            ow_input,
            family or "",
            idcardnumber or "",
            email or "",
            address or "",
            city or "",
            nationality or "",
        )

        if flag:
            self._actualizar_estado("Cuenta creada", "OK")
            logger.info("Cuenta creada")
        else:
            self._actualizar_estado("ERROR ! Cuenta NO CREADA", "Error")
            logger.error("ERROR ! Cuenta NO CREADA")
        return flag

    def create_account_block(self, id_input, ow_input):
        logging.info("Dentro de create_account_block.")

        if isinstance(ow_input, str):
            owner = ow_input
        else:
            if ow_input is not None:
                owner = ow_input.value
            else:
                owner = "Desconocido"

        print("Owner: ", owner)
        print("ACC-id: ", id_input)

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            print("Debe indicar un nombre")
            return

        self.account_id = id_input  

        flag = database.crearCuenta(self.account_id, owner)

        if flag:
            self._actualizar_estado("Cuenta creada", "OK") 
        else:
            self._actualizar_estado("ERROR ! Cuenta NO CREADA", "Error")   

    def ejecutarAccion(self, widget, accion, origen, cantidad, destino=None, tienda=None, propietario=None, apellidos=None, doc_id=None, email=None, address=None, city=None, nationality=None, mortgage_id = None, credit_id = None, return_period = None, rate=None, dateInicio=None):
        logging.info("into de ejecutarAccion.")
        print("into de ejecutarAccion.")
        # print("into de ejecutarAccion.")
        # print("------------------------------")
        # print("Acció: ", accion.value)
        # print("Origen: ", origen.value)
        # print("Cantidad: ", cantidad.value)
        print("Destino: ", destino)

        # self.account_id = self.account_selector.value

        # True si el evento se guardó en BD; cada rama informa en la UI.
        resultado = False

        if accion == "crear" or accion == "AccountCreated":
            if propietario == "":
                self._actualizar_estado("Introducir Nombre Titular.", "Error")
            else:
                resultado = self.create_account(
                    None,
                    origen,
                    propietario,
                    apellidos,
                    doc_id,
                    email,
                    address,
                    city,
                    nationality,
                    desde_eventos=(accion == "AccountCreated"),
                )

        elif accion == "depositar" or accion == "MoneyDeposited":
            print("Jump-2_handle_deposit")
            cmd = commands.DepositMoney(
                origen,
                cantidad
            )

            resultado = self._informar(domain.handle_deposit(cmd), f"Depósito de {cantidad} € registrado en {origen}")

        elif accion == "retirar" or accion == "Moneywithdraw":
            print("Jump-2_handle_withdraw")
            cmd = commands.MoneyWithDraw(
                origen,
                cantidad
            )

            resultado = self._informar(domain.handle_withdraw(cmd), f"Retirada de {cantidad} € registrada en {origen}")

        elif accion == "pedir_hipoteca" or accion == "demandMortgage":
            print("Jump-2_handle_DemandMortgage")
            resultado = self._pedir_prestamo(origen, cantidad, rate, return_period, dateInicio, credito=0)

        elif accion == "pago_hipoteca" or accion == "mortgagePayment":
            print("Jump-2_handle_MortgagePayment")

            hyp_id = database.buscar_hypoteka_asociadaCuenta(origen)
            print("hyp_id: ", hyp_id)
            if not hyp_id:
                self._actualizar_estado("No hay hipoteca asociada", "Error")
            else:
                cmd = commands.MortgagePayment(
                    hyp_id[0],
                    cantidad,
                    dateInicio or None  # sin fecha indicada, el pago queda sin fecha
                )

                resultado = self._informar(domain.handle_mortgagePayment(cmd), f"Pago de {cantidad} € registrado en la hipoteca {hyp_id[0]}")

        elif accion == "pedir_crédito" or accion == "demandCredit":
            print("Jump-2_handle_DemandCredit")
            resultado = self._pedir_prestamo(origen, cantidad, rate, return_period, dateInicio, credito=1)

        elif accion == "pago_crédito" or accion == "CreditPayment":
            print("Jump-2_handle_CreditPayment")

            credit_id = database.buscar_credito_asociadaCuenta(origen)
            if not credit_id:
                self._actualizar_estado("No hay crédito asociado", "Error")
            else:
                cmd = commands.CreditPayment(
                    credit_id[0],
                    cantidad,
                    dateInicio or None  # sin fecha indicada, el pago queda sin fecha
                )

                resultado = self._informar(domain.handle_CreditPayment(cmd), f"Pago de {cantidad} € registrado en el crédito {credit_id[0]}")

        elif accion == "transferencia" or accion == "MoneyTransfer":
            print("Jump-2_handle_MoneyTransfer")
            cmd = commands.TransferMoney(
                origen,
                cantidad,
                destino
            )

            resultado = self._informar(domain.handle_moneyTransfer(cmd), f"Transferencia de {cantidad} € de {origen} a {destino} registrada")

        elif accion == "pago_tarjeta" or accion == "CardPayment":
            print("Jump-2_handle_CardPayment")
            cmd = commands.CardPayment(
                origen,
                cantidad,
                tienda
            )

            resultado = self._informar(domain.handle_CardPayment(cmd), f"Pago con tarjeta de {cantidad} € en {tienda} registrado en {origen}")

        elif accion == "cerrar" or accion == "CloseAccount":
            cmd = commands.CloseAccount(
                origen
            )

            resultado = self._informar(domain.handle_close_account(cmd), f"Cierre de la cuenta {origen} registrado")

        # self.refresh_balance()

        print("FIN de ejecutarAccion.")
        return resultado

    def _informar(self, guardado, mensaje_ok):
        """Mensaje verde si save_event confirmó la inserción; rojo con el error si no."""
        if guardado and guardado.get("ok"):
            self._actualizar_estado(mensaje_ok, "OK")
            return True
        detalle = guardado.get("mensaje") if guardado else "sin respuesta"
        self._actualizar_estado(f"ERROR al guardar en BD: {detalle}", "Error")
        return False

    # Hipoteca (credito=0) o crédito (credito=1): evento + fila en hipotecas con el mismo id y fecha.
    def _pedir_prestamo(self, origen, cantidad, rate, return_period, dateInicio, credito):
        if not origen:
            self._actualizar_estado("No hay cuenta asociada", "Error")
            return False

        # La FK hipotecas -> accounts rechazaría el préstamo: avisar antes de emitir el evento.
        if not database.load_accountInfo(origen):
            self._actualizar_estado(f"La cuenta {origen} no existe", "Error")
            return False

        # Validar todo antes de emitir el evento.
        try:
            anios = int(return_period)
        except (TypeError, ValueError):
            self._actualizar_estado("Periodo de retorno (AÑOS) no válido", "Error")
            return False

        try:
            float(str(rate).replace(",", "."))
            float(str(cantidad).replace(",", "."))
        except ValueError:
            self._actualizar_estado("Tasa de interés o cantidad no válida", "Error")
            return False

        inicio = datetime.fromisoformat(dateInicio) if dateInicio else datetime.now()
        fecha_fin = inicio + relativedelta(years=anios)

        if credito:
            prestamo_id = database.generar_id_credito()
            cmd = commands.DemandCredit(origen, prestamo_id, rate, cantidad, anios, inicio.isoformat(timespec='seconds'))
            guardado = domain.handle_demandCredit(cmd)
            mensaje = f"Crédito {prestamo_id} de {cantidad} € registrado en {origen}"
        else:
            prestamo_id = database.generar_id_hypoteka()
            cmd = commands.DemandMortgage(origen, prestamo_id, rate, cantidad, anios, inicio.isoformat(timespec='seconds'))
            guardado = domain.handle_demandMortgage(cmd)
            mensaje = f"Hipoteca {prestamo_id} de {cantidad} € registrada en {origen}"

        if not guardado.get("ok"):
            return self._informar(guardado, mensaje)

        self.manager.crear_hipoteca(origen, cantidad, rate, inicio, fecha_fin, credito, hipoteca_id=prestamo_id)
        return self._informar(guardado, mensaje)
    
    def gestionCuentaAlDia(self, accion, cantidad):
        logging.info("into de gestion Cuenta Al Dia.")
        print("into de gestion Cuenta Al Dia.")

        if accion.value == "crear":
            self.create_account()

        elif accion.value == "depositar":
            print("Jump-2_handle_deposit")
 
        elif accion.value == "retirar":
            print("Jump-2_handle_withdraw")


        elif accion.value == "transferencia":
            print("Jump-2_handle_Transfer")

        elif accion.value == "cerrar":
            print("Jump-2_handle_Transfer")

    # Método para calcular a partir de los eventos que la tabla ACCOUNTS está al día.
    #--------------------------------------------------------------------------------------
    # Las reglas de saldo viven solo en domain.py; aquí no se graba ningún evento.
    def calculoEventosACuenta(self, widget):
        logger.info("Calculo Eventos A Cuenta.")

        try:
            proyeccion = domain.rebuild_read_model()
        except sqlite3.Error as e:
            logger.error(f"Error guardando la proyección: {e}")
            self.label_info = f"ERROR tratamiento en bloque: {e}"
            self._actualizar_estado(self.label_info, "Error")
            return None

        self.label_info = (
            f"TERMINADO TRATAMIENTO EN BLOQUE !! {proyeccion.processed} eventos"
            f", {len(proyeccion.skipped)} ignorados"
        )
        if proyeccion.loans_without_account:
            self.label_info += f", {len(proyeccion.loans_without_account)} préstamos sin cuenta"
        logger.info(self.label_info)
        avisos = proyeccion.skipped or proyeccion.loans_without_account
        self._actualizar_estado(self.label_info, "warning" if avisos else "OK")
        return proyeccion

    def listar_hypotecasCreditos_asociados(self, origen, tipo):
        if tipo == "hip":
            return database.listar_hypotecasCreditos_asociados(origen, 0)
        else: 
            return database.listar_hypotecasCreditos_asociados(origen, 1)

    def traer_Info_CreditoHypoteka(self, hip_id):
        logging.info("Trer info completa: pagos Hipoteca.")

        info = database.obtenerInfoCreditoHypoteka(hip_id)
        return info

    def traer_EventosPago_CreditoHypoteka(self, hip_id, tipo):
        logging.info("Trer info completa: pagos Hipoteca.")

        info = database.load_eventsOfType(hip_id, tipo)
        processJSON = daemonInput.ProcesadoDatosDemonio()
        resultArray = []
        for inf in info:
            dataJSON = processJSON.leerDatosJSON(inf[2])
            resultArray.append(processJSON.procesar_json_hypCred(dataJSON))
        
        print("resultArray:", resultArray)
        return resultArray

    # Método para lanzar Batch tratamiento Eventos y actualizar DB si necesario.
    #--------------------------------------------------------------------------------------
    def lanzar_BatchTratarEventos(self, widget):
        logger.info("Dentro Batch Tratar Eventos Update DB")

        return self.calculoEventosACuenta(widget) is not None