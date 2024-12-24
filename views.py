from pydantic_core.core_schema import str_schema
from sqlalchemy.orm import Session
from functools import wraps
from sqlalchemy.exc import IntegrityError
from config import app, templates
from db import get_db, User, Tour, SessionLocal
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi import Request, Form, Depends, File, Response, UploadFile, HTTPException
import shutil
import os

def admin_required(view):
    @wraps(view)
    async def wrapped(request: Request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id or not request.session.get('is_admin', False):
            raise HTTPException(status_code=403, detail="Admin access required.")
        return await view(request, *args, **kwargs)
    return wrapped

def login_required(view):
    @wraps(view)
    async def wrapped(request: Request, *args, **kwargs):
        if not request.session.get('is_authenticated', False):
            return RedirectResponse('/login')
        return await view(request, *args, **kwargs)
    return wrapped

def grant_admin(username: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            print(f"User '{username}' not found!")
            return
        user.is_admin = True
        db.commit()
        print(f"User '{username}' is now an admin.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

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

@app.get('/login', response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@app.post('/login')
async def post_login(request: Request, username: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(username=username, password=password).first()
    if user is None:
        return RedirectResponse('/login', status_code=303)
    request.session['is_authenticated'] = True
    request.session['user_id'] = user.id
    request.session['is_admin'] = user.is_admin
    return RedirectResponse('/', status_code=303)


@app.get('/profile', response_class=HTMLResponse)
@login_required
async def profile(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).get(request.session['user_id'])
    return templates.TemplateResponse('profile.html', {'request': request, 'user': user})

@app.post('/profile', response_class=JSONResponse)
@login_required
async def profile(
        request: Request,
        username: str = Form(),
        email: str = Form(),
        db: Session = Depends(get_db)
):
    user = db.query(User).get(request.session['user_id'])
    user.username = username
    user.email = email
    db.commit()
    db.refresh(user)
    return {}

@app.get("/create-tour", response_class=HTMLResponse)
async def get_create_tour(request: Request):
    return templates.TemplateResponse("tourCreate.html", {"request": request})

@app.post('/create-tour')
async def tour_create(request: Request, text: str = Form(), image: UploadFile = File(), db: Session = Depends(get_db)):
    image_path = f'static/images/{image.filename}'
    with open(image_path, 'wb') as file:
        shutil.copyfileobj(image.file, file)

    tour = Tour(text=text, images=image_path)
    db.add(tour)
    db.commit()
    db.refresh(tour)

    return {"message": "Tour created successfully"}