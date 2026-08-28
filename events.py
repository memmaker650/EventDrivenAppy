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

class AccountClosed(self, account_id, owner):
    def __init__(self):
        self.account_id = account_id
        self.owner = owner
        self.state = "closed"