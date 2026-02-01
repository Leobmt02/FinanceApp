"""
SQLAlchemy Models for FinanceApp
Personal Finance Management Application

Models:
- User: User authentication and profile
- Transaction: Financial transactions (income/expenses)
- Installment: Credit card installments
- SavingsGoal: Savings objectives (cofrinhos)
"""

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Date, DateTime,
    Numeric, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


# ============================================
# ENUMS
# ============================================

class TransactionType(str, enum.Enum):
    """Types of financial transactions."""
    ENTRADA = "entrada"
    SAIDA_DEBITO = "saida_debito"
    SAIDA_CREDITO = "saida_credito"


class PaymentStatus(str, enum.Enum):
    """Payment status for installments."""
    PENDENTE = "pendente"
    PAGO = "pago"
    ATRASADO = "atrasado"


# ============================================
# USER MODEL
# ============================================

class User(Base):
    """
    User model for authentication and profile.
    
    Attributes:
        id: Primary key
        nome: Full name
        email: Unique email for login
        celular: Mobile phone number
        senha_hash: Bcrypt hashed password
        is_active: Account active status
        created_at: Account creation timestamp
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    celular = Column(String(20), nullable=True)
    senha_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    savings_goals = relationship(
        "SavingsGoal",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


# ============================================
# TRANSACTION MODEL
# ============================================

class Transaction(Base):
    """
    Financial transaction model.
    
    Supports three types:
    - entrada: Income (salary, investments, etc.)
    - saida_debito: Direct debit expense
    - saida_credito: Credit card expense (can have installments)
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        valor_total: Total transaction amount
        descricao: Description of the transaction
        categoria: Category (Alimentação, Moradia, Transporte, etc.)
        tipo: Transaction type (enum)
        data_compra: Purchase date
        num_parcelas: Number of installments (for credit)
        notas: Additional notes
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    valor_total = Column(Numeric(12, 2), nullable=False)
    descricao = Column(String(255), nullable=False)
    categoria = Column(String(50), nullable=False)
    tipo = Column(
        Enum(TransactionType),
        nullable=False,
        default=TransactionType.SAIDA_DEBITO
    )
    data_compra = Column(Date, nullable=False)
    num_parcelas = Column(Integer, default=1)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="transactions")
    installments = relationship(
        "Installment",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="Installment.numero_parcela"
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, tipo='{self.tipo}', valor={self.valor_total})>"


# ============================================
# INSTALLMENT MODEL
# ============================================

class Installment(Base):
    """
    Credit card installment model.
    
    Automatically generated when a 'saida_credito' transaction
    is created with multiple installments.
    
    Attributes:
        id: Primary key
        transacao_id: Foreign key to Transaction
        numero_parcela: Installment number (1, 2, 3...)
        total_parcelas: Total number of installments
        valor_parcela: Installment value
        data_vencimento: Due date
        status_pagamento: Payment status (pendente, pago, atrasado)
    """
    __tablename__ = "installments"

    id = Column(Integer, primary_key=True, index=True)
    transacao_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    numero_parcela = Column(Integer, nullable=False)
    total_parcelas = Column(Integer, nullable=False)
    valor_parcela = Column(Numeric(12, 2), nullable=False)
    data_vencimento = Column(Date, nullable=False, index=True)
    status_pagamento = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDENTE
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    transaction = relationship("Transaction", back_populates="installments")

    @property
    def parcela_formatada(self) -> str:
        """Returns formatted installment string like '1/12'."""
        return f"{self.numero_parcela}/{self.total_parcelas}"

    def __repr__(self):
        return f"<Installment(id={self.id}, parcela='{self.parcela_formatada}')>"


# ============================================
# SAVINGS GOAL MODEL
# ============================================

class SavingsGoal(Base):
    """
    Savings goal model (Cofrinhos).
    
    Allows users to create savings objectives and track progress.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        nome_objetivo: Goal name (e.g., "Viagem", "Reserva")
        descricao: Goal description
        valor_meta: Target amount
        valor_atual: Current saved amount
        data_limite: Target date to reach goal
        is_active: Whether the goal is still active
    """
    __tablename__ = "savings_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    nome_objetivo = Column(String(100), nullable=False)
    descricao = Column(Text, nullable=True)
    valor_meta = Column(Numeric(12, 2), nullable=False)
    valor_atual = Column(Numeric(12, 2), default=0)
    data_limite = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="savings_goals")

    @property
    def progress_percentage(self) -> float:
        """
        Calculate progress towards the goal.
        Returns percentage as a float (0.0 to 100.0).
        """
        if self.valor_meta and self.valor_meta > 0:
            progress = (float(self.valor_atual) / float(self.valor_meta)) * 100
            return min(progress, 100.0)  # Cap at 100%
        return 0.0

    @property
    def valor_restante(self) -> float:
        """Calculate remaining amount to reach the goal."""
        remaining = float(self.valor_meta) - float(self.valor_atual)
        return max(remaining, 0.0)

    def __repr__(self):
        return f"<SavingsGoal(id={self.id}, nome='{self.nome_objetivo}', progress={self.progress_percentage:.1f}%)>"
