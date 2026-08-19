import toga
from toga.style import Pack
from toga.style.pack import COLUMN

from database import init_db, loadMaxAccountID
from commands import CreateAccount, DepositMoney
from domain import (
    handle_create_account,
    handle_deposit,
    load_account,
)

print("Arrancando aplicación...")

class EventSourcingApp(toga.App):

    def startup(self):

        init_db()

        self.account_id = f"ACC-{loadMaxAccountID()+1:03d}"

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

        box = toga.Box(
            children=[
                self.account_input,
                self.owner_input, 
                self.label_saldo,
                create_btn,
                deposit_btn
            ],
            style=Pack(direction=COLUMN, margin=10)
        )

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = box
        self.main_window.show()

        self.refresh_balance()

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

        self.refresh_balance()

    def deposit(self, widget):

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
        "Event Sourcing",
        "org.example.eventsourcing"
    )

    print("Lanzando app...")
    app.main_loop()