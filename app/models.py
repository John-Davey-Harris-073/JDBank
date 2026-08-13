from datetime import datetime

import bcrypt
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from .database import Base

TRANSACTION_TYPES = ("income", "expense", "transfer")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    accounts = relationship(
        "Account", back_populates="owner", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="owner", cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                raw_password.encode("utf-8"), self.password_hash.encode("utf-8")
            )
        except ValueError:
            return False


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    currency = Column(String(10), nullable=False)
    balance = Column(Numeric(18, 2), nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="accounts")
    outgoing_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.account_from_id",
        back_populates="account_from",
        cascade="all, delete-orphan",
    )
    incoming_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.account_to_id",
        back_populates="account_to",
        cascade="all, delete-orphan",
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    account_from_id = Column(
        Integer, ForeignKey("accounts.id"), nullable=True, index=True
    )
    account_to_id = Column(
        Integer, ForeignKey("accounts.id"), nullable=True, index=True
    )
    type = Column(Enum(*TRANSACTION_TYPES, name="transaction_type"), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    category = Column(String(100), nullable=True)
    comment = Column(String(500), nullable=True)
    date_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="transactions")
    account_from = relationship(
        "Account", foreign_keys=[account_from_id], back_populates="outgoing_transactions"
    )
    account_to = relationship(
        "Account", foreign_keys=[account_to_id], back_populates="incoming_transactions"
    )