from datetime import datetime
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_user
from ..models import Account, Transaction, User
from ..services import recalc_account_balance
from ..templating import templates

router = APIRouter()

DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


def _redirect(location: str) -> RedirectResponse:
    return RedirectResponse(location, status_code=303)


def _account_of_user(db: Session, account_id, user: User):
    if not account_id:
        return None
    account = db.get(Account, account_id)
    if account is None or account.user_id != user.id:
        return None
    return account


def _validate_transaction(
    db: Session,
    user: User,
    tx_type: str,
    amount_raw: str,
    from_id,
    to_id,
    date_time_raw: str,
):
    if tx_type not in ("income", "expense", "transfer"):
        return "Неизвестный тип транзакции"

    try:
        amount = Decimal(amount_raw.strip())
    except (InvalidOperation, AttributeError):
        return "Укажите корректную сумму"
    if amount <= 0:
        return "Сумма должна быть больше нуля"

    account_from = _account_of_user(db, from_id, user)
    account_to = _account_of_user(db, to_id, user)

    if tx_type == "income" and account_to is None:
        return "Для дохода укажите счёт"
    if tx_type == "expense" and account_from is None:
        return "Для расхода укажите счёт"
    if tx_type == "transfer":
        if account_from is None or account_to is None:
            return "Для перевода укажите оба счёта"
        if account_from.id == account_to.id:
            return "Нельзя переводить на тот же счёт"

    if date_time_raw:
        try:
            datetime.strptime(date_time_raw, DATETIME_FORMAT)
        except ValueError:
            return "Неверный формат даты"

    return None


def _transaction_fields(
    db: Session,
    user: User,
    tx_type: str,
    amount_raw: str,
    from_id,
    to_id,
    date_time_raw: str,
    category: str,
    comment: str,
):
    account_from = _account_of_user(db, from_id, user)
    account_to = _account_of_user(db, to_id, user)
    amount = Decimal(amount_raw)
    date_time = (
        datetime.strptime(date_time_raw, DATETIME_FORMAT)
        if date_time_raw
        else datetime.now()
    )
    return {
        "type": tx_type,
        "amount": amount,
        "account_from_id": account_from.id if account_from else None,
        "account_to_id": account_to.id if account_to else None,
        "category": category.strip()[:100] if category.strip() else None,
        "comment": comment.strip()[:500] if comment.strip() else None,
        "date_time": date_time,
    }


@router.post("/transactions/create")
def create_transaction(
    request: Request,
    tx_type: str = Form(""),
    amount: str = Form(""),
    account_from: str = Form(""),
    account_to: str = Form(""),
    category: str = Form(""),
    comment: str = Form(""),
    date_time: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    tx_type = tx_type.strip().lower()
    from_id = account_from.strip() or None
    to_id = account_to.strip() or None

    error = _validate_transaction(
        db, user, tx_type, amount, from_id, to_id, date_time
    )
    if error:
        return templates.TemplateResponse(
            "index.html", _context(request, db, user, error=error), status_code=400
        )

    fields = _transaction_fields(
        db, user, tx_type, amount, from_id, to_id, date_time, category, comment
    )
    transaction = Transaction(user_id=user.id, **fields)
    db.add(transaction)
    db.commit()

    for account_id in {fields["account_from_id"], fields["account_to_id"]}:
        if account_id is not None:
            recalc_account_balance(db, db.get(Account, account_id))
    db.commit()
    return _redirect("/")


@router.post("/transactions/{transaction_id}/edit")
def edit_transaction(
    transaction_id: int,
    request: Request,
    tx_type: str = Form(""),
    amount: str = Form(""),
    account_from: str = Form(""),
    account_to: str = Form(""),
    category: str = Form(""),
    comment: str = Form(""),
    date_time: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None or transaction.user_id != user.id:
        return _redirect("/")

    tx_type = tx_type.strip().lower()
    from_id = account_from.strip() or None
    to_id = account_to.strip() or None

    error = _validate_transaction(
        db, user, tx_type, amount, from_id, to_id, date_time
    )
    if error:
        return templates.TemplateResponse(
            "index.html", _context(request, db, user, error=error), status_code=400
        )

    old_account_ids = {transaction.account_from_id, transaction.account_to_id}

    fields = _transaction_fields(
        db, user, tx_type, amount, from_id, to_id, date_time, category, comment
    )
    for key, value in fields.items():
        setattr(transaction, key, value)
    db.commit()

    for account_id in old_account_ids | {transaction.account_from_id, transaction.account_to_id}:
        if account_id is not None:
            recalc_account_balance(db, db.get(Account, account_id))
    db.commit()
    return _redirect("/")


@router.post("/transactions/{transaction_id}/delete")
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None or transaction.user_id != user.id:
        return _redirect("/")

    accounts = {transaction.account_from_id, transaction.account_to_id}

    db.delete(transaction)
    db.commit()

    for account_id in accounts:
        if account_id is not None:
            recalc_account_balance(db, db.get(Account, account_id))
    db.commit()
    return _redirect("/")


def _context(request: Request, db: Session, user: User, error: str = None, success: str = None):
    from .accounts import self_context

    return self_context(request, db, user, error=error, success=success)