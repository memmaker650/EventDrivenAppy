import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple

from dateutil.relativedelta import relativedelta

import events
import hypotekas
from database import save_event, load_events, load_all_events, guardar_proyeccion

logger = logging.getLogger(__name__)

# ------------------------------------------------------------ reglas de saldo
# ÚNICO sitio donde se decide cómo afecta cada evento al saldo de una cuenta.
# Lo usan tanto load_account() como el batch (rebuild_read_model).
CREDITS = (
    events.MoneyDeposited,
    events.CreditDemanded,       # el crédito se ingresa en la cuenta
)
DEBITS = (
    events.MoneyWithdrawn,
    events.CardPaid,
    events.OverdraftApplied,
    events.MoneyTransferred,     # el destino lo abona Projection
    events.MortgagePaid,         # cuotas y amortizaciones se cargan en la
    events.MortgageAmortised,    # cuenta asociada al préstamo
    events.CreditPaid,
)
# MortgageDemanded no mueve saldo: el dinero va al vendedor, no a la cuenta.


def to_decimal(value) -> Decimal:
    """Importe guardado (int, float o texto, con coma o punto) -> Decimal."""
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"importe no válido: {value!r}") from None


class BankAccount:
    """Agregado: se reconstruye aplicando los eventos en orden."""

    def __init__(self, account_id=None):
        self.account_id = account_id
        self.owner = None
        self.family_name = ""
        self.doc_id = ""
        self.state = None
        self.balance = Decimal("0")

    def apply(self, event):
        if isinstance(event, events.AccountCreated):
            self.owner = event.owner
            self.family_name = event.family_name
            self.doc_id = event.doc_id
            self.state = event.state
        elif isinstance(event, events.AccountClosed):
            self.state = "closed"
        elif isinstance(event, CREDITS):
            self.balance += to_decimal(event.amount)
        elif isinstance(event, DEBITS):
            self.balance -= to_decimal(event.amount)

    def receive_transfer(self, event):
        self.balance += to_decimal(event.amount)


@dataclass
class Loan:
    """Hipoteca o crédito tal y como se pidió (evento demand*)."""
    loan_id: str
    account_id: str
    capital: Decimal
    interest_rate: Decimal
    years: int
    start: date
    is_credit: bool

    @property
    def months(self):
        return self.years * 12

    @property
    def end(self):
        return self.start + relativedelta(years=self.years)


@dataclass
class Projection:
    """Estado derivado de recorrer event_store. No escribe eventos."""
    accounts: Dict[str, BankAccount] = field(default_factory=dict)
    loans: Dict[str, Loan] = field(default_factory=dict)
    processed: int = 0
    skipped: List[Tuple[int, str]] = field(default_factory=list)
    loans_without_account: List[str] = field(default_factory=list)

    def _account(self, account_id):
        if not account_id:
            raise ValueError("evento sin cuenta asociada")
        if account_id not in self.accounts:
            self.accounts[account_id] = BankAccount(account_id)
        return self.accounts[account_id]

    def apply(self, event):
        if isinstance(event, (events.MortgageDemanded, events.CreditDemanded)):
            is_credit = isinstance(event, events.CreditDemanded)
            loan_id = event.credit_id if is_credit else event.mortgage_id
            loan = Loan(
                loan_id=loan_id,
                account_id=event.account_id,
                capital=to_decimal(event.amount),
                interest_rate=to_decimal(event.interest_rate),
                years=int(event.return_period),
                start=datetime.fromisoformat(str(event.initial_date)).date(),
                is_credit=is_credit,
            )
            self._account(loan.account_id).apply(event)
            self.loans[loan_id] = loan
        elif isinstance(event, (events.MortgagePaid, events.MortgageAmortised,
                                events.CreditPaid)):
            loan_id = getattr(event, "credit_id", None) or event.mortgage_id
            loan = self.loans.get(loan_id)
            if loan is None:
                raise ValueError(f"préstamo desconocido {loan_id}")
            self._account(loan.account_id).apply(event)
        elif isinstance(event, events.MoneyTransferred):
            to_decimal(event.amount)  # valida antes de tocar ninguna cuenta
            destination = self._account(event.destination)
            self._account(event.account_id).apply(event)
            destination.receive_transfer(event)
        else:
            self._account(event.account_id).apply(event)


def project(records):
    """Recorre (id, aggregate_id, event_type, event_data) en orden global.

    Los eventos que no se pueden aplicar (tipo desconocido, importe no
    válido, préstamo inexistente...) se anotan en `skipped` y se siguen
    procesando los demás.
    """
    projection = Projection()

    for event_id, aggregate_id, event_type, data_json in records:
        try:
            data = json.loads(data_json)
            # Eventos antiguos sin account_id: la cuenta es el propio stream.
            if not data.get("account_id"):
                data["account_id"] = aggregate_id
            projection.apply(events.from_record(event_type, data))
        except (events.UnknownEventType, ValueError, TypeError) as e:
            logger.warning("Evento %s (%s) ignorado: %s", event_id, event_type, e)
            projection.skipped.append((event_id, f"{event_type}: {e}"))
            continue
        projection.processed += 1

    return projection


def load_account(account_id):
    # Se proyecta todo el event_store para incluir transferencias recibidas.
    projection = project(load_all_events())
    return projection.accounts.get(account_id) or BankAccount(account_id)


def rebuild_read_model():
    """Batch: recalcula accounts/hipotecas desde event_store.

    Solo lee eventos; nunca los vuelve a grabar, así que se puede lanzar
    tantas veces como se quiera con el mismo resultado.
    """
    projection = project(load_all_events())

    cuentas = []
    for account in projection.accounts.values():
        if account.owner is None:
            logger.warning("Cuenta %s con movimientos pero sin AccountCreated",
                           account.account_id)
            continue
        cuentas.append((
            account.account_id,
            account.owner,
            account.family_name,
            account.doc_id,
            account.state,
            float(round(account.balance, 2)),
        ))

    prestamos = []
    for loan in projection.loans.values():
        cuota = hypotekas.cuota_mensual(loan.capital, loan.interest_rate,
                                        loan.months)
        prestamos.append((
            loan.account_id,
            loan.loan_id,
            float(loan.capital),
            float(loan.interest_rate),
            loan.start.isoformat(),
            loan.end.isoformat(),
            cuota,
            loan.months,
            loan.months,
            float(loan.capital),
            1 if loan.is_credit else 0,
        ))

    projection.loans_without_account = guardar_proyeccion(cuentas, prestamos)
    for loan_id in projection.loans_without_account:
        logger.warning("Préstamo %s omitido: su cuenta %s no existe en accounts",
                       loan_id, projection.loans[loan_id].account_id)
    logger.info("Proyección: %s eventos, %s ignorados, %s cuentas, %s préstamos, %s sin cuenta",
                projection.processed, len(projection.skipped),
                len(cuentas), len(prestamos), len(projection.loans_without_account))
    return projection


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
