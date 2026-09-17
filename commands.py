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
    def __init__(self, account_id, hypoteka_id, rate, amount, period, dateInit):
        self.account_id = account_id
        self.mortgage_id = hypoteka_id
        self.rate = rate
        self.amount = amount
        self.period = period
        self.dateInit = dateInit

class MortgagePayment:
    def __init__(self, hypoteka_id, amount, datePay):
        self.mortgage_id = hypoteka_id
        self.amount = amount
        self.paymentDate = datePay

class MortgageAmortisation:
    def __init__(self, hypoteka_id, amount, datePay):
        self.mortgage_id = hypoteka_id
        self.amount = amount
        self.paymentDate = datePay        

class DemandCredit:
    def __init__(self, account_id, credit_id, rate, amount, period, dateInit):
        self.account_id = account_id
        self.credit_id = credit_id
        self.rate = rate
        self.amount = amount
        self.period = period
        self.dateInit = dateInit

class CreditPayment:
    def __init__(self, credit_id, amount, datePay):
        self.credit_id = credit_id
        self.amount = amount
        self.paymentDate = datePay        

class Overdraft:
    def __init__(self, account_id, amount, shop=None):
        self.account_id = account_id
        self.amount = amount
        self.shop = shop

class CloseAccount:
    def __init__(self, account_id, amount=0):
        self.account_id = account_id
        self.amount = amount
        self.state = "closed"