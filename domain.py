import json
import logging

import events
from database import save_event, load_events

logger = logging.getLogger(__name__)


class BankAccount:
    """Agregado: se reconstruye aplicando los eventos en orden."""

    def __init__(self):
        self.owner = None
        self.balance = 0

    def apply(self, event):
        if isinstance(event, events.AccountCreated):
            self.owner = event.owner
        elif isinstance(event, events.MoneyDeposited):
            self.balance += int(event.amount)
        elif isinstance(event, (events.MoneyWithdrawn, events.CardPaid)):
            self.balance -= int(event.amount)
        # Pendiente de decidir (igual que antes, no afectan al saldo):
        # MoneyTransferred, OverdraftApplied, AccountClosed,
        # MortgageDemanded, CreditDemanded.


def load_account(account_id):
    account = BankAccount()

    for event_type, data_json in load_events(account_id):
        try:
            event = events.from_record(event_type, json.loads(data_json))
        except events.UnknownEventType:
            logger.warning("Evento desconocido '%s' en %s, se ignora",
                           event_type, account_id)
            continue
        account.apply(event)

    return account


def _emit(stream_id, event):
    """Guarda un evento en el flujo (stream) indicado."""
    event_type, data = events.to_record(event)
    logger.info("%s -> %s", event_type, stream_id)
    return save_event(stream_id, event_type, data)


def handle_create_account(command):
    return _emit(
        command.account_id,
        events.AccountCreated(
            account_id=command.account_id,
            owner=command.owner,
            family_name=command.family_name,
            doc_id=command.doc_id,
        ),
    )


def handle_deposit(command):
    return _emit(
        command.account_id,
        events.MoneyDeposited(account_id=command.account_id,
                              amount=command.amount),
    )


def handle_withdraw(command):
    return _emit(
        command.account_id,
        events.MoneyWithdrawn(account_id=command.account_id,
                              amount=command.amount),
    )


def handle_moneyTransfer(command):
    return _emit(
        command.account_id,
        events.MoneyTransferred(account_id=command.account_id,
                                amount=command.amount,
                                destination=command.To),
    )


def handle_CardPayment(command):
    return _emit(
        command.account_id,
        events.CardPaid(account_id=command.account_id,
                        amount=command.amount,
                        shop=command.shop),
    )


def handle_demandMortgage(command):
    return _emit(
        command.account_id,
        events.MortgageDemanded(
            account_id=command.account_id,
            mortgage_id=command.mortgage_id,
            interest_rate=command.rate,
            amount=command.amount,
            return_period=command.period,
            initial_date=command.dateInit,
        ),
    )


def handle_mortgagePayment(command):
    return _emit(
        command.mortgage_id,
        events.MortgagePaid(mortgage_id=command.mortgage_id,
                            amount=command.amount,
                            payment_date=command.paymentDate),
    )


def handle_mortgageAmortisation(command):
    return _emit(
        command.mortgage_id,
        events.MortgageAmortised(mortgage_id=command.mortgage_id,
                                 amount=command.amount,
                                 payment_date=command.paymentDate),
    )


def handle_demandCredit(command):
    return _emit(
        command.credit_id,
        events.CreditDemanded(
            account_id=command.account_id,
            credit_id=command.credit_id,
            interest_rate=command.rate,
            amount=command.amount,
            return_period=command.period,
            initial_date=command.dateInit,
        ),
    )


def handle_CreditPayment(command):
    return _emit(
        command.credit_id,
        events.CreditPaid(credit_id=command.credit_id,
                          amount=command.amount,
                          payment_date=command.paymentDate),
    )


def handle_Overdraft(command):
    return _emit(
        command.account_id,
        events.OverdraftApplied(account_id=command.account_id,
                                amount=command.amount),
    )


def handle_close_account(command):
    return _emit(
        command.account_id,
        events.AccountClosed(account_id=command.account_id,
                             amount=command.amount),
    )
