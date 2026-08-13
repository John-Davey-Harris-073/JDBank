import os

from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.filters["money"] = lambda v: f"{v:,.2f}".replace(",", " ")