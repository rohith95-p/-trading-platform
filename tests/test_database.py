"""
Tests for database schema and models

This module tests database table creation, relationships, and constraints.
"""

import pytest
from src.data.models import User, APIKey, Strategy, Trade, Position, Signal, AuditLog
from datetime import datetime
import uuid

class TestUserTable:
    """Test users table"""
    
    def test_user_creation(self, test_db):
        """Test creating a user"""
        user = User(
            email="test@example.com",
            password_hash="hashed_password"
        )
        test_db.add(user)
        test_db.commit()
        
        retrieved_user = test_db.query(User).filter(User.email == "test@example.com").first()
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.max_strategies == 10
        assert retrieved_user.max_trades_per_day == 100
        assert retrieved_user.max_api_calls_per_hour == 1000
    
    def test_user_email_unique(self, test_db):
        """Test that email is unique"""
        user1 = User(email="test@example.com", password_hash="hash1")
        user2 = User(email="test@example.com", password_hash="hash2")
        
        test_db.add(user1)
        test_db.commit()
        
        test_db.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()

class TestAPIKeyTable:
    """Test api_keys table"""
    
    def test_api_key_creation(self, test_db):
        """Test creating an API key"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        api_key = APIKey(
            user_id=user.id,
            exchange="kalshi",
            key_nonce=b"nonce",
            key_encrypted=b"encrypted_key",
            secret_nonce=b"nonce",
            secret_encrypted=b"encrypted_secret"
        )
        test_db.add(api_key)
        test_db.commit()
        
        retrieved_key = test_db.query(APIKey).filter(APIKey.exchange == "kalshi").first()
        assert retrieved_key is not None
        assert retrieved_key.exchange == "kalshi"
        assert retrieved_key.is_valid == True
    
    def test_api_key_user_exchange_unique(self, test_db):
        """Test unique constraint on user_id and exchange"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        key1 = APIKey(
            user_id=user.id,
            exchange="kalshi",
            key_nonce=b"nonce",
            key_encrypted=b"key1",
            secret_nonce=b"nonce",
            secret_encrypted=b"secret1"
        )
        key2 = APIKey(
            user_id=user.id,
            exchange="kalshi",
            key_nonce=b"nonce",
            key_encrypted=b"key2",
            secret_nonce=b"nonce",
            secret_encrypted=b"secret2"
        )
        
        test_db.add(key1)
        test_db.commit()
        
        test_db.add(key2)
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()

class TestStrategyTable:
    """Test strategies table"""
    
    def test_strategy_creation(self, test_db):
        """Test creating a strategy"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        strategy = Strategy(
            user_id=user.id,
            name="Test Strategy",
            type="directional",
            config={"param1": "value1"}
        )
        test_db.add(strategy)
        test_db.commit()
        
        retrieved_strategy = test_db.query(Strategy).filter(Strategy.name == "Test Strategy").first()
        assert retrieved_strategy is not None
        assert retrieved_strategy.type == "directional"
        assert retrieved_strategy.is_active == False

class TestTradeTable:
    """Test trades table"""
    
    def test_trade_creation(self, test_db):
        """Test creating a trade"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        trade = Trade(
            user_id=user.id,
            exchange="kalshi",
            symbol="BTC/USD",
            side="buy",
            type="market",
            price=50000.00,
            size=1.0,
            fee=10.00
        )
        test_db.add(trade)
        test_db.commit()
        
        retrieved_trade = test_db.query(Trade).filter(Trade.symbol == "BTC/USD").first()
        assert retrieved_trade is not None
        assert retrieved_trade.side == "buy"
        assert retrieved_trade.price == 50000.00

class TestPositionTable:
    """Test positions table"""
    
    def test_position_creation(self, test_db):
        """Test creating a position"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        position = Position(
            user_id=user.id,
            exchange="kalshi",
            symbol="BTC/USD",
            size=1.0,
            avg_price=50000.00,
            current_price=51000.00
        )
        test_db.add(position)
        test_db.commit()
        
        retrieved_position = test_db.query(Position).filter(Position.symbol == "BTC/USD").first()
        assert retrieved_position is not None
        assert retrieved_position.size == 1.0
    
    def test_position_user_exchange_symbol_unique(self, test_db):
        """Test unique constraint on user_id, exchange, and symbol"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        pos1 = Position(
            user_id=user.id,
            exchange="kalshi",
            symbol="BTC/USD",
            size=1.0,
            avg_price=50000.00
        )
        pos2 = Position(
            user_id=user.id,
            exchange="kalshi",
            symbol="BTC/USD",
            size=2.0,
            avg_price=51000.00
        )
        
        test_db.add(pos1)
        test_db.commit()
        
        test_db.add(pos2)
        with pytest.raises(Exception):  # IntegrityError
            test_db.commit()

class TestSignalTable:
    """Test signals table"""
    
    def test_signal_creation(self, test_db):
        """Test creating a signal"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        signal = Signal(
            user_id=user.id,
            source="news",
            asset="BTC",
            direction="long",
            confidence=0.85,
            rationale="Bullish news"
        )
        test_db.add(signal)
        test_db.commit()
        
        retrieved_signal = test_db.query(Signal).filter(Signal.asset == "BTC").first()
        assert retrieved_signal is not None
        assert retrieved_signal.direction == "long"
        assert float(retrieved_signal.confidence) == 0.85

class TestAuditLogTable:
    """Test audit_log table"""
    
    def test_audit_log_creation(self, test_db):
        """Test creating an audit log"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        audit_log = AuditLog(
            user_id=user.id,
            action="user_login",
            details={"email": user.email}
        )
        test_db.add(audit_log)
        test_db.commit()
        
        retrieved_log = test_db.query(AuditLog).filter(AuditLog.action == "user_login").first()
        assert retrieved_log is not None
        assert retrieved_log.user_id == user.id

class TestRelationships:
    """Test model relationships"""
    
    def test_user_api_keys_relationship(self, test_db):
        """Test user to api_keys relationship"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        api_key = APIKey(
            user_id=user.id,
            exchange="kalshi",
            key_nonce=b"nonce",
            key_encrypted=b"key",
            secret_nonce=b"nonce",
            secret_encrypted=b"secret"
        )
        test_db.add(api_key)
        test_db.commit()
        
        retrieved_user = test_db.query(User).filter(User.email == "test@example.com").first()
        assert len(retrieved_user.api_keys) == 1
        assert retrieved_user.api_keys[0].exchange == "kalshi"
    
    def test_user_strategies_relationship(self, test_db):
        """Test user to strategies relationship"""
        user = User(email="test@example.com", password_hash="hash")
        test_db.add(user)
        test_db.commit()
        
        strategy = Strategy(
            user_id=user.id,
            name="Test",
            type="directional",
            config={}
        )
        test_db.add(strategy)
        test_db.commit()
        
        retrieved_user = test_db.query(User).filter(User.email == "test@example.com").first()
        assert len(retrieved_user.strategies) == 1
        assert retrieved_user.strategies[0].name == "Test"
