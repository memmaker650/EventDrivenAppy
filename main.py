import sys
import os
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from toga.colors import RED, BLUE, GREEN, ORANGE, YELLOW
from toga import Icon
import logging
from pathlib import Path
from datetime import datetime

from plyer import notification

fecha = datetime.now().strftime("%Y%m%d")

import gestionDatos

print("Arrancando aplicación...")

class EventSourcingApp(toga.App):
    estadoApp = str
    estadoTexto = str
    action_selector = toga.Selection()
    boton_execute = False
    operationSelected = ""
    NationSelected = ""
    listaCredHyp = []
    cuenta = ["", "", "", "", ""]
    EventosCuenta = [["", "", "", ""]]
    dataCredHyp = ["", "", "", "", "", "", "", ""]
    dataEventosPagosHypCred = []
    
    # Contructor de la clase de la GUI
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.estadoApp = "info"
        self.estadoTexto = "Inicial"
        self.gD = gestionDatos.gestionDatos(app=self)

    def refrescar_cuentas(self):
        self.account_input.value = self.gD.initBusiness()
        print("Account_id refreshed: ", self.account_input.value)
        cuentas = self.gD.load_accounts()

        # Recargar sin perder la cuenta que el usuario tenía elegida.
        for selector in (self.account_selector, self.transfer_account_selector):
            seleccionada = selector.value
            selector.items = cuentas
            if seleccionada in cuentas:
                selector.value = seleccionada

    def account_changed(self, widget):  
        logging.info("Dentro de Account_Changed")

        self.account_id = widget.value

    def account_changed_CuentaInfo(self, widget):
        logging.info("Dentro de Account_Changed")

        # Al cargar el selector salta on_change antes de que existan las tablas.
        if not hasattr(self, "tablaEventos"):
            return

        self.account_id = widget.value

        info = self.gD.load_accountInfo(widget.value)
        self.tabla_cuenta.data = [tuple(info)] if info else []

        self.eventosCuenta = self.gD.cargaEventosCompletos(widget.value) or []
        self.tablaEventos.data = [
            (evento[0], evento[1], evento[2], evento[3])
            for evento in self.eventosCuenta
        ]

    def check_eventos_cuentas(self, widget):
        self.gD.calculoEventosACuenta(widget)
        # Refrescar la cuenta mostrada con el saldo recalculado.
        if self.cuentas_selector.value:
            self.account_changed_CuentaInfo(self.cuentas_selector)

    def info_account_changed(self, widget):
        logging.info("Dentro de info_account_changed")

        self.account_id = widget.value
        # Al cambiar de cuenta, recargar la lista de hipotecas/créditos.
        if hasattr(self, "Lista_elementos"):
            self.type_op_changed(self.hyp_cred)

    def type_op_changed(self, widget):
        logging.info("Dentro de type_op_Changed")

        if widget.value == "Hipoteca":
            self.operationSelected = "hip"
        else:
             self.operationSelected = "cre"

        # on_change salta al crear el selector, antes de que exista la lista.
        if not hasattr(self, "Lista_elementos"):
            return

        self.listaCredHyp = self.gD.listar_hypotecasCreditos_asociados(self.account_id, self.operationSelected)
        self.Lista_elementos.items = self.listaCredHyp

    def negocioTraerDatosCredHipotecas(self, widget):
        id = widget.value

        self.tabla_superior.data.clear()
        self.tabla_inferior.data.clear()
        # Lista vacía (cuenta sin hipotecas/créditos): nada que mostrar.
        if not id:
            return

        tipo_pago = "CreditPayment" if self.operationSelected == "cre" else "mortgagePayment"
        self.dataEventosPagosHypCred = self.gD.traer_EventosPago_CreditoHypoteka(id, tipo_pago)
        self.dataCredHyp = self.gD.traer_Info_CreditoHypoteka(id)
        print("Datos Hipoteca: ", self.dataCredHyp)
        total = 0

        for dataHC in self.dataEventosPagosHypCred:
            self.tabla_superior.data.append(
                [
                    dataHC[0],
                    dataHC[1],
                ]
            )
            total += dataHC[0]
        self.tabla_superior.data.append(
                [
                    total,
                    "TOTAL",
                ]
        )

        self.tabla_inferior.data.append(
            [
                self.dataCredHyp[1],
                self.dataCredHyp[2],
                self.dataCredHyp[3],
                self.dataCredHyp[4],
                self.dataCredHyp[5],
                self.dataCredHyp[6],
                self.dataCredHyp[7]
            ]
        )

    def action_changed(self, widget):
        print("Dentro de Action_Changed")
        logging.info("Dentro de Action_Changed")

        accion = widget.value

        # Campos (etiqueta + entrada) que necesita cada acción; crear y cerrar no necesitan ninguno.
        campos_por_accion = {
            "depositar": (self.amount_box,),
            "retirar": (self.amount_box,),
            "pago_hipoteca": (self.amount_box,),
            "pago_crédito": (self.amount_box,),
            "pedir_hipoteca": (self.amount_box, self.rate_box, self.years_box),
            "pedir_crédito": (self.amount_box, self.rate_box, self.years_box),
            "pago_tarjeta": (self.amount_box, self.shop_box),
            "transferencia": (self.amount_box, self.label_destino, self.transfer_account_selector),
        }
        visibles = campos_por_accion.get(accion, ())

        for campo in (self.amount_box, self.rate_box, self.years_box, self.shop_box,
                      self.label_destino, self.transfer_account_selector):
            campo.style.visibility = "visible" if campo in visibles else "hidden"

        # En macOS plyer necesita pyobjus; sin él la notificación no debe romper la UI.
        try:
            notification.notify(
                title="Mi aplicación",
                message="Tienes una nueva tarea pendiente",
                app_name="EventBasedApPy",
                timeout=10
            )
        except NotImplementedError as e:
            logging.warning(f"Notificación no disponible: {e}")

    def cambiar_nacionalidad(self, widget):
        print("Nacionalidad Select: ", widget.value)  
        self.NationSelected = widget.value 
        
    def actualizar_estado(self, texto, estado):
        logging.info("Dentro actualizar_estado")

        self.estadoApp = estado
        self.estadoTexto = texto

        if self.estadoApp == "info" or self.estadoApp == "Info":
            self.label_info.text = self.estadoTexto
            self.label_info.style.color = BLUE
        elif self.estadoApp == "Error" or self.estadoApp == "error":
            self.label_info.text = self.estadoTexto
            self.label_info.style.color = RED
        elif self.estadoApp == "cuidado" or self.estadoApp == "warning":
            self.label_info.text = self.estadoTexto
            self.label_info.style.color = YELLOW
        elif self.estadoApp == "ok" or self.estadoApp == "OK" or self.estadoApp == "Ok":
            self.label_info.text = self.estadoTexto
            self.label_info.style.color = GREEN

        # Refresco los datos tras creación cuenta.
        self.refrescar_cuentas()    

    def limpiar_formulario(self):
        for campo in (self.owner_input, self.family_name_input, self.doc_id_input,
                      self.email_input, self.address_input, self.city_input):
            campo.value = ""
        self.nationality_selection.value = self.nationality_selection.items[0].value

    def crear_cuenta(self, widget):
        creada = self.gD.create_account(widget, self.account_input.value, self.owner_input.value, self.family_name_input.value, self.doc_id_input.value, self.email_input.value, self.address_input.value, self.city_input.value, self.nationality_selection.value)
        if creada:
            self.limpiar_formulario()

    def ejecutar(self, widget):
        accion = self.action_selector.value
        ok = self.gD.ejecutarAccion(
            widget,
            accion=accion,
            origen=self.account_selector.value,
            cantidad=self.amount_input.value,
            destino=self.transfer_account_selector.value,
            tienda=self.shop_input.value,
            propietario=self.owner_input.value,
            apellidos=self.family_name_input.value,
            doc_id=self.doc_id_input.value,
            email=self.email_input.value,
            address=self.address_input.value,
            city=self.city_input.value,
            nationality=self.nationality_selection.value,
            return_period=self.yearsReturn.value,
            rate=self.interest_rate.value,
        )
        if ok and accion == "crear":
            self.limpiar_formulario()

    def _campo(self, texto, entrada):
        """Etiqueta + entrada en una fila; se muestra/oculta como un bloque."""
        return toga.Box(
            children=[toga.Label(texto, style=Pack(width=170, margin_top=4)), entrada],
            style=Pack(direction=ROW, margin_left=10, margin_top=2, margin_bottom=2),
        )

    @staticmethod
    def mensajeUsuario(self, mensaje, color):
        self.label_info.text = mensaje
        self.label_info.style.color = color

        return True

    def startup(self):
        logging.info("Dentro startup")
        
        # Inicio la BDD y operaciones iniciales
        self.account_id = self.gD.initBusiness()

        self.titulo = toga.Label(
            "EggBank - Operaciones por eventos.",
            style=Pack(margin=10)
            )
        self.Titulo2 = toga.Label(
            "Datos cliente",
            style=Pack(margin=10)
            )
        name_box = toga.Box(style=Pack(direction=ROW, margin=10))

        self.owner_input = toga.TextInput(
            placeholder="Nombre",
            style=Pack(flex=1, margin_right=5)
        )

        self.family_name_input = toga.TextInput(
            placeholder="Apellidos",
            style=Pack(flex=1, margin_left=5)
        )

        name_box.add(self.owner_input)
        name_box.add(self.family_name_input)

        self.doc_id_input = toga.TextInput(
            placeholder="Documento de identidad",
            style=Pack(margin=10)
        )

        self.email_input = toga.TextInput(
            placeholder="e-mail",
            style=Pack(margin=10)
        )

        address_box = toga.Box(style=Pack(direction=ROW, margin=10))

        self.address_input = toga.TextInput(
            placeholder="Dirección",
            style=Pack(flex=2, margin_right=5)
        )

        self.city_input = toga.TextInput(
            placeholder="Ciudad",
            style=Pack(flex=1, margin_left=5)
        )

        address_box.add(self.address_input)
        address_box.add(self.city_input)

        self.nationality_selection = toga.Selection(
            items=[],
            style=Pack(margin=10),
            on_change=self.cambiar_nacionalidad
        )
        self.nationality_selection.items = self.gD.traer_listaNacionalidades()

        self.NationSelected = self.nationality_selection.items[0]
        print("Previo Crear cuenta: ", self.NationSelected.value)

        self.account_input = toga.TextInput(
            value=self.account_id,
            placeholder="Número de cuenta",
            style=Pack(margin=10)
        )

        self.label_info = toga.Label("Inicial")

        create_btn = toga.Button(
            "Crear cuenta",
            on_press=self.crear_cuenta
        )   

        btn_hypotekas = toga.Button(
            "Info Hipotecas",
            style=Pack(width=200),
            background_color="green",
            on_press=self.ventana_infoHipoteca)

        btn_izquierdo = toga.Button(
            "Batch Tratar Eventos",
            style=Pack(width=200),
            background_color = "blue",
            on_press=self.gD.lanzar_BatchTratarEventos
        )

        contenedor_botonhyp = toga.Box(
            children=[
                btn_izquierdo,
                toga.Box(style=Pack(flex=1)),
                btn_hypotekas
                ],
            style=Pack(direction=ROW, margin=10),
        )

        self.separador = toga.Box(
            style=Pack(
                height=1,
                background_color="#C0C0C0",
                margin_top=5,
                margin_bottom=5
            )
        )

        self.origen_label = toga.Label(
            "Origen :",
            style=Pack(margin=10)
            )
        self.account_selector = toga.Selection(
            items=[],
            on_change=self.account_changed
        )
        self.account_selector.items = self.gD.load_accounts()

        self.accion_label = toga.Label(
            "Acción Tipo Evento :",
            style=Pack(margin=10)
            )
        self.action_selector = toga.Selection(
            items=["crear", "depositar", "retirar", "transferencia", "pago_tarjeta", "pedir_hipoteca", "pago_hipoteca", "pedir_crédito", "pago_crédito", "cerrar"],
            on_change=self.action_changed
        )

        # Cantidad
        self.amount_input = toga.TextInput(
            placeholder="Cantidad",
            style=Pack(width=200)
        )

        # Tienda
        self.shop_input = toga.TextInput(
            placeholder="Tienda",
            style=Pack(width=200)
        )

        # Tasa Interés
        self.interest_rate = toga.TextInput(
            placeholder="Tasa Interés",
            style=Pack(width=200)
        )

        # Tiempo Hypoteca/Crédito
        self.yearsReturn = toga.TextInput(
            placeholder="Periodo Retorno (AÑOS)",
            style=Pack(width=200)
        )

        self.amount_box = self._campo("Cantidad (€) :", self.amount_input)
        self.rate_box = self._campo("Tasa interés (%) :", self.interest_rate)
        self.years_box = self._campo("Periodo retorno (años) :", self.yearsReturn)
        self.shop_box = self._campo("Tienda :", self.shop_input)

        # Selector de cuenta destino (para transferencia)
        self.label_destino = toga.Label(
            "Cuenta destino :",
            style=Pack(margin=10)
            )       
        self.transfer_account_selector = toga.Selection(
            items=[],
            on_change=self.account_changed
        )
        self.transfer_account_selector.items = self.gD.load_accounts()

        # Botón Ejecutar Acción
        self.execute_btn = toga.Button(
            "Ejecutar",
            on_press=self.ejecutar,
            style=Pack(margin=10)
        )

        # Ocultos inicialmente
        self.amount_box.style.visibility = "hidden"
        self.shop_box.style.visibility = "hidden"
        self.rate_box.style.visibility = "hidden"
        self.years_box.style.visibility = "hidden"
        self.label_destino.style.visibility = "hidden"
        self.transfer_account_selector.style.visibility = "hidden"

        self.btn_cuentas = toga.Button(
            "Ver cuentas",
            on_press=self.abrir_ventana_cuentas,
            style=Pack(margin=10)
        )

        self.espacio = toga.Box(
            style=toga.style.Pack(height=20)
        )

        box = toga.Box(
            children=[
                self.titulo,
                self.account_input,
                self.Titulo2,
                name_box,
                self.doc_id_input,
                self.email_input, 
                address_box,
                self.nationality_selection,
                create_btn,
                self.espacio,
                self.separador,
                self.espacio,
                self.origen_label,
                self.account_selector,
                self.accion_label, 
                self.action_selector,
                self.amount_box,
                self.rate_box,
                self.years_box,
                self.shop_box,
                self.label_destino,
                self.transfer_account_selector,
                contenedor_botonhyp,
                self.execute_btn,
                self.espacio,
                self.espacio,
                self.espacio,
                self.btn_cuentas,
                self.espacio,
                self.espacio,
                self.label_info
            ],
            style=Pack(direction=COLUMN, margin=10)
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = box
        self.main_window.show()

        # self.refresh_balance()

    # Abrir nueva ventana para mostrar estado de cuenta y movimientos.
    #-------------------------------------------------------------------------
    def abrir_ventana_cuentas(self, widget):
        logging.info("Dentro de ventana sobre cuentas.")
        # Nueva ventana
        ventana = toga.Window(title="Listado de cuentas", size=(900, 500))
        # Contenedor principal
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # Título
        titulo = toga.Label(
            "Listado de cuentas bancarias",
            style=Pack(margin_bottom=10)
        )
        # Selector propio: no pisar self.account_selector de la pantalla principal.
        # Los items se cargan al final, cuando ya existen las tablas.
        self.cuentas_selector = toga.Selection(
            items=[],
            on_change=self.account_changed_CuentaInfo
        )

        # Datos de la cuenta
        datos_cuenta = [
            (
            self.cuenta[0],
            self.cuenta[1],
            self.cuenta[4],
            self.cuenta[3],
            self.cuenta[2],
            )
        ]
        
        label_detallesCuenta = toga.Label(
            "Detalles cuenta: ",
            style=Pack(margin_bottom=10)
        )
        # Tabla
        self.tabla_cuenta = toga.Table(
            columns=[
                "ID cuenta",
                "Titular",
                "Saldo",
                "Estado",
                "Fecha creación"
                ],
            data=datos_cuenta,
            style=Pack(flex=1)
        )

        self.espacio = toga.Box(
            style=toga.style.Pack(height=20)
        )

        datos_eventos = [
            (
            evento[0],
            evento[1],
            evento[2],
            evento[3],
            )
            for evento in self.EventosCuenta 
            ]

        label_EventosCuenta = toga.Label(
            "Eventos cuenta: ",
            style=Pack(margin_bottom=10)
        )

        self.tablaEventos = toga.Table(
            columns=[
                "Cuenta / préstamo",
                "Tipo evento",
                "Evento",
                "Fecha creación",
                ],
            data=datos_eventos,
            style=Pack(flex=1)
        )

        self.btn_CheckEvents = toga.Button(
            "Check Eventos-Cuentas",
            on_press=self.check_eventos_cuentas,
            style=Pack(margin=10)
        )

        cuentas_items = self.gD.load_accounts()
        cuentas_items.insert(0, "") # Añadi vacío como primer elementos, user selecciona cuenta que ver.
        self.cuentas_selector.items = cuentas_items

        box.add(titulo)
        box.add(self.cuentas_selector)
        box.add(label_detallesCuenta)
        box.add(self.tabla_cuenta)
        box.add(self.espacio)
        box.add(label_EventosCuenta)
        box.add(self.tablaEventos)
        box.add(self.btn_CheckEvents)

        ventana.content = box
        ventana.show()

    # Abrir nueva ventana para mostrar detalles de las cuetas con créditos o hipotecas.
    #------------------------------------------------------------------------------------
    def ventana_infoHipoteca(self, widget):
        # Ventana secundaria: si fuera MainWindow, al cerrarla se cerraría la app.
        ventana = toga.Window(title="Hipotecas y créditos", size=(900, 600))

        # Desplegable
        self.combo = toga.Selection(
                items=[],
                style=Pack(margin=5),
                on_change=self.info_account_changed
                )

        self.hyp_cred = toga.Selection(
                items=["Crédito", "Hipoteca"],
                style=Pack(margin=5),
                on_change=self.type_op_changed
                )

        self.Lista_elementos = toga.Selection(
                items=[],
                style=Pack(margin=5),
                on_change=self.negocioTraerDatosCredHipotecas
                )

        # Primera tabla
        titulo = toga.Label(
            "Pagos",
            style=Pack(margin_bottom=10)
        )

        self.tabla_superior = toga.Table(
            columns=["Importe", "Fecha pago"],
            data=[
                ["", ""],
                ["", ""],
            ],
            style=Pack(flex=1, margin=5)
            )

        # Label
        self.label = toga.Label(
            "Detalles :",
            style=Pack(margin=(10, 5))
        )

        # Segunda tabla: mismo orden que obtenerInfoCreditoHypoteka()[1:8]
        self.tabla_inferior = toga.Table(
            columns=["Id", "Montante", "Interés", "Fecha inicio", "Cuota", "Meses", "Saldo"],
            data=[],
            style=Pack(flex=1, margin=5)
        )

        # Contenedor principal
        caja = toga.Box(
            style=Pack(direction=COLUMN, margin=10)
            )

        caja.add(self.combo)
        caja.add(self.hyp_cred)
        caja.add(self.Lista_elementos)
        caja.add(titulo)
        caja.add(self.tabla_superior)
        caja.add(self.label)
        caja.add(self.tabla_inferior)

        self.combo.items = self.gD.load_accounts()

        ventana.content = caja
        ventana.show()

    def refresh_balance(self):
        acc = self.gD.domainAccount(self.account_id)
        self.label_info.text = (
            f"Titular: {acc.owner} | "
            f"Saldo: {acc.balance}"
        )    
    
def main():
    if sys.platform == "win32":
        log_file = Path(r"C:\Users\Jorge.Vega\Documents\ENABLON-proj\PROYECTOS\EbD\EventDrivenApplication\log\\")
    elif sys.platform == "darwin":
        log_file = Path.home() / "PycharmProjects" / "EventDrivenAppy" / "log"
    else:
        # Linux u otros
        log_file = Path.home() / "EventDrivenApplication" / "log"

    # 👇 Esto es lo que falta: crear la carpeta si no existe
    log_file.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=log_file / f"EbAPy_{fecha}.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s -  %(message)s",
        force=True
        )

    icon_path = Path(__file__).parent / "resources" / "Eggbank.ico"

    app = EventSourcingApp(
        formal_name="Event Based ApPy",
        app_id="com.SkullWithGasMask.EventBasedBank",
    )

    print("Lanzando app...")
    app.main_loop()    

if __name__ == "__main__":
    print("Creando app...")

    main()    