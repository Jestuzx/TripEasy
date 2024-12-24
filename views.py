from pydantic_core.core_schema import str_schema
from sqlalchemy.orm import Session
from functools import wraps
from sqlalchemy.exc import IntegrityError
from config import app, templates
from db import get_db, User, Tour, SessionLocal, Booking
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi import Request, Form, Depends, File, Response, UploadFile, HTTPException
import shutil
import os
from typing import Optional


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
@admin_required
async def tour_create(request: Request, price: str=Form(), text: str = Form(), image: UploadFile = File(), db: Session = Depends(get_db)):
    image_path = f'static/images/{image.filename}'
    with open(image_path, 'wb') as file:
        shutil.copyfileobj(image.file, file)

    tour = Tour(text=text, image=image_path, price=price)
    db.add(tour)
    db.commit()
    db.refresh(tour)

    return {"message": "Tour created successfully"}

@app.get("/admin/tours", response_class=HTMLResponse)
@admin_required
async def get_tours(request: Request, db: Session = Depends(get_db)):
    tours = db.query(Tour).all()
    return templates.TemplateResponse("admin_tours.html", {"request": request, "tours": tours})

@app.delete('/delete-tour/{tour_id}')
@admin_required
async def delete_tour(request: Request, tour_id: int, db: Session = Depends(get_db)):
    tour = db.query(Tour).filter(Tour.id == tour_id).first()

    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")

    db.delete(tour)
    db.commit()

    return {"message": "Tour deleted successfully"}

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    user_id = request.session.get('user_id')
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None

@app.get('/book-tour/{tour_id}', response_class=HTMLResponse)
async def book_tour(request: Request, tour_id: int, db: Session = Depends(get_db)):
    tour = db.query(Tour).filter(Tour.id == tour_id).first()
    if not tour:
        return {"message": "Tour not found!"}
    return templates.TemplateResponse('bookTour.html', {'request': request, 'tour': tour})


# app.py
@app.post('/book-tour/{tour_id}')
async def process_payment(request: Request, tour_id: int,
                          card_number: str = Form(...),
                          card_expiry: str = Form(...),
                          card_cvc: str = Form(...),
                          db: Session = Depends(get_db)):
    # Ищем тур по ID
    tour = db.query(Tour).filter(Tour.id == tour_id).first()

    if not tour:
        return {"message": "Tour not found!"}

    # Получаем текущего пользователя
    user = get_current_user(request, db)
    if not user:
        return {"message": "User not found!"}

    # Сохраняем информацию о бронировании
    booking = Booking(user_id=user.id, tour_id=tour.id)
    db.add(booking)
    db.commit()

    # Создаем сообщение для отображения
    message = f"Tour '{tour.text}' booked successfully by {user.username}!"

    # Отправляем сообщение и тур обратно на страницу
    return templates.TemplateResponse('bookTour.html', {
        'request': request,
        'tour': tour,
        'message': message
    })


@app.post('/cancel-booking')
@login_required
async def cancel_booking(request: Request, db: Session = Depends(get_db), booking_id: int = Form()):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return JSONResponse({'success': False, 'message': 'Booking not found.'})

    if booking.user_id != request.user.id:
        return JSONResponse({'success': False, 'message': 'You are not authorized to cancel this booking.'})

    db.delete(booking)
    db.commit()
    return JSONResponse({'success': True, 'message': 'Booking canceled successfully!'})
