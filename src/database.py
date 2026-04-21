"""
Database configuration and models
"""

from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

from src.config import settings

# Database setup
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    api_keys = relationship("APIKey", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    signals = relationship("Signal", back_populates="user")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    exchange = Column(String)
    encrypted_key = Column(String)
    encrypted_secret = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="api_keys")
    __table_args__ = (Index('idx_user_exchange', 'user_id', 'exchange', unique=True),)

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    name = Column(String)
    type = Column(String)
    config = Column(JSON)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    strategy_id = Column(String, ForeignKey("strategies.id"))
    exchange = Column(String)
    symbol = Column(String)
    side = Column(String)
    price = Column(Float)
    size = Column(Float)
    fee = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    source = Column(String)
    asset = Column(String)
    direction = Column(String)
    confidence = Column(Float)
    rationale = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="signals")

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True)
    action = Column(String)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables (only if database is available)
try:
    Base.metadata.create_all(bind=engine)
except Exception:
    # Database not available during import - will be created on first connection
    pass
