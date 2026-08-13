from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Account, Transaction

_INFLOW_TYPES = ("income", "transfer")
_OUTFLOW_TYPES = ("expense", "transfer")


def recalc_account_balance(db: Session, account: Account) -> None:
    inflow = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_to_id == account.id,
            Transaction.type.in_(_INFLOW_TYPES),
        )
    )
    outflow = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.account_from_id == account.id,
            Transaction.type.in_(_OUTFLOW_TYPES),
        )
    )
    account.balance = Decimal(inflow) - Decimal(outflow)
    db.add(account)