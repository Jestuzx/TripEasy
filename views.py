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
from datetime import datetime

def admin_required(view):
    @wraps(view)
    async def wrapped(request: Request, *args, **kwargs):
        user_id = request.session.get('user_id')
        is_admin = request.session.get('is_admin', False)
        print(f"Admin check: user_id={user_id}, is_admin={is_admin}")
        if not user_id or not is_admin:
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

    # Fetch the bookings related to the user
    bookings = db.query(Booking).filter(Booking.user_id == user.id).all()

    return templates.TemplateResponse(
        'profile.html',
        {
            'request': request,
            'user': user,
            'bookings': bookings
        }
    )


@app.post('/profile', response_class=HTMLResponse)
@login_required
async def update_profile(
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

    # Return the updated user and the success message to the template
    success_message = "Profile updated successfully!"
    bookings = db.query(Booking).filter(Booking.user_id == user.id).all()

    return templates.TemplateResponse(
        'profile.html',
        {
            'request': request,
            'user': user,
            'bookings': bookings,
            'success_message': success_message
        }
    )


@app.get("/admin/tours", response_class=HTMLResponse)
@login_required
@admin_required
async def get_admin_tours(request: Request, db: Session = Depends(get_db)):
    tours = db.query(Tour).all()
    return templates.TemplateResponse("admin_tours.html", {"request": request, "tours": tours})

@app.post('/admin/create-tour')
@admin_required
@login_required
async def create_tour(request: Request, price: str = Form(), text: str = Form(), image: UploadFile = File(), db: Session = Depends(get_db)):
    image_path = f'static/images/{image.filename}'
    with open(image_path, 'wb') as file:
        shutil.copyfileobj(image.file, file)

    tour = Tour(text=text, price=price, image=image_path)
    db.add(tour)
    db.commit()
    db.refresh(tour)

    return JSONResponse(content={
        "message": "Tour created successfully",
        "id": tour.id,
        "text": tour.text,
        "price": tour.price,
        "image": tour.image
    })


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
    # Fetch the tour by ID
    tour = db.query(Tour).filter(Tour.id == tour_id).first()
    if not tour:
        return templates.TemplateResponse(
            "error.html",  # Создайте error.html, если у вас его нет
            {"request": request, "message": "Tour not found!"}
        )
    return templates.TemplateResponse(
        "bookTour.html",  # Рендерим страницу бронирования с деталями тура
        {"request": request, "tour": tour}
    )


@app.post('/book-tour/{tour_id}', response_class=HTMLResponse)
async def process_payment(
        request: Request,
        tour_id: int,
        card_number: str = Form(...),
        card_expiry: str = Form(...),
        card_cvc: str = Form(...),
        people_count: int = Form(...),
        tour_date: str = Form(...),
        db: Session = Depends(get_db)
):

    tour = db.query(Tour).filter(Tour.id == tour_id).first()
    if not tour:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "Tour not found!"}
        )


    total_price = tour.price * people_count


    user = get_current_user(request, db)
    if not user:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "message": "User not found!"}
        )


    try:
        tour_date_obj = datetime.strptime(tour_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    booking = Booking(
        user_id=user.id,
        tour_id=tour.id,
        people_count=people_count,
        tour_date=tour_date_obj,
        total_price=total_price
    )

    db.add(booking)
    db.commit()

    print(
        f"Tour '{tour.text}' booked successfully by {user.username} for {people_count} people! Total Price: ${total_price}")

    return RedirectResponse(url="/profile", status_code=303)


@app.post('/cancel-booking')
@login_required
async def cancel_booking(request: Request, db: Session = Depends(get_db), booking_id: int = Form(...)):
    # Get the user ID from the session
    user_id = request.session.get('user_id')

    # Find the booking by its ID
    booking = db.query(Booking).filter(Booking.id == booking_id).first()

    if not booking:
        return JSONResponse({'success': False, 'message': 'Booking not found.'})

    # Check if the current user is the one who made the booking
    if booking.user_id != user_id:
        return JSONResponse({'success': False, 'message': 'You are not authorized to cancel this booking.'})

    # Delete the booking and commit the changes
    db.delete(booking)
    db.commit()

    return JSONResponse({'success': True, 'message': 'Booking canceled successfully!'})


@app.post('/search')
async def search(inp: str = Form(...), db: Session = Depends(get_db)):
    tours = db.query(Tour).filter(Tour.text.ilike(f'%{inp}%')).all()
    results = [{
        'id': tour.id,
        'text': tour.text,
        'image': tour.image,
        'price': tour.price
    } for tour in tours]

    return JSONResponse(content={"result": results})