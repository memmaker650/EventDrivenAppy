import sys
import os
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from toga.colors import RED, BLUE, GREEN, ORANGE, YELLOW
from toga.icons import Icon
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
        print("Account_id refreshed: ", self.account_id)
        self.account_selector.items = self.gD.load_accounts()   

    def account_changed(self, widget):  
        logging.info("Dentro de Account_Changed")

        self.account_id = widget.value

    def account_changed_CuentaInfo(self, widget):  
        logging.info("Dentro de Account_Changed")

        self.account_id = widget.value

        info = self.gD.load_accountInfo(widget.value)
        self.tabla_cuenta.data = [tuple(info)] if info else []

        self.eventosCuenta = self.gD.cargaEventosCompletos(widget.value) or []
        self.tablaEventos.data = [
            (evento[0], evento[1], evento[2], evento[3])
            for evento in self.eventosCuenta
        ]

    def type_op_changed(self, widget):  
        logging.info("Dentro de type_op_Changed")

        if widget.value == "Hipoteca":
            self.operationSelected = "hip"
        else:
             self.operationSelected = "cre"  

        self.listaCredHyp = self.gD.listar_hypotecasCreditos_asociados(self.account_id, self.operationSelected)     
        self.Lista_elementos.items = self.listaCredHyp

    def negocioTraerDatosCredHipotecas(self, widget):
        id = widget.value

        self.dataEventosPagosHypCred = self.gD.traer_EventosPago_CreditoHypoteka(id, "mortgagePayment")
        self.dataCredHyp = self.gD.traer_Info_CreditoHypoteka(id)
        print("Datos Hipoteca: ", self.dataCredHyp)
        total = 0

        self.tabla_superior.data.clear()

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

        self.tabla_inferior.data.clear()
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

        # Ocultar todo por defecto
        self.amount_input.style.visibility = "hidden"
        self.transfer_account_selector.style.visibility = "hidden"

        # Crear y cerrar: nada
        if accion in ("crear", "cerrar"):
            pass
        # Depositar, retirar y pago_tarjeta: solo cantidad
        elif accion in ("depositar", "retirar", "pago_hipoteca", "pago_crédito"):
            self.amount_input.style.visibility = "visible"
            self.interest_rate.visibility = "hidden"
            self.yearsReturn.visibility = "hidden"
            self.shop_input.style.visibility = "hidden"
        # Hipoteca y Crédito: creación
        elif accion in ("pedir_hipoteca", "pedir_crédito"):
            self.amount_input.style.visibility = "visible"   
            self.interest_rate.visibility = "visible"
            self.yearsReturn.visibility = "visible"
            self.shop_input.style.visibility = "hidden"
        elif accion in ("pago_tarjeta"): 
            self.amount_input.style.visibility = "visible"   
            self.shop_input.style.visibility = "visible"
        # Transferencia: cantidad + cuenta destino
        elif accion == "transferencia":
            self.amount_input.style.visibility = "visible"
            self.label_destino.style.visibility = "visible"
            self.transfer_account_selector.style.visibility = "visible" 

        notification.notify(
            title="Mi aplicación",
            message="Tienes una nueva tarea pendiente",
            app_name="EventBasedApPy",
            timeout=10
        )    
        
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
            style=Pack(margin=10)
        )
        self.nationality_selection.items = self.gD.traer_listaNacionalidades()

        self.account_input = toga.TextInput(
            value=self.account_id,
            placeholder="Número de cuenta",
            style=Pack(margin=10)
        )

        self.label_info = toga.Label("Inicial")

        create_btn = toga.Button(
            "Crear cuenta",
            on_press=lambda widget: self.gD.create_account(widget, self.account_input.value, self.owner_input.value, self.family_name_input.value, self.doc_id_input.value, self.address_input.value, self.city_input.value, self.nationality_selection)
        )   

        btn_hypotekas = toga.Button(
            "Info Hipotecas",
            style=Pack(width=200),
            background_color="green",
            on_press=self.ventana_infoHipoteca)

        btn_izquierdo = toga.Button(
            "Batcg Tratar Eventos",
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
            on_press=lambda widget: self.gD.ejecutarAccion(widget, self.action_selector.value, self.account_selector.value, self.amount_input.value, self.transfer_account_selector.value, None, self.shop_input.value, self.interest_rate.value, self.yearsReturn.value),
            style=Pack(margin=10)
        )

        # Ocultos inicialmente
        self.amount_input.style.visibility = "hidden"
        self.shop_input.style.visibility = "hidden"
        self.interest_rate.visibility = "hidden"
        self.yearsReturn.visibility = "hidden"
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
                self.interest_rate,
                self.amount_input,
                self.yearsReturn, 
                self.shop_input,
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
        self.account_selector = "ACC-001"
        self.account_selector = toga.Selection(
            items=[],
            on_change=self.account_changed_CuentaInfo
        )   
        cuentas_items = self.gD.load_accounts()
        cuentas_items.insert(0, "") # Añadi vacío como primer elementos, user selecciona cuenta que ver.
        self.account_selector.items = cuentas_items
        
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
            "Detalles cuenta: ",
            style=Pack(margin_bottom=10)
        )

        self.tablaEventos = toga.Table(
            columns=[
                "ID cuenta",
                "Tipo evento",
                "Evento",
                "Fecha creación",
                ],
            data=datos_eventos,
            style=Pack(flex=1)
        )

        self.btn_CheckEvents = toga.Button(
            "Check Eventos-Cuentas",
            on_press=self.gD.calculoEventosACuenta,
            style=Pack(margin=10)
        )

        box.add(titulo)
        box.add(self.account_selector)
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
        self.main_window = toga.MainWindow(title=self.formal_name)

        # Desplegable
        self.combo = toga.Selection(
                items=[],
                style=Pack(margin=5),
                on_change=self.account_changed
                )
        self.combo.items = self.gD.load_accounts()

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
            "Pagos Hipoteca",
            style=Pack(margin_bottom=10)
        )

        self.tabla_superior = toga.Table(
            columns=["ID", "Nombre"],
            data=[
                ["", ""],
                ["", ""],
            ],
            style=Pack(flex=1, margin=5)
            )

        # Label
        self.label = toga.Label(
            "Detalles Hipoteca :",
            style=Pack(margin=(10, 5))
        )

        # Segunda tabla 
        self.tabla_inferior = toga.Table(
            columns=["Id Hipoteca", "Montante", "Interés", "Meses", "Cuota"],
            data=[
            [self.dataCredHyp[1], self.dataCredHyp[2], self.dataCredHyp[3], self.dataCredHyp[4],self.dataCredHyp[5]],
            ],
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

        self.main_window.content = caja
        self.main_window.show()

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

    app = EventSourcingApp(
        formal_name="Event Based ApPy",
        app_id="com.SkullWithGasMask.EventBasedBank",
        icon=Icon("resources/Eggnank_icon")
    )

    print("Lanzando app...")
    app.main_loop()    

if __name__ == "__main__":
    print("Creando app...")

    main()    