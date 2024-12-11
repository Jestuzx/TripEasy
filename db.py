from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship


DATABASE_URL = 'sqlite:///app.db'

engine = create_engine(DATABASE_URL)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class ModelDateDataMixin(Base):
    __abstract__ = True

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    modifiedd_at = Column(DateTime(timezone=True), default=datetime.utcnow)

class User(ModelDateDataMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(256), nullable=False)
    email = Column(String(),nullable=False,unique=True)


class Tour(ModelDateDataMixin):
    __tablename__ = 'tour'

    id = Column(Integer,primary_key=True)
    text = Column(String(256), nullable=False)
    image = Column(Text, nullable=False)
