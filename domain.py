import json

import logging
from database import save_event, load_events

logger = logging.getLogger(__name__)

class BankAccount:
    def __init__(self):
        self.owner = None
        self.balance = 0

    def apply(self, event_type, data):

        if event_type == "AccountCreated":
            self.owner = data["owner"]

        elif event_type == "MoneyDeposited":
            self.balance += int(data["amount"])
        elif event_type == "Moneywithdraw":
            self.balance -= int(data["amount"])
        elif event_type == "CardPayment":
            self.balance -= int(data["amount"])    


def load_account(account_id):
    account = BankAccount()

    for event_type, data_json in load_events(account_id):
        data = json.loads(data_json)
        account.apply(event_type, data)

    return account


def handle_create_account(command):
    print("Handle_create_account")
    logger.info("Hadle_create_account")
    resultado = save_event(
        command.account_id,
        "AccountCreated",
        {
            "account_id": command.account_id,
            "owner": command.owner,
            "state":"open"
        }
    )
    
    return resultado

def handle_deposit(command):
    print("handle_deposit")
    logger.info("handle_deposit")

    save_event(
        command.account_id,
        "MoneyDeposited",
        {
            "account_id": command.account_id,
            "amount": command.amount
        }
    )

def handle_withdraw(command):
    print("handle_withdraw")
    logger.info("handle_withdraw")

    save_event(
        command.account_id,
        "Moneywithdraw",
        {
            "account_id": command.account_id,
            "amount": command.amount
        }
    )

def handle_moneyTransfer(command):
    print("handle_moneyTransfer")
    logger.info("handle_moneyTransfer")

    save_event(
        command.account_id,
        "MoneyTransfer",
        {
            "account_id": command.account_id,
            "amount": command.amount,
            "To": command.To  
        }
    )

def handle_CardPayment(command):
    print("Card Payment")
    logger.info("handle_Card_Payment")

    save_event(
        command.account_id,
        "CardPayment",
        {
            "amount": command.amount,
            "shop": command.shop
        }
    )

def handle_demandMortgage(command):
    print("Demand Mortgage")
    logger.info("handle_Demand_Mortgage")

    save_event(
        command.account_id,
        "demandMortgage",
        {
            "account_id": command.account_id,
            "amount": command.amount,
        }
    )

def handle_mortgagePayment(command):
    print("Mortgage Payment")
    logger.info("handle_Mortgage_Payment")

    save_event(
        command.account_id,
        "mortgagePayment",
        {
            "account_id": command.account_id,
            "amount": command.amount,
        }
    ) 

def handle_demandCredit(command):
    print("demand Credit")
    logger.info("handle_demandCredit")

    save_event(
        command.account_id,
        "demandCredit",
        {
            "account_id": command.account_id,
            "amount": command.amount,
        }
    )  

def handle_CreditPayment(command):
    print("Credit Payment")
    logger.info("handle_CreditPayment")

    save_event(
        command.account_id,
        "CreditPayment",
        {
            "account_id": command.account_id,
            "amount": command.amount,
        }
    )    

def handle_Overdraft(command):
    print("handle_deposit")
    logger.info("handle_deposit")

    save_event(
        command.account_id,
        "Overdraft",
        {
            "amount": command.amount,
        }
    )

def handle_close_account(command):
    print("handle_Close_account")
    logger.info("handle_Close_account")

    save_event(
        command.account_id,
        "CloseAccount",
        {
            "amount": command.amount
        }
    )