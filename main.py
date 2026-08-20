import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from database import init_db, loadMaxAccountID, load_accounts
from commands import CreateAccount, DepositMoney
from domain import (
    handle_create_account,
    handle_deposit,
    handle_withdraw,
    handle_moneyTransfer,
    handle_close_account,
    load_account
)

print("Arrancando aplicación...")

class EventSourcingApp(toga.App):
    estadoApp = "info"
    estadoTexto = "Texto de prueba"
    action = ""

    def account_changed(self, widget):       
        self.account_id = widget.value

        self.refresh_balance()

    def action_changed(self, widget):       
        self.action = widget.value

    def defineEstadoApp(self, estado, texto):       
        self.estadoApp = estado
        self.estadoTexto = texto

    def startup(self):

        init_db()

        self.account_id = f"ACC-{loadMaxAccountID()+1:03d}"

        self.titulo = toga.Label(
            "ID cuenta",
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
            on_press=self.create_account
        )   

        self.acction_selector = toga.Selection(
            items=["crear", "depositar", "retirar", "transferencia", "cerrar"],
            on_change=self.account_changed
        )

        self.execute_btn = toga.Button(
            "Ejecutar",
            on_press=lambda widget: self.ejecutarAccion(widget, 100)
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
        self.account_selector.items = load_accounts()

        self.acction_selector = toga.Selection(
            items=["crear", "depositar", "retirar", "transferencia", "cerrar"],
            on_change=self.action_changed
        )

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
                self.acction_selector,
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

    def abrir_ventana_cuentas(self, widget):
        # Nueva ventana
        ventana = toga.Window(title="Listado de cuentas", size=(900, 500))
        # Contenedor principal
        box = toga.Box(style=Pack(direction=COLUMN, margin=10))

        # Título
        titulo = toga.Label(
            "Listado de cuentas bancarias",
            style=Pack(margin_bottom=10)
        )
        
        self.account_selector = toga.Selection(
            items=[],
            on_change=self.account_changed
        )
        self.account_selector.items = load_accounts()

        # Datos de ejemplo
        datos = [
            (1, "Juan Pérez", 1250.50, "Activa", "2026-08-20"),
            (2, "Ana García", 350.00, "Activa", "2026-08-19"),
            (3, "Pedro López", 0.00, "Bloqueada", "2026-08-15"),
        ]

        # Tabla
        tabla = toga.Table(
            columns=[
                "ID cuenta",
                "Titular",
                "Saldo",
                "Estado",
                "Último movimiento"
                ],
            data=datos,
            style=Pack(flex=1)
        )

        self.espacio = toga.Box(
            style=toga.style.Pack(height=20)
        )

        tablaEventos = toga.Table(
            columns=[
                "ID cuenta",
                "Titular",
                "Saldo",
                "Estado",
                "Último movimiento"
                ],
            data=datos,
            style=Pack(flex=1)
        )

        box.add(titulo)
        box.add(self.account_selector)
        box.add(tabla)
        box.add(self.espacio)

        ventana.content = box
        ventana.show()   

    def create_account(self, widget):

        owner = self.owner_input.value

        if not owner:
            self.label_info.text = "Debe indicar un nombre"
            return

        account_id = self.account_input.value    

        cmd = CreateAccount(
            self.account_id,
            owner
        )

        handle_create_account(cmd)

        self.account_selector.items = load_accounts()

        self.refresh_balance()

    def ejecutarAccion(self, widget, accion):
        self.account_id = self.account_selector.value

        if accion == "crear":
            create_account()

        elif accion == "depositar":
            cmd = DepositMoney(
                self.account_id,
                100
            )

            handle_deposit(cmd)
        elif accion == "retirar":
            cmd = Moneywithdraw(
                self.account_id,
                100
            )

            handle_withdraw(cmd)

        elif accion == "transferencia":
            cmd = MoneyTransfer(
                self.account_id,
                100
            )

            handle_moneyTransfer(cmd)

        elif accion == "cerrar":
            cmd = CloseAccount(
                self.account_id
            )

            handle_close_account(cmd)

        self.refresh_balance()

    def refresh_balance(self):

        acc = load_account(self.account_id)

        self.label_info.text = (
            f"Titular: {acc.owner} | "
            f"Saldo: {acc.balance}"
        )
    
def main():
    return EventSourcingApp()

if __name__ == "__main__":
    print("Creando app...")

    app = EventSourcingApp(
        "Event Based ApPy",
        "org.example.eventsourcing"
    )

    print("Lanzando app...")
    app.main_loop()