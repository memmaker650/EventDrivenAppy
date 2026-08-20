class AccountCreated:
    def __init__(self, account_id, owner):
        self.account_id = account_id
        self.owner = owner
        self.state = "open"

class MoneyDeposited:
    def __init__(self, amount):
        self.amount = amount

class MoneyWithdrawn:
    def __init__(self, amount):
        self.amount = -amount

class MoneyTransferred:
    def __init__(self, amount, destiny):
        self.amount = amount
        self.destinaton = destiny

class AccountClosed:
    def __init__(self):
        self.state = "closed"