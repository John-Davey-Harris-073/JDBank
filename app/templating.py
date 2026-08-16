from fastapi.templating import Jinja2Templates

from .paths import templates_dir

templates = Jinja2Templates(directory=templates_dir())
templates.env.filters["money"] = lambda v: f"{v:,.2f}".replace(",", " ")