import logging

logger = logging.getLogger(__name__)

class AccountCreated:
    def __init__(self, account_id, owner):
        self.account_id = account_id
        self.owner = owner
        self.state = "open"

class MoneyDeposited:
    def __init__(self, amount):
        self.amount = amount

class MoneyWithDraw:
    def __init__(self, amount):
        self.amount = -amount

class DemandMortgage:
    def __init__(self, account_id, rate, amount, period, dateInit):
        self.account_id = account_id
        self.interest_rate = rate
        self.amount = -amount
        self.period = period
        self.initialDate = dateInit

class MortgagePayment:
    def __init__(self, account_id, amount, pdate):
        self.account_id = account_id
        self.amount = -amount
        self.payment_date = pdate

class AmortisationPayment:
    def __init__(self, account_id, amount, pdate):
        self.account_id = account_id
        self.amount = -amount
        self.payment_date = pdate

class DemandCredit:
    def __init__(self, account_id, rate, amount, period, dateInit):
        self.account_id = account_id
        self.interest_rate = rate
        self.amount = -amount
        self.period = period
        self.initialDate = dateInit

class CreditPayment:
    def __init__(self, account_id, amount, pdate):
        self.account_id = account_id
        self.amount = -amount
        self.payment_date = pdate

class MoneyTransfer:
    def __init__(self, amount, destiny):
        self.amount = amount
        self.destinaton = destiny

class PaymentCard:
    def __init__(self, amount, shop):
        self.amount = amount
        self.shop = shop

class Overdraft:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount    

class AccountClosed:
    def __init__(self, account_id, owner):
        self.account_id = account_id
        self.owner = owner
        self.state = "closed"