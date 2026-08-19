import json

from database import save_event, load_events


class BankAccount:
    def __init__(self):
        self.owner = None
        self.balance = 0

    def apply(self, event_type, data):

        if event_type == "AccountCreated":
            self.owner = data["owner"]

        elif event_type == "MoneyDeposited":
            self.balance += data["amount"]


def load_account(account_id):

    account = BankAccount()

    for event_type, data_json in load_events(account_id):
        data = json.loads(data_json)
        account.apply(event_type, data)

    return account


def handle_create_account(command):

    save_event(
        command.account_id,
        "AccountCreated",
        {
            "owner": command.owner
        }
    )


def handle_deposit(command):

    save_event(
        command.account_id,
        "MoneyDeposited",
        {
            "amount": command.amount
        }
    )

def handle_withdraw(command):

    save_event(
        command.account_id,
        "Moneywithdraw",
        {
            "amount": command.amount
        }
    )

def handle_moneyTransfer(command):

    save_event(
        command.account_id,
        "MoneyTransfer",
        {
            "amount": command.amount
        }
    )

def handle_close_account(command):

    save_event(
        command.account_id,
        "CloseAccount",
        {
            "amount": command.amount
        }
    )