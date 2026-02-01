"""
Utility Functions for FinanceApp

Includes:
- Password hashing and verification
- Installment date calculation
- JWT token generation
"""

from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any
import bcrypt
from jose import JWTError, jwt
import os

# ============================================
# PASSWORD HASHING
# ============================================


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Previously hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )


# ============================================
# JWT TOKEN FUNCTIONS
# ============================================

# Secret key - should be set via environment variable in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


# ============================================
# INSTALLMENT CALCULATION
# ============================================

def calcular_datas_parcelas(
    data_primeira_parcela: date,
    num_parcelas: int,
    valor_total: Decimal
) -> List[Dict[str, Any]]:
    """
    Calculate installment dates and values for credit purchases.
    
    This function automatically generates installment records with:
    - Sequential installment numbers (1/N, 2/N, etc.)
    - Due dates incremented by 1 month for each subsequent installment
    - Equal installment values (with rounding adjustment on the last installment)
    
    Args:
        data_primeira_parcela: Date of the first installment
        num_parcelas: Total number of installments (1-48)
        valor_total: Total transaction value
        
    Returns:
        List of dictionaries containing installment data:
        [
            {
                "numero_parcela": 1,
                "total_parcelas": 12,
                "valor_parcela": Decimal("99.99"),
                "data_vencimento": date(2024, 2, 15),
                "status_pagamento": "pendente"
            },
            ...
        ]
        
    Example:
        >>> parcelas = calcular_datas_parcelas(
        ...     data_primeira_parcela=date(2024, 1, 15),
        ...     num_parcelas=12,
        ...     valor_total=Decimal("1200.00")
        ... )
        >>> len(parcelas)
        12
        >>> parcelas[0]["parcela_formatada"]
        '1/12'
    """
    if num_parcelas < 1:
        raise ValueError("Número de parcelas deve ser pelo menos 1")
    
    if num_parcelas > 48:
        raise ValueError("Número máximo de parcelas é 48")
    
    if valor_total <= 0:
        raise ValueError("Valor total deve ser positivo")
    
    # Calculate base installment value (rounded to 2 decimal places)
    valor_parcela_base = (valor_total / num_parcelas).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )
    
    # Calculate the remainder to adjust the last installment
    valor_total_calculado = valor_parcela_base * num_parcelas
    diferenca = valor_total - valor_total_calculado
    
    parcelas = []
    
    for i in range(num_parcelas):
        # Calculate due date (add i months to the first date)
        data_vencimento = data_primeira_parcela + relativedelta(months=i)
        
        # Adjust the last installment value if there's a rounding difference
        if i == num_parcelas - 1 and diferenca != 0:
            valor_parcela = valor_parcela_base + diferenca
        else:
            valor_parcela = valor_parcela_base
        
        parcela = {
            "numero_parcela": i + 1,
            "total_parcelas": num_parcelas,
            "valor_parcela": valor_parcela,
            "data_vencimento": data_vencimento,
            "status_pagamento": "pendente"
        }
        
        parcelas.append(parcela)
    
    return parcelas


def get_parcelas_do_mes(
    parcelas: List[Dict[str, Any]],
    mes: int,
    ano: int
) -> List[Dict[str, Any]]:
    """
    Filter installments by month and year.
    
    Args:
        parcelas: List of installment dictionaries
        mes: Month (1-12)
        ano: Year
        
    Returns:
        Filtered list of installments due in the specified month
    """
    return [
        p for p in parcelas
        if p["data_vencimento"].month == mes and p["data_vencimento"].year == ano
    ]


# ============================================
# DATE UTILITIES
# ============================================

def get_primeiro_dia_mes(mes: int, ano: int) -> date:
    """Get the first day of a month."""
    return date(ano, mes, 1)


def get_ultimo_dia_mes(mes: int, ano: int) -> date:
    """Get the last day of a month."""
    if mes == 12:
        return date(ano + 1, 1, 1) - timedelta(days=1)
    return date(ano, mes + 1, 1) - timedelta(days=1)


def get_mes_anterior(mes: int, ano: int) -> tuple:
    """Get the previous month and year."""
    if mes == 1:
        return 12, ano - 1
    return mes - 1, ano


# ============================================
# FORMATTING UTILITIES
# ============================================

def format_currency_brl(valor: Decimal) -> str:
    """
    Format a decimal value as Brazilian Real currency.
    
    Args:
        valor: Decimal value
        
    Returns:
        Formatted string like "R$ 1.234,56"
    """
    valor_str = f"{valor:,.2f}"
    # Convert to Brazilian format
    valor_str = valor_str.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {valor_str}"


def parse_currency_brl(valor_str: str) -> Decimal:
    """
    Parse a Brazilian Real currency string to Decimal.
    
    Args:
        valor_str: String like "R$ 1.234,56" or "1234.56"
        
    Returns:
        Decimal value
    """
    # Remove currency symbol and spaces
    valor_str = valor_str.replace("R$", "").replace(" ", "").strip()
    # Convert from Brazilian format
    valor_str = valor_str.replace(".", "").replace(",", ".")
    return Decimal(valor_str)
