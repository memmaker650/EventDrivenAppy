import commands
import domain
import events


def test_create_account_command():
    cmd = commands.CreateAccount("ACC-001", "Ana")
    assert cmd.account_id == "ACC-001"
    assert cmd.owner == "Ana"
    assert cmd.state == "open"


def test_deposit_withdraw_transfer_card_commands():
    deposit = commands.DepositMoney("ACC-001", 100)
    withdraw = commands.MoneyWithDraw("ACC-001", 40)
    transfer = commands.TransferMoney("ACC-001", 25, "ACC-002")
    card = commands.CardPayment("ACC-001", 12, "Mercadona")

    assert deposit.amount == 100
    assert withdraw.amount == 40
    assert transfer.To == "ACC-002"
    assert card.shop == "Mercadona"


def test_mortgage_and_credit_commands():
    demand = commands.DemandMortgage("ACC-001", "HYP-001", "3.5", 120000, 20, "2026-01-01")
    pay = commands.MortgagePayment("HYP-001", 500, "2026-02-01")
    amort = commands.MortgageAmortisation("HYP-001", 1000, "2026-03-01")
    credit = commands.DemandCredit("ACC-001", "CRE-001", "8", 3000, 2, "2026-01-01")
    credit_pay = commands.CreditPayment("CRE-001", 100, "2026-02-01")
    overdraft = commands.Overdraft("ACC-001", 50, "tienda")
    close = commands.CloseAccount("ACC-001")

    assert demand.mortgage_id == "HYP-001"
    assert pay.paymentDate == "2026-02-01"
    assert amort.mortgage_id == "HYP-001"
    assert credit.credit_id == "CRE-001"
    assert credit_pay.credit_id == "CRE-001"
    assert credit_pay.paymentDate == "2026-02-01"
    assert overdraft.account_id == "ACC-001"
    assert close.state == "closed"
    assert close.amount == 0


def test_event_classes():
    created = events.AccountCreated("ACC-001", "Luis")
    deposited = events.MoneyDeposited(80)
    withdrawn = events.MoneyWithDraw(30)
    mortgage = events.DemandMortgage("ACC-001", 3.5, 100000, 20, "2026-01-01")
    mortgage_pay = events.MortgagePayment("ACC-001", 400, "2026-02-01")
    amort = events.AmortisationPayment("ACC-001", 1000, "2026-03-01")
    credit = events.DemandCredit("ACC-001", 7, 2000, 1, "2026-01-01")
    credit_pay = events.CreditPayment("ACC-001", 50, "2026-02-01")
    transfer = events.MoneyTransfer(20, "ACC-009")
    card = events.PaymentCard(15, "Ikea")
    overdraft = events.Overdraft("ACC-001", 10)
    closed = events.AccountClosed("ACC-001", "Luis")

    assert created.state == "open"
    assert deposited.amount == 80
    assert withdrawn.amount == -30
    assert mortgage.amount == -100000
    assert mortgage_pay.payment_date == "2026-02-01"
    assert amort.amount == -1000
    assert credit.interest_rate == 7
    assert credit_pay.amount == -50
    assert transfer.destinaton == "ACC-009"
    assert card.shop == "Ikea"
    assert overdraft.amount == 10
    assert closed.state == "closed"


def test_bank_account_apply_secuencia():
    account = domain.BankAccount()
    account.apply("AccountCreated", {"owner": "Marta"})
    account.apply("MoneyDeposited", {"amount": 200})
    account.apply("Moneywithdraw", {"amount": 50})
    account.apply("CardPayment", {"amount": 20})

    assert account.owner == "Marta"
    assert account.balance == 130


def test_load_account_reconstruye_desde_eventos(isolated_db):
    domain.handle_create_account(commands.CreateAccount("ACC-010", "Paco"))
    domain.handle_deposit(commands.DepositMoney("ACC-010", 300))
    domain.handle_withdraw(commands.MoneyWithDraw("ACC-010", 80))

    account = domain.load_account("ACC-010")
    assert account.owner == "Paco"
    assert account.balance == 220


def test_handle_create_account_persiste_evento(isolated_db):
    resultado = domain.handle_create_account(commands.CreateAccount("ACC-011", "Eva"))
    assert resultado["ok"] is True
    eventos = domain.load_events("ACC-011")
    assert eventos[0][0] == "AccountCreated"


def test_handle_deposit_withdraw_transfer_card(isolated_db):
    domain.handle_deposit(commands.DepositMoney("ACC-012", 90))
    domain.handle_withdraw(commands.MoneyWithDraw("ACC-012", 10))
    domain.handle_moneyTransfer(commands.TransferMoney("ACC-012", 15, "ACC-099"))
    domain.handle_CardPayment(commands.CardPayment("ACC-012", 5, "Zara"))

    tipos = [e[0] for e in domain.load_events("ACC-012")]
    assert tipos == ["MoneyDeposited", "Moneywithdraw", "MoneyTransfer", "CardPayment"]


def test_handle_demand_and_payment_mortgage(isolated_db):
    cmd = commands.DemandMortgage("ACC-013", "HYP-010", "2.5", 80000, 15, "2026-01-01T00:00:00")
    domain.handle_demandMortgage(cmd)
    domain.handle_mortgagePayment(commands.MortgagePayment("HYP-010", 350, "2026-02-01"))

    assert domain.load_events("ACC-013")[0][0] == "demandMortgage"
    assert domain.load_events("HYP-010")[0][0] == "mortgagePayment"


def test_handle_mortgage_amortisation(isolated_db):
    cmd = commands.MortgageAmortisation("HYP-011", 2000, "2026-04-01")
    domain.handle_mortgageAmortisation(cmd)
    assert domain.load_events("HYP-011")[0][0] == "mortgageAmortisation"


def test_handle_demand_credit(isolated_db):
    cmd = commands.DemandCredit("ACC-014", "CRE-010", "9", 1500, 1, "2026-01-01")
    domain.handle_demandCredit(cmd)
    assert domain.load_events("CRE-010")[0][0] == "demandCredit"


def test_handle_credit_payment(isolated_db):
    cmd = commands.CreditPayment("CRE-011", 80, "2026-02-01")
    domain.handle_CreditPayment(cmd)
    assert domain.load_events("CRE-011")[0][0] == "CreditPayment"


def test_handle_overdraft_and_close(isolated_db):
    domain.handle_Overdraft(commands.Overdraft("ACC-015", 25))
    domain.handle_close_account(commands.CloseAccount("ACC-015"))

    tipos = [e[0] for e in domain.load_events("ACC-015")]
    assert tipos == ["Overdraft", "CloseAccount"]
