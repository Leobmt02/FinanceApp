"""
Transactions Router for FinanceApp

Endpoints:
- GET / - List all transactions
- POST / - Create new transaction (auto-generates installments for credit)
- GET /{id} - Get transaction by ID
- PUT /{id} - Update transaction
- DELETE /{id} - Delete transaction
- PUT /installments/{id} - Update installment status
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import date
from decimal import Decimal

from ..database import get_db
from ..models import Transaction, Installment, User, TransactionType, PaymentStatus
from ..schemas import (
    TransactionCreate, TransactionRead, TransactionUpdate,
    TransactionListItem, InstallmentRead, InstallmentUpdate,
    TransactionFilter, PaginatedResponse
)
from ..utils import calcular_datas_parcelas
from .auth import get_current_user

router = APIRouter()


# ============================================
# TRANSACTION ENDPOINTS
# ============================================

@router.get("/", response_model=List[TransactionListItem])
async def list_transactions(
    tipo: Optional[TransactionType] = None,
    categoria: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all transactions for the current user with optional filters.
    
    - **tipo**: Filter by transaction type
    - **categoria**: Filter by category
    - **data_inicio**: Filter from date
    - **data_fim**: Filter to date
    """
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    
    # Apply filters
    if tipo:
        query = query.filter(Transaction.tipo == tipo)
    if categoria:
        query = query.filter(Transaction.categoria == categoria)
    if data_inicio:
        query = query.filter(Transaction.data_compra >= data_inicio)
    if data_fim:
        query = query.filter(Transaction.data_compra <= data_fim)
    
    # Order by date descending and paginate
    transactions = query.order_by(desc(Transaction.data_compra)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # Add status to each transaction
    result = []
    for t in transactions:
        status = None
        if t.tipo == TransactionType.ENTRADA:
            status = "RECEBIDO"
        elif t.tipo == TransactionType.SAIDA_DEBITO:
            status = "CONFIRMADO"
        elif t.tipo == TransactionType.SAIDA_CREDITO:
            # Check if any installment is pending
            pending = any(i.status_pagamento == PaymentStatus.PENDENTE for i in t.installments)
            status = "PENDENTE" if pending else "CONFIRMADO"
        
        item = TransactionListItem(
            id=t.id,
            descricao=t.descricao,
            categoria=t.categoria,
            tipo=t.tipo,
            valor_total=t.valor_total,
            data_compra=t.data_compra,
            num_parcelas=t.num_parcelas,
            status=status
        )
        result.append(item)
    
    return result


@router.post("/", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new transaction.
    
    For credit transactions (saida_credito), installments are automatically
    generated based on num_parcelas.
    
    - **valor_total**: Total transaction value
    - **descricao**: Description
    - **categoria**: Category
    - **tipo**: entrada, saida_debito, or saida_credito
    - **data_compra**: Purchase date
    - **num_parcelas**: Number of installments (for credit)
    - **notas**: Additional notes (optional)
    """
    # Create transaction
    new_transaction = Transaction(
        user_id=current_user.id,
        valor_total=transaction_data.valor_total,
        descricao=transaction_data.descricao,
        categoria=transaction_data.categoria,
        tipo=transaction_data.tipo,
        data_compra=transaction_data.data_compra,
        num_parcelas=transaction_data.num_parcelas,
        notas=transaction_data.notas
    )
    
    db.add(new_transaction)
    db.flush()  # Get the ID without committing
    
    # Auto-generate installments for credit transactions
    if transaction_data.tipo == TransactionType.SAIDA_CREDITO and transaction_data.num_parcelas > 0:
        parcelas = calcular_datas_parcelas(
            data_primeira_parcela=transaction_data.data_compra,
            num_parcelas=transaction_data.num_parcelas,
            valor_total=Decimal(str(transaction_data.valor_total))
        )
        
        for parcela in parcelas:
            installment = Installment(
                transacao_id=new_transaction.id,
                numero_parcela=parcela["numero_parcela"],
                total_parcelas=parcela["total_parcelas"],
                valor_parcela=parcela["valor_parcela"],
                data_vencimento=parcela["data_vencimento"],
                status_pagamento=PaymentStatus.PENDENTE
            )
            db.add(installment)
    
    db.commit()
    db.refresh(new_transaction)
    
    return new_transaction


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific transaction by ID with all installments.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada"
        )
    
    return transaction


@router.put("/{transaction_id}", response_model=TransactionRead)
async def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a transaction's editable fields.
    
    Note: valor_total, tipo, and num_parcelas cannot be changed after creation.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada"
        )
    
    if transaction_data.descricao is not None:
        transaction.descricao = transaction_data.descricao
    if transaction_data.categoria is not None:
        transaction.categoria = transaction_data.categoria
    if transaction_data.notas is not None:
        transaction.notas = transaction_data.notas
    
    db.commit()
    db.refresh(transaction)
    
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a transaction and all its installments.
    """
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transação não encontrada"
        )
    
    db.delete(transaction)
    db.commit()


# ============================================
# INSTALLMENT ENDPOINTS
# ============================================

@router.get("/installments/month", response_model=List[InstallmentRead])
async def get_installments_by_month(
    mes: int = Query(..., ge=1, le=12),
    ano: int = Query(..., ge=2000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all installments due in a specific month.
    """
    from sqlalchemy import extract
    
    installments = db.query(Installment).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        extract('month', Installment.data_vencimento) == mes,
        extract('year', Installment.data_vencimento) == ano
    ).order_by(Installment.data_vencimento).all()
    
    return installments


@router.put("/installments/{installment_id}", response_model=InstallmentRead)
async def update_installment_status(
    installment_id: int,
    status_data: InstallmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an installment's payment status.
    
    - **status_pagamento**: pendente, pago, or atrasado
    """
    installment = db.query(Installment).join(Transaction).filter(
        Installment.id == installment_id,
        Transaction.user_id == current_user.id
    ).first()
    
    if not installment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcela não encontrada"
        )
    
    installment.status_pagamento = status_data.status_pagamento
    db.commit()
    db.refresh(installment)
    
    return installment


@router.get("/categories", response_model=List[str])
async def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of categories used by the current user.
    """
    categories = db.query(Transaction.categoria).filter(
        Transaction.user_id == current_user.id
    ).distinct().all()
    
    return [c[0] for c in categories]
