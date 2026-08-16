from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .config import config
from .database import get_db, init_db
from .deps import RedirectToLogin, require_user
from .models import Account, Transaction, User
from .paths import static_dir
from .routes import accounts, auth, transactions
from .templating import templates

app = FastAPI(title="JDBank")

app.add_middleware(
    SessionMiddleware,
    secret_key=config.SECRET_KEY,
    session_cookie=config.SESSION_COOKIE_NAME,
    max_age=config.SESSION_COOKIE_MAX_AGE,
    same_site="lax",
    https_only=config.SESSION_HTTPS_ONLY,
)

app.mount(
    "/static",
    StaticFiles(directory=static_dir(), check_dir=False),
    name="static",
)


@app.exception_handler(RedirectToLogin)
async def redirect_to_login(request: Request, exc: RedirectToLogin):
    return RedirectResponse("/login", status_code=303)


app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/download", response_class=HTMLResponse)
def download_page(request: Request, db: Session = Depends(get_db)):
    user = None
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
    return templates.TemplateResponse(
        "download.html",
        {"request": request, "user": user, "error": None, "success": None},
    )


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    accounts = (
        db.query(Account).filter(Account.user_id == user.id).order_by(Account.id).all()
    )
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id)
        .order_by(Transaction.date_time.desc(), Transaction.id.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "accounts": accounts,
            "transactions": transactions,
            "error": None,
            "success": None,
        },
    )