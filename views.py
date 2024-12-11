from sqlalchemy.orm import Session
from functools import wraps
from sqlalchemy.exc import IntegrityError

from config import app, templates
from db import get_db, User, Tour
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, Form, Depends, File, Response, UploadFile

def login_required(view):
    @wraps(view)
    async def wrapped(request: Request, *args, **kwargs):
        if not request.session.get('is_authenticated', False):
            return RedirectResponse('/login')
        return await view(request, *args, **kwargs)
    return wrapped

@app.get('/', response_class=HTMLResponse)
async def index(request: Request, db: Session=Depends(get_db)):
    tour = db.query(Tour).all()
    return templates.TemplateResponse('index.html', {'title': 'Home', 'tours': tour, 'request': request})

@app.get('/registration', response_class=HTMLResponse)
async def register(request: Request, is_invalid_data: bool = False):
    return templates.TemplateResponse('register.html', {'request': request, 'is_invalid_data': is_invalid_data})


@app.post('/registration')
async def register(
        request: Request,
        username: str = Form(),
        password: str = Form(),
        email: str = Form(),
        db: Session = Depends(get_db)
):
    user = User(username=username, password=password, email=email)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        return RedirectResponse('/registration?is_invalid_data=True', status_code=303)
    return RedirectResponse('/', status_code=303)