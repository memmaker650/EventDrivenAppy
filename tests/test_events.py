import events

# Registros tal y como los guardaba el domain.py antiguo.
LEGACY = [
    ("AccountCreated", {"account_id": "ACC-001", "owner": "Ana",
                        "family_name": "Ruiz", "doc_id": "123", "state": "open"}),
    ("MoneyDeposited", {"account_id": "ACC-001", "amount": 100}),
    ("Moneywithdraw", {"account_id": "ACC-001", "amount": 30}),
    ("MoneyTransfer", {"account_id": "ACC-001", "amount": 5, "To": "ACC-002"}),
    ("demandMortgage", {"account_id": "ACC-001", "mortgage_id": "HYP-1",
                        "interest_Rate": 2.5, "amount": 1000,
                        "return_Period": 20, "initialDate": "2026-01-01T00:00:00"}),
    ("mortgagePayment", {"mortgage_id": "HYP-1", "amount": 10,
                         "payment_date": "2026-02-01"}),
    ("mortgageAmortisation", {"mortgage_id": "HYP-1", "amount": 50,
                              "payment_date": "2026-03-01"}),
    ("demandCredit", {"account_id": "ACC-001", "credit_id": "CRE-1",
                      "interest_Rate": 5, "amount": 500,
                      "return_Period": 2, "initialDate": "2026-01-01T00:00:00"}),
    ("CreditPayment", {"credit_id": "CRE-1", "amount": 20,
                       "payment_date": "2026-02-01"}),
    ("CloseAccount", {"amount": 0, "account_id": "ACC-001"}),
]


def test_roundtrip_legacy_records():
    for event_type, data in LEGACY:
        event = events.from_record(event_type, data)
        assert events.to_record(event) == (event_type, data)


def test_old_records_without_account_id():
    card = events.from_record("CardPayment", {"amount": 9, "shop": "Bar"})
    assert card.account_id == ""
    over = events.from_record("Overdraft", {"amount": 9})
    assert over.amount == 9
    closed = events.from_record("CloseAccount", {"amount": 0})
    assert closed.account_id == ""


def test_unknown_type():
    try:
        events.from_record("NoExiste", {})
    except events.UnknownEventType:
        return
    raise AssertionError("debería fallar")
