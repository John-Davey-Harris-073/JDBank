import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..templating import templates

router = APIRouter()

USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,50}$")


def _redirect(location: str) -> RedirectResponse:
    return RedirectResponse(location, status_code=303)


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return _redirect("/")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username.strip()).first()
    if user is None or not user.check_password(password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверное имя пользователя или пароль"},
            status_code=400,
        )
    request.session["user_id"] = user.id
    return _redirect("/")


@router.get("/register")
def register_page(request: Request):
    if request.session.get("user_id"):
        return _redirect("/")
    return templates.TemplateResponse(
        "register.html", {"request": request, "error": None}
    )


@router.post("/register")
def register(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    password2: str = Form(""),
    db: Session = Depends(get_db),
):
    username = username.strip()
    error = None

    if not USERNAME_RE.match(username):
        error = "Имя пользователя: 3–50 символов (буквы, цифры, _, -)"
    elif len(password) < 6:
        error = "Пароль должен содержать минимум 6 символов"
    elif len(password) > 72:
        error = "Пароль слишком длинный (максимум 72 символа)"
    elif password != password2:
        error = "Пароли не совпадают"
    elif db.query(User).filter(User.username == username).first():
        error = "Это имя пользователя уже занято"

    if error:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": error}, status_code=400
        )

    user = User(username=username)
    user.set_password(password)
    db.add(user)
    db.commit()

    request.session["user_id"] = user.id
    return _redirect("/")


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return _redirect("/login")