import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.database import SessionLocal, init_db
from app.main import app

client = TestClient(app, follow_redirects=False)
PASSED = 0


def check(name, condition, extra=""):
    global PASSED
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {extra}" if extra and not condition else ""))
    if condition:
        PASSED += 1
    else:
        raise SystemExit(1)


def tx(id_, **kwargs):
    data = {
        "tx_type": "",
        "amount": "",
        "account_from": "",
        "account_to": "",
        "category": "",
        "comment": "",
        "date_time": "",
    }
    data.update(kwargs)
    url = f"/transactions/{id_}/edit" if id_ else "/transactions/create"
    return client.post(url, data=data)


def balance(name):
    with SessionLocal() as db:
        from app.models import Account

        return float(db.query(Account).filter(Account.name == name).first().balance)


with SessionLocal() as db:
    from app.models import Account, Transaction, User

    for m in (Transaction, Account, User):
        db.query(m).delete()
    db.commit()


init_db()

# --- гостевой доступ запрещён ---
r = client.get("/")
check("guest GET / -> redirect", r.status_code == 303 and r.headers["location"] == "/login", str(r.status_code))
r = client.post("/transactions/create", data={"tx_type": "income"})
check("guest POST /transactions/create -> redirect", r.status_code == 303)

# --- регистрация ---
r = client.get("/login")
check("GET /login renders", r.status_code == 200 and "Вход в JDBank" in r.text)
r = client.get("/register")
check("GET /register renders", r.status_code == 200 and "Регистрация" in r.text)

r = client.post("/register", data={"username": "alice", "password": "secret123", "password2": "secret123"})
check("register OK -> redirect to /", r.status_code == 303 and r.headers["location"] == "/")
r = client.get("/")
check("after register session works, page renders", r.status_code == 200 and "alice" in r.text)

r = client.post("/register", data={"username": "alice", "password": "xxxxxx", "password2": "xxxxxx"})
check("duplicate username rejected", r.status_code == 400)
r = client.post("/register", data={"username": "bob", "password": "123", "password2": "123"})
check("short password rejected", r.status_code == 400)
r = client.post("/register", data={"username": "bob", "password": "abc123", "password2": "abc999"})
check("mismatched passwords rejected", r.status_code == 400)

# --- логин/логаут ---
client.post("/logout")
r = client.post("/login", data={"username": "alice", "password": "wrong"})
check("wrong password rejected", r.status_code == 400)
r = client.post("/login", data={"username": "alice", "password": "secret123"})
check("login OK", r.status_code == 303 and r.headers["location"] == "/")
client.post("/logout")
r = client.get("/")
check("after logout guest redirected", r.status_code == 303)
client.post("/login", data={"username": "alice", "password": "secret123"})

# --- счета ---
r = client.post("/accounts/create", data={"name": "Наличные", "currency": "byn"})
check("create account (currency uppercased)", r.status_code == 303)
check("balance 0", balance("Наличные") == 0.0)
r = client.post("/accounts/create", data={"name": "Карта BYN", "currency": "BYN"})
check("create second account", r.status_code == 303)
r = client.post("/accounts/create", data={"name": "", "currency": "USD"})
check("empty account name rejected", r.status_code == 400)
page = client.get("/").text
check("accounts visible on page", "Наличные" in page and "Карта BYN" in page)

# --- транзакции ---
r = tx(None, tx_type="income", amount="100", account_to="1", category="Зарплата")
check("income 100", r.status_code == 303)
check("balance 100", balance("Наличные") == 100.0)

r = tx(None, tx_type="expense", amount="30", account_from="1", category="Еда")
check("expense 30", r.status_code == 303)
check("balance 70", balance("Наличные") == 70.0)

r = tx(None, tx_type="transfer", amount="20", account_from="1", account_to="2")
check("transfer 20", r.status_code == 303)
check("balance 50 / 20", balance("Наличные") == 50.0 and balance("Карта BYN") == 20.0)

r = tx(None, tx_type="income", amount="abc", account_to="1")
check("invalid amount rejected", r.status_code == 400)
r = tx(None, tx_type="income", amount="-5", account_to="1")
check("negative amount rejected", r.status_code == 400)
r = tx(None, tx_type="income", amount="10")
check("income without account rejected", r.status_code == 400)
r = tx(None, tx_type="expense", amount="10", account_to="1")
check("expense with only to-account rejected", r.status_code == 400)
r = tx(None, tx_type="transfer", amount="10", account_from="1", account_to="1")
check("transfer to same account rejected", r.status_code == 400)
r = tx(None, tx_type="transfer", amount="10", account_from="1")
check("transfer with one account rejected", r.status_code == 400)
r = tx(None, tx_type="income", amount="10", account_to="999")
check("foreign account id rejected", r.status_code == 400)

# --- даты ---
r = tx(None, tx_type="expense", amount="5", account_from="2", date_time="2026-08-01T10:30")
check("custom datetime accepted", r.status_code == 303)
r = tx(None, tx_type="expense", amount="5", account_from="2", date_time="not-a-date")
check("bad datetime rejected", r.status_code == 400)
check("balance 50 / 15", balance("Наличные") == 50.0 and balance("Карта BYN") == 15.0)

# --- редактирование ---
r = tx(1, tx_type="expense", amount="10", account_from="1")
check("edit tx #1 -> expense 10", r.status_code == 303)
check("balance after edit -60 / 15", balance("Наличные") == -60.0 and balance("Карта BYN") == 15.0)

# --- удаление транзакции ---
r = client.post("/transactions/2/delete")
check("delete tx #2 (expense 30)", r.status_code == 303)
check("balance after delete -30 / 15", balance("Наличные") == -30.0 and balance("Карта BYN") == 15.0)

# --- второй пользователь не трогает чужое ---
client.post("/logout")
client.post("/register", data={"username": "mallory", "password": "hunter22", "password2": "hunter22"})
r = client.post("/transactions/1/delete")
check("user2 cannot delete user1 tx", r.status_code == 303)
check("user1 balance intact", balance("Наличные") == -30.0)
r = client.post("/accounts/1/delete")
check("user2 cannot delete user1 account", r.status_code == 303)
check("user1 account intact", balance("Наличные") == -30.0)
r = tx(None, tx_type="income", amount="10", account_to="1")
check("user2 cannot use user1 account", r.status_code == 400)

# --- удаление счёта пересчитывает связанный счёт ---
client.post("/logout")
client.post("/login", data={"username": "alice", "password": "secret123"})
r = client.post("/accounts/2/delete")
check("delete account #2", r.status_code == 303)
check("balance after account delete -10", balance("Наличные") == -10.0)
with SessionLocal() as db:
    from app.models import Account

    check("deleted account gone", db.query(Account).filter(Account.name == "Карта BYN").first() is None)

print(f"\nALL STAGE-2 CHECKS PASSED ({PASSED})")