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
    def __init__(self, account_id, rate, amount, period, dateInit):
        self.account_id = account_id
        self.rate = rate
        self.amount = amount
        self.period = period
        self.dateInit = dateInit

class MortgagePayment:
    def __init__(self, account_id, amount, datePay):
        self.account_id = account_id
        self.amount = amount
        self.paymentDate = datePay

class MortgageAmortisation:
    def __init__(self, account_id, amount, datePay):
        self.account_id = account_id
        self.amount = amount
        self.paymentDate = datePay        

class DemandCredit:
    def __init__(self, account_id, amount, rate, period, dateInit):
        self.account_id = account_id
        self.amount = amount
        self.returnPeriod = period
        self.returnPeriod = period
        self.dateInit = dateInit

class CreditPayment:
    def __init__(self, account_id, amount, datePay):
        self.account_id = account_id
        self.amount = amount
        self.paymentDate = datePay        

class Overdraft:
    def __init__(self, account_id, amount, shop):
        self.account_id = account_id
        self.amount = amount

class CloseAccount:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.state = "closed"