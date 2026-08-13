from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_user
from ..models import Account, User
from ..services import recalc_account_balance
from ..templating import templates

router = APIRouter()


def _redirect(location: str) -> RedirectResponse:
    return RedirectResponse(location, status_code=303)


@router.post("/accounts/create")
def create_account(
    request: Request,
    name: str = Form(""),
    currency: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    name = name.strip()
    currency = currency.strip().upper()

    error = None
    if not name or len(name) > 100:
        error = "Укажите название счёта (до 100 символов)"
    elif not currency or len(currency) > 10:
        error = "Укажите тикер валюты (например, BYN, USD, BTC)"

    if error:
        return templates.TemplateResponse(
            "index.html", self_context(request, db, user, error=error), status_code=400
        )

    account = Account(name=name, currency=currency, user_id=user.id)
    db.add(account)
    db.commit()
    return _redirect("/")


@router.post("/accounts/{account_id}/delete")
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    account = db.get(Account, account_id)
    if account is None or account.user_id != user.id:
        return _redirect("/")

    related_ids = {
        t.account_from_id if t.account_from_id != account.id else t.account_to_id
        for t in account.outgoing_transactions + account.incoming_transactions
        if t.account_from_id != account.id or t.account_to_id != account.id
    }
    related_ids.discard(None)

    db.delete(account)
    db.commit()

    for acc_id in related_ids:
        related = db.get(Account, acc_id)
        if related and related.user_id == user.id:
            recalc_account_balance(db, related)
    db.commit()
    return _redirect("/")


def self_context(request: Request, db: Session, user: User, error: str = None, success: str = None):
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    return {
        "request": request,
        "user": user,
        "accounts": accounts,
        "error": error,
        "success": success,
    }