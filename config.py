from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware


app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')
app.add_middleware(SessionMiddleware, secret_key='12345')

templates = Jinja2Templates(directory="templates")
