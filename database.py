from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

# Используем psycopg3 connection string
engine = create_engine(config.DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://'))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    bonus_balance = Column(Integer, default=0)
    registration_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    date = Column(String(20))
    time = Column(String(10))
    guests = Column(Integer)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class RedemptionRequest(Base):
    __tablename__ = "redemption_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    amount = Column(Integer)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()