class CreateAccount:
    def __init__(self, account_id, owner, state):
        self.account_id = account_id
        self.owner = owner
        self.state = state


class DepositMoney:
    def __init__(self, account_id, amount):
        self.account_id = account_id
        self.amount = amount