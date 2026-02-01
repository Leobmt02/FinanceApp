"""
Pydantic Schemas for FinanceApp
Data validation and serialization for the API.

Schemas organized by module:
- User: Authentication and profile
- Transaction: Financial transactions
- Installment: Credit card installments
- SavingsGoal: Savings objectives
- Dashboard: Summary views
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, computed_field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# ============================================
# ENUMS
# ============================================

class TransactionType(str, Enum):
    """Types of financial transactions."""
    ENTRADA = "entrada"
    SAIDA_DEBITO = "saida_debito"
    SAIDA_CREDITO = "saida_credito"


class PaymentStatus(str, Enum):
    """Payment status for installments."""
    PENDENTE = "pendente"
    PAGO = "pago"
    ATRASADO = "atrasado"


# ============================================
# USER SCHEMAS
# ============================================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    nome: str = Field(..., min_length=2, max_length=100, description="Nome completo")
    email: EmailStr = Field(..., description="Email único para login")
    celular: Optional[str] = Field(None, max_length=20, description="Telefone celular")


class UserCreate(UserBase):
    """Schema for user registration."""
    senha: str = Field(..., min_length=6, description="Senha (mínimo 6 caracteres)")
    confirmar_senha: str = Field(..., description="Confirmação de senha")

    @field_validator('confirmar_senha')
    @classmethod
    def senhas_coincidem(cls, v: str, info) -> str:
        if 'senha' in info.data and v != info.data['senha']:
            raise ValueError('As senhas não coincidem')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    senha: str


class UserRead(BaseModel):
    """Schema for reading user data (excludes password)."""
    id: int
    nome: str
    email: EmailStr
    celular: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    celular: Optional[str] = Field(None, max_length=20)


class Token(BaseModel):
    """JWT Token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: Optional[int] = None
    email: Optional[str] = None


# ============================================
# INSTALLMENT SCHEMAS
# ============================================

class InstallmentBase(BaseModel):
    """Base installment schema."""
    numero_parcela: int = Field(..., ge=1, description="Número da parcela")
    total_parcelas: int = Field(..., ge=1, description="Total de parcelas")
    valor_parcela: Decimal = Field(..., ge=0, decimal_places=2)
    data_vencimento: date
    status_pagamento: PaymentStatus = PaymentStatus.PENDENTE


class InstallmentCreate(InstallmentBase):
    """Schema for creating an installment (internal use)."""
    transacao_id: int


class InstallmentRead(InstallmentBase):
    """Schema for reading installment data."""
    id: int
    transacao_id: int
    created_at: datetime

    @computed_field
    @property
    def parcela_formatada(self) -> str:
        """Returns formatted installment string like '1/12'."""
        return f"{self.numero_parcela}/{self.total_parcelas}"

    model_config = {"from_attributes": True}


class InstallmentUpdate(BaseModel):
    """Schema for updating installment status."""
    status_pagamento: PaymentStatus


# ============================================
# TRANSACTION SCHEMAS
# ============================================

class TransactionBase(BaseModel):
    """Base transaction schema with common fields."""
    valor_total: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        description="Valor total da transação"
    )
    descricao: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Descrição da transação"
    )
    categoria: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Categoria (Alimentação, Moradia, etc.)"
    )
    tipo: TransactionType = Field(
        ...,
        description="Tipo de transação"
    )
    data_compra: date = Field(..., description="Data da compra/transação")
    notas: Optional[str] = Field(None, description="Notas e observações")


class TransactionCreate(TransactionBase):
    """
    Schema for creating a transaction.
    
    For 'saida_credito', num_parcelas > 1 will automatically
    generate installment records.
    """
    num_parcelas: int = Field(
        default=1,
        ge=1,
        le=48,
        description="Número de parcelas (1-48)"
    )

    @field_validator('num_parcelas')
    @classmethod
    def validate_parcelas(cls, v: int, info) -> int:
        # Parcelas only make sense for credit transactions
        if 'tipo' in info.data:
            if info.data['tipo'] != TransactionType.SAIDA_CREDITO and v > 1:
                raise ValueError('Parcelamento só é permitido para transações de crédito')
        return v


class TransactionRead(TransactionBase):
    """Schema for reading transaction data with installments."""
    id: int
    user_id: int
    num_parcelas: int
    created_at: datetime
    installments: List[InstallmentRead] = []

    model_config = {"from_attributes": True}


class TransactionUpdate(BaseModel):
    """Schema for updating a transaction."""
    descricao: Optional[str] = Field(None, max_length=255)
    categoria: Optional[str] = Field(None, max_length=50)
    notas: Optional[str] = None


