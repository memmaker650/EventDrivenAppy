import logging

logger = logging.getLogger(__name__)

class CreateAccount:
    logger.info("CreateAccount class")
    def __init__(self, account_id, owner):
        self.account_id = account_id
        self.owner = owner
        self.state = "open"

class DepositMoney:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

class MoneyWithDraw:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

class TransferMoney:
    def __init__(self, account_id, amount, destiny):
        self.account_id = account_id
        self.amount = amount
        self.To = destiny

class CardPayment:
    def __init__(self, account_id, amount, shop):
        self.account_id = account_id
        self.amount = amount
        self.shop = shop

class DemandMortgage:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

class MortgagePayment:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

class DemandCredit:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount

class CreditPayment:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount        

class Overdraft:
    def __init__(self, account_id, amount, shop):
        self.account_id = account_id
        self.amount = amount

class CloseAccount:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.state = "closed"