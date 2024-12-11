from sqlalchemy.orm import Session
from functools import wraps

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