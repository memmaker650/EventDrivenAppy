"""
Catálogo de eventos del dominio bancario (única fuente de verdad).

Reglas:
- Un evento es un hecho inmutable del pasado (dataclass frozen).
- Los importes se guardan SIEMPRE en positivo; el signo lo decide
  BankAccount.apply() en domain.py.
- `event_type` es el nombre con el que se persiste el evento en la BD.
  NUNCA lo cambies una vez hay datos guardados. Los nombres "raros"
  ("Moneywithdraw", "demandMortgage"...) se mantienen tal cual para no
  romper los eventos existentes ni el código que filtra por tipo
  (database.load_eventsOfType, daemonInput, etc.).
- `aliases` traduce el nombre limpio del campo Python a la clave que ya
  existe en el JSON almacenado ("interest_rate" -> "interest_Rate").
"""
import logging
from dataclasses import dataclass, asdict, fields
from typing import Any, ClassVar, Dict, Tuple, Type

logger = logging.getLogger(__name__)

# nombre guardado en BD -> clase. Se rellena solo (ver Event.__init_subclass__).
EVENT_TYPES: Dict[str, Type["Event"]] = {}


class UnknownEventType(KeyError):
    """El tipo de evento leído de la BD no está en el catálogo."""


@dataclass(frozen=True)
class Event:
    event_type: ClassVar[str] = ""
    aliases: ClassVar[Dict[str, str]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "event_type" in cls.__dict__:
            if cls.event_type in EVENT_TYPES:
                raise ValueError(f"event_type duplicado: {cls.event_type}")
            EVENT_TYPES[cls.event_type] = cls

    def to_data(self) -> Dict[str, Any]:
        """Diccionario listo para serializar a JSON (con las claves legacy)."""
        return {self.aliases.get(k, k): v for k, v in asdict(self).items()}

    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> "Event":
        """Reconstruye el evento; ignora claves desconocidas."""
        inverse = {v: k for k, v in cls.aliases.items()}
        valid = {f.name for f in fields(cls)}
        kwargs = {}
        for key, value in data.items():
            name = inverse.get(key, key)
            if name in valid:
                kwargs[name] = value
        return cls(**kwargs)


# ---------------------------------------------------------------- cuenta
@dataclass(frozen=True)
class AccountCreated(Event):
    event_type = "AccountCreated"
    account_id: str
    owner: str
    family_name: str = ""
    doc_id: str = ""
    state: str = "open"


@dataclass(frozen=True)
class AccountClosed(Event):
    event_type = "CloseAccount"
    account_id: str = ""  # los eventos antiguos solo guardaban amount
    amount: float = 0


# ---------------------------------------------------------------- dinero
@dataclass(frozen=True)
class MoneyDeposited(Event):
    event_type = "MoneyDeposited"
    account_id: str
    amount: float


@dataclass(frozen=True)
class MoneyWithdrawn(Event):
    event_type = "Moneywithdraw"  # legacy: w minúscula, se mantiene
    account_id: str
    amount: float


@dataclass(frozen=True)
class MoneyTransferred(Event):
    event_type = "MoneyTransfer"
    aliases = {"destination": "To"}
    account_id: str
    amount: float
    destination: str


@dataclass(frozen=True)
class CardPaid(Event):
    event_type = "CardPayment"
    amount: float
    shop: str
    account_id: str = ""  # los eventos antiguos no lo guardaban


@dataclass(frozen=True)
class OverdraftApplied(Event):
    event_type = "Overdraft"
    amount: float
    account_id: str = ""  # los eventos antiguos no lo guardaban


# ------------------------------------------------------------- hipotecas
_LOAN_ALIASES = {
    "interest_rate": "interest_Rate",
    "return_period": "return_Period",
    "initial_date": "initialDate",
}


@dataclass(frozen=True)
class MortgageDemanded(Event):
    event_type = "demandMortgage"
    aliases = _LOAN_ALIASES
    account_id: str
    mortgage_id: str
    interest_rate: float
    amount: float
    return_period: int
    initial_date: str


@dataclass(frozen=True)
class MortgagePaid(Event):
    event_type = "mortgagePayment"
    mortgage_id: str
    amount: float
    payment_date: str


@dataclass(frozen=True)
class MortgageAmortised(Event):
    event_type = "mortgageAmortisation"
    mortgage_id: str
    amount: float
    payment_date: str


# --------------------------------------------------------------- créditos
@dataclass(frozen=True)
class CreditDemanded(Event):
    event_type = "demandCredit"
    aliases = _LOAN_ALIASES
    account_id: str
    credit_id: str
    interest_rate: float
    amount: float
    return_period: int
    initial_date: str


@dataclass(frozen=True)
class CreditPaid(Event):
    event_type = "CreditPayment"
    credit_id: str
    amount: float
    payment_date: str


# ------------------------------------------------------------ serialización
def to_record(event: Event) -> Tuple[str, Dict[str, Any]]:
    """Evento -> (nombre_guardado, dict) para save_event()."""
    return event.event_type, event.to_data()


def from_record(event_type: str, data: Dict[str, Any]) -> Event:
    """(nombre_guardado, dict) leído de la BD -> evento."""
    try:
        cls = EVENT_TYPES[event_type]
    except KeyError:
        raise UnknownEventType(event_type) from None
    return cls.from_data(data)
