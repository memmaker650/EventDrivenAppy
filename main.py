import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from database import init_db, loadMaxAccountID, load_accounts
from commands import CreateAccount, DepositMoney
from domain import (
    handle_create_account,
    handle_deposit,
    load_account,
)

print("Arrancando aplicación...")

class EventSourcingApp(toga.App):
    def account_changed(self, widget):       
        self.account_id = widget.value

        self.refresh_balance()

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

        self.label_saldo = toga.Label(
            "Titular: - | Saldo: 0",
            style=Pack(margin=10)
        )

        create_btn = toga.Button(
            "Crear cuenta",
            on_press=self.create_account
        )

        deposit_btn = toga.Button(
            "Ingresar 100",
            on_press=self.deposit
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
            on_change=self.account_changed
        )

        btn_cuentas = toga.Button(
            "Ver cuentas",
            on_press=self.abrir_ventana_cuentas,
            style=Pack(padding=10)
        )

        box = toga.Box(
            children=[
                self.titulo,
                self.account_input,
                self.owner_input,
                self.separador,
                create_btn,
                self.account_selector, 
                self.label_saldo,
                self.acction_selector,
                deposit_btn,
                btn_cuentas
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

        box.add(titulo)
        box.add(tabla)

        ventana.content = box
        ventana.show()   

    def create_account(self, widget):

        owner = self.owner_input.value

        if not owner:
            self.label_saldo.text = "Debe indicar un nombre"
            return

        account_id = self.account_input.value    

        cmd = CreateAccount(
            self.account_id,
            owner
        )

        handle_create_account(cmd)

        self.account_selector.items = load_accounts()

        self.refresh_balance()

    def deposit(self, widget):
        self.account_id = self.account_selector.value

        cmd = DepositMoney(
            self.account_id,
            100
        )

        handle_deposit(cmd)

        self.refresh_balance()

    def refresh_balance(self):

        acc = load_account(self.account_id)

        self.label_saldo.text = (
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