class TransactionListItem(BaseModel):
    """Simplified transaction for list views."""
    id: int
    descricao: str
    categoria: str
    tipo: TransactionType
    valor_total: Decimal
    data_compra: date
    num_parcelas: int
    status: Optional[str] = None  # CONFIRMADO, RECEBIDO, PENDENTE

    model_config = {"from_attributes": True}


# ============================================
# SAVINGS GOAL SCHEMAS
# ============================================

class SavingsGoalBase(BaseModel):
    """Base savings goal schema."""
    nome_objetivo: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Nome do objetivo (ex: Viagem, Reserva)"
    )
    descricao: Optional[str] = Field(None, description="Descrição do objetivo")
    valor_meta: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Valor da meta"
    )
    data_limite: Optional[date] = Field(None, description="Data limite para atingir meta")


class SavingsGoalCreate(SavingsGoalBase):
    """Schema for creating a savings goal."""
    valor_inicial: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        decimal_places=2,
        description="Valor inicial depositado"
    )


class SavingsGoalRead(SavingsGoalBase):
    """Schema for reading savings goal with progress."""
    id: int
    user_id: int
    valor_atual: Decimal
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def progress_percentage(self) -> float:
        """Calculate progress towards the goal (0-100)."""
        if self.valor_meta and self.valor_meta > 0:
            progress = (float(self.valor_atual) / float(self.valor_meta)) * 100
            return round(min(progress, 100.0), 2)
        return 0.0

    @computed_field
    @property
    def valor_restante(self) -> Decimal:
        """Calculate remaining amount to reach goal."""
        remaining = self.valor_meta - self.valor_atual
        return max(remaining, Decimal("0"))

    model_config = {"from_attributes": True}


class SavingsGoalUpdate(BaseModel):
    """Schema for updating a savings goal."""
    nome_objetivo: Optional[str] = Field(None, max_length=100)
    descricao: Optional[str] = None
    valor_meta: Optional[Decimal] = Field(None, gt=0)
    data_limite: Optional[date] = None


class SavingsGoalDeposit(BaseModel):
    """Schema for depositing into a savings goal."""
    valor: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Valor a depositar"
    )


class SavingsGoalWithdraw(BaseModel):
    """Schema for withdrawing from a savings goal."""
    valor: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        description="Valor a resgatar"
    )


# ============================================
# DASHBOARD SCHEMAS
# ============================================

class DashboardSummary(BaseModel):
    """
    Dashboard summary for a specific month/year.
    
    Calculation rules:
    - total_entradas: Sum of all 'entrada' transactions in the month
    - total_saidas: Sum of debit transactions + credit installments due in the month
    - total_guardado: Sum of valor_atual from all SavingsGoals
    - saldo_disponivel: total_entradas - total_saidas
    """
    mes: int = Field(..., ge=1, le=12)
    ano: int = Field(..., ge=2000)
    total_entradas: Decimal = Field(..., description="Total de receitas do mês")
    total_saidas: Decimal = Field(..., description="Total de despesas do mês")
    total_guardado: Decimal = Field(..., description="Total em cofrinhos")
    saldo_disponivel: Decimal = Field(..., description="Saldo disponível")

    @computed_field
    @property
    def variacao_percentual(self) -> Optional[float]:
        """Calculate percentage variation (income vs expenses)."""
        if self.total_entradas > 0:
            savings_rate = ((self.total_entradas - self.total_saidas) / self.total_entradas) * 100
            return round(float(savings_rate), 2)
        return None


class CategorySummary(BaseModel):
    """Summary of expenses by category."""
    categoria: str
    valor_total: Decimal
    percentual: float


class DashboardCategorySummary(BaseModel):
    """Dashboard category breakdown."""
    mes: int
    ano: int
    total: Decimal
    categorias: List[CategorySummary]


class BankAccountSummary(BaseModel):
    """Summary by bank/account (for future use)."""
    nome_banco: str
    saldo: Decimal
    gasto_mes: Decimal
    cor: Optional[str] = None  # For UI display


# ============================================
# PAGINATION & FILTERS
# ============================================

class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TransactionFilter(BaseModel):
    """Filter parameters for transactions."""
    tipo: Optional[TransactionType] = None
    categoria: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    valor_min: Optional[Decimal] = None
    valor_max: Optional[Decimal] = None


class PaginatedResponse(BaseModel):
    """Generic paginated response."""
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int
