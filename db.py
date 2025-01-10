from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///app.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    email = Column(String)
    is_admin = Column(Boolean, default=False)
    bookings = relationship("Booking", back_populates="user")

class Tour(Base):
    __tablename__ = "tours"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    price = Column(Integer)
    image = Column(String)

    bookings = relationship("Booking", back_populates="tour")

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    tour_id = Column(Integer, ForeignKey('tours.id'))
    people_count = Column(Integer, nullable=False)
    tour_date = Column(Date, nullable=False)
    total_price = Column(Float, nullable=False)

    user = relationship("User", back_populates="bookings")

    tour = relationship("Tour", back_populates="bookings")

