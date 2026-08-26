import os
import toga
from toga.style import Pack
from toga.style.pack import COLUMN
import logging
from pathlib import Path
from datetime import datetime

fecha = datetime.now().strftime("%Y%m%d")

import database
from commands import CreateAccount, DepositMoney, MoneyWithDraw, TransferMoney, PaymentCard, Overdraft
from domain import (
    handle_create_account,
    handle_deposit,
    handle_withdraw,
    handle_moneyTransfer,
    handle_PaymentCard,
    handle_close_account,
    load_account
)

print("Arrancando aplicación...")

class EventSourcingApp(toga.App):
    estadoApp = "info"
    estadoTexto = "Inicial"
    action_selector = toga.Selection()
    boton_execute = False

    def account_changed(self, widget):  
        print("Dentro de Account_Changed")
        logging.info("Dentro de Account_Changed")

        self.account_id = widget.value

        self.refresh_balance()

    def action_changed(self, widget):
        print("Dentro de Action_Changed")
        logging.info("Dentro de Action_Changed")

        accion = widget.value
        # logging.info("WActión: ", accion)

        # Ocultar todo por defecto
        self.amount_input.style.visibility = "hidden"
        self.transfer_account_selector.style.visibility = "hidden"

        # Crear y cerrar: nada
        if accion in ("crear", "cerrar"):
            pass

        # Depositar, retirar y pago_tarjeta: solo cantidad
        elif accion in ("depositar", "retirar", "pago_tarjeta"):
            self.amount_input.style.visibility = "visible"

        # Transferencia: cantidad + cuenta destino
        elif accion == "transferencia":
            self.amount_input.style.visibility = "visible"
            self.transfer_account_selector.style.visibility = "visible" 

    def defineEstadoApp(self, estado, texto):       
        self.estadoApp = estado
        self.estadoTexto = texto

    def startup(self):
        logging.info("Dentro startup")
        database.init_db()

        self.account_id = f"ACC-{database.loadMaxAccountID()+1:03d}"

        self.titulo = toga.Label(
            "EggBank - Operaciones por eventos.",
            style=Pack(margin=10)
            )

        self.owner_input = toga.TextInput(
            placeholder="Nombre del titular",
            style=Pack(margin=10)
            )

        self.account_input = toga.TextInput(
            value=self.account_id,
            placeholder="Número de cuenta",
            style=Pack(margin=10)
        )

        self.label_info = toga.Label("Inicial")

        if self.estadoApp == "info":
            self.label_info = toga.Label(
                self.estadoTexto,
                style=Pack(margin=10)
            )
        elif self.estadoApp == "error":
            self.label_info = toga.Label(
                self.estadoTexto,
                style=Pack(margin=10, color="red")
            )
        elif self.estadoApp == "cuidado":
            self.label_info = toga.Label(
                self.estadoTexto,
                style=Pack(margin=10, color="yellow")
            )
        elif self.estadoApp == "ok":
            self.label_info = toga.Label(
                self.estadoTexto,
                style=Pack(margin=10, color="green")
            )

        create_btn = toga.Button(
            "Crear cuenta",
            on_press=lambda widget: self.create_account(widget, self.account_input, self.owner_input)
        )   

        self.action_selector = toga.Selection(
            items=["crear", "depositar", "retirar", "transferencia", "cerrar"],
            on_change=self.action_changed
        )

        self.separador = toga.Box(
            style=Pack(
                height=1,
                background_color="#C0C0C0",
                margin_top=5,
                margin_bottom=5
            )
        )

        self.account_selector = toga.Selection(
            items=[],
            on_change=self.account_changed
        )
        self.account_selector.items = database.load_accounts()

        self.accion_label = toga.Label(
            "Acción Tipo Evento :",
            style=Pack(margin=10)
            )
        self.action_selector = toga.Selection(
            items=["crear", "depositar", "retirar", "transferencia", "pago_tarjeta", "cerrar"],
            on_change=self.action_changed
        )

        # Cantidad
        self.amount_input = toga.TextInput(
            placeholder="Cantidad",
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
        self.transfer_account_selector.items = database.load_accounts()

        # Botón Ejecutar Acción
        self.execute_btn = toga.Button(
            "Ejecutar",
            on_press=lambda widget: self.ejecutarAccion(widget, self.action_selector, self.account_selector, self.amount_input, self.transfer_account_selector)
        )

        # Ocultos inicialmente
        self.amount_input.style.visibility = "hidden"
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
                self.owner_input,
                create_btn,
                self.espacio,
                self.separador,
                self.espacio,
                self.account_selector,
                self.accion_label, 
                self.action_selector,
                self.amount_input,
                self.label_destino,
                self.transfer_account_selector,
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

        self.refresh_balance()

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
            on_change=self.account_changed
        )
        self.account_selector.items = database.load_accounts()
        print("Default account: ", self.account_selector.value)
        cuenta = database.load_accountInfo(self.account_selector.value)

        # Datos de la cuenta
        datos_cuenta = [
            (
            cuenta[0],
            cuenta[1],
            cuenta[4],
            cuenta[3],
            cuenta[2],
            )
        ]

        # Tabla
        tabla_cuenta = toga.Table(
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

        eventos = database.load_eventsFull(self.account_selector.value)

        datos_eventos = [
            (
            evento[0],
            evento[1],
            evento[2],
            evento[3],
            )
            for evento in eventos
            ]

        tablaEventos = toga.Table(
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
            on_press=self.calculoEventosACuenta,
            style=Pack(margin=10)
        )

        box.add(titulo)
        box.add(self.account_selector)
        box.add(tabla_cuenta)
        box.add(self.espacio)
        box.add(tablaEventos)
        box.add(self.btn_CheckEvents)

        ventana.content = box
        ventana.show()   

    def create_account(self, widget, id_input, ow_input):
        logging.info("Dentro de create_account.")
        if isinstance(ow_input, str):
            owner = ow_input
        else:
            if ow_input is not None:
                owner = ow_input.value
            else:
                self.label_info.text = "Error Crear Cuenta, dueño no rellenado." 
                return
        print("Owner: ", owner)
        print("ACC-id: ", id_input)

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            print("Debe indicar un nombre")
            return
        
        self.account_id = id_input.value   
        
        if self.boton_execute:
            cmd = CreateAccount(
                self.account_id,
                owner
            )

            resul = handle_create_account(cmd)

            self.account_selector.items = database.load_accounts()
        database.crearCuenta(self.account_id, owner)

        # self.refresh_balance()
        # self.gestion_mensaje_info(resul)

    def create_account_block(self, id_input, ow_input):
        logging.info("Dentro de create_account_block.")
        if isinstance(ow_input, str):
            owner = ow_input
        else:
            if ow_input is not None:
                owner = ow_input.value
            else:
                self.label_info.text = "Error Crear Cuenta, dueño no rellenado." 
                return
        print("Owner: ", owner)
        print("ACC-id: ", id_input)

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            print("Debe indicar un nombre")
            return

        self.account_id = id_input  

        database.crearCuenta(self.account_id, owner)

        # self.refresh_balance()
        # self.gestion_mensaje_info(resul)    

    def ejecutarAccion(self, widget, accion, origen, cantidad, destino):
        logging.info("into de ejecutarAccion.")
        print("into de ejecutarAccion.")
        print("------------------------------")
        print("Acció: ", accion.value)
        print("Origen: ", origen.value)
        print("Cantidad: ", cantidad.value)
        print("Destino: ", destino.value)

        self.boton_execute = True

        self.account_id = self.account_selector.value

        if accion.value == "crear":
            if self.owner_input == "":
                self.label_info.text("Introducir Nombre Titular.")
            else:
                self.create_account(None, origen.value, self.owner_input)

        elif accion.value == "depositar":
            print("Jump-2_handle_deposit")
            cmd = DepositMoney(
                origen.value,
                cantidad.value
            )

            handle_deposit(cmd)
        elif accion.value == "retirar":
            print("Jump-2_handle_withdraw")
            cmd = MoneyWithDraw(
                origen.value,
                cantidad.value
            )

            handle_withdraw(cmd)

        elif accion.value == "transferencia":
            print("Jump-2_handle_Transfer")
            cmd = MoneyTransfer(
                origen.value,
                cantidad.value,
                destino.value
            )

            handle_moneyTransfer(cmd)    

        elif accion.value == "cerrar":
            cmd = CloseAccount(
                origen.value
            )

            handle_close_account(cmd)

        self.refresh_balance()
        self.boton_execute = False  
    
    def gestionCuentaAlDia(self, accion, cantidad):
        logging.info("into de gestion Cuenta Al Dia.")
        print("into de gestion Cuenta Al Dia.")

        if accion.value == "crear":
            create_account()

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
    def calculoEventosACuenta(self, widget):    
        logging.info("Calculo Eventos A Cuenta.")
        print("Calculo Eventos A Cuenta")
        
        # Traer info de la tabla Eventos.
        idsEvents = database.load_diffIDAccountInEvents()
        print(idsEvents)

        for x in idsEvents:
            datos = database.load_accountInfo(x)

            if not datos:      # datos == []
                print("La cuenta no existe")
                x = x[0]
                print("ID no creado:", x)
                duegno = database.load_ownerForAccountInEvent(x)
                print("Dueño: ", duegno)
                self.create_account_block(x, duegno)
            else:
                montante = 0.0
                print("Dentro cálculo montante FINAL.")
                # Cuenta creada, cálculo del montante de la cuenta.
                cargas = database.load_moneyForAccountInEvent(x)
                if cargas is None:
                    logging.info("Es None")
                elif not cargas:
                    logging.info("Está vacío")
                else:
                    for nombre, valor in cargas:
                        if nombre == "MoneyDeposited":
                            montante += float(valor)
                        else:
                            montante -= float(valor)

                resultado = database.store_moneyForAccount(montante, x)
                if resultado == 1:
                    self.label_info = "Montante actualizado !!"
                else:
                    self.label_info = "Error guardado Montante - KO !!"

        
        print("TERMINADO TRATAMIENTO EN BLOQUE !!")
        logging.info("TERMINADO TRATAMIENTO EN BLOQUE !!")
        self.label_info = ("TERMINADO TRATAMIENTO EN BLOQUE !!")
    
    def refresh_balance(self):
        acc = load_account(self.account_id)

        self.label_info.text = (
            f"Titular: {acc.owner} | "
            f"Saldo: {acc.balance}"
        )

    def gestion_mensaje_info (self, resultado):
        logging.info("gestion_mensaje_info")
        if resultado["ok"]: 
            estadoApp = "ok"
            self.label_info.text = resultado["mensaje"]
            self.label_info.style.color = "green"
        else:
            estadoApp = "error"
            self.label_info.text = "¡ ERROR !" + " " + resultado["mensaje"],
            self.label_info.style.color = "red" 
    
def main():
    log_file = Path(r"C:\Users\Jorge.Vega\Documents\ENABLON-proj\PROYECTOS\EbD\EventDrivenApplication\log\\")
    logging.basicConfig(
        filename=os.path.join(log_file, f"EbAPy_{fecha}.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s -  %(message)s",
        force=True
        )

    app = EventSourcingApp(
        "Event Based ApPy",
        "com.SkullWithGasMask.EventBasedBank")

    print("Lanzando app...")
    app.main_loop()    

if __name__ == "__main__":
    print("Creando app...")

    main()    