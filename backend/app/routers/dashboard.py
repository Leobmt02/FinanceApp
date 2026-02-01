"""
Dashboard Router for FinanceApp

Endpoints:
- GET /summary - Get monthly financial summary
- GET /categories - Get expenses by category for a month
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import List
from decimal import Decimal
from datetime import date

from ..database import get_db
from ..models import Transaction, Installment, SavingsGoal, User, TransactionType, PaymentStatus
from ..schemas import DashboardSummary, DashboardCategorySummary, CategorySummary
from .auth import get_current_user

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    mes: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    ano: int = Query(..., ge=2000, description="Ano"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get financial summary for a specific month.
    
    Returns:
    - **total_entradas**: Sum of all income (entrada) transactions
    - **total_saidas**: Sum of debit expenses + credit installments due this month
    - **total_guardado**: Sum of all SavingsGoal current values
    - **saldo_disponivel**: total_entradas - total_saidas
    """
    
    # Calculate total income (entradas) for the month
    total_entradas = db.query(func.coalesce(func.sum(Transaction.valor_total), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.tipo == TransactionType.ENTRADA,
        extract('month', Transaction.data_compra) == mes,
        extract('year', Transaction.data_compra) == ano
    ).scalar()
    
    # Calculate debit expenses for the month
    total_debito = db.query(func.coalesce(func.sum(Transaction.valor_total), 0)).filter(
        Transaction.user_id == current_user.id,
        Transaction.tipo == TransactionType.SAIDA_DEBITO,
        extract('month', Transaction.data_compra) == mes,
        extract('year', Transaction.data_compra) == ano
    ).scalar()
    
    # Calculate credit installments due in the month
    total_parcelas = db.query(func.coalesce(func.sum(Installment.valor_parcela), 0)).join(
        Transaction
    ).filter(
        Transaction.user_id == current_user.id,
        extract('month', Installment.data_vencimento) == mes,
        extract('year', Installment.data_vencimento) == ano
    ).scalar()
    
    # Total expenses = debit + credit installments
    total_saidas = Decimal(str(total_debito)) + Decimal(str(total_parcelas))
    
    # Calculate total saved in all savings goals
    total_guardado = db.query(func.coalesce(func.sum(SavingsGoal.valor_atual), 0)).filter(
        SavingsGoal.user_id == current_user.id,
        SavingsGoal.is_active == True
    ).scalar()
    
    # Calculate available balance
    saldo_disponivel = Decimal(str(total_entradas)) - total_saidas
    
    return DashboardSummary(
        mes=mes,
        ano=ano,
        total_entradas=Decimal(str(total_entradas)),
        total_saidas=total_saidas,
        total_guardado=Decimal(str(total_guardado)),
        saldo_disponivel=saldo_disponivel
    )


@router.get("/categories", response_model=DashboardCategorySummary)
async def get_expenses_by_category(
    mes: int = Query(..., ge=1, le=12),
    ano: int = Query(..., ge=2000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get expense breakdown by category for a specific month.
    
    Returns the distribution of expenses (debit + credit installments)
    across categories with percentage calculations.
    """
    
    # Get debit expenses by category
    debit_by_category = db.query(
        Transaction.categoria,
        func.sum(Transaction.valor_total).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.tipo == TransactionType.SAIDA_DEBITO,
        extract('month', Transaction.data_compra) == mes,
        extract('year', Transaction.data_compra) == ano
    ).group_by(Transaction.categoria).all()
    
    # Get credit installments by category (through transaction)
    credit_by_category = db.query(
        Transaction.categoria,
        func.sum(Installment.valor_parcela).label('total')
    ).join(Installment).filter(
        Transaction.user_id == current_user.id,
        extract('month', Installment.data_vencimento) == mes,
        extract('year', Installment.data_vencimento) == ano
    ).group_by(Transaction.categoria).all()
    
    # Combine both into a dictionary
    category_totals = {}
    
    for cat, total in debit_by_category:
        category_totals[cat] = category_totals.get(cat, Decimal('0')) + Decimal(str(total))
    
    for cat, total in credit_by_category:
        category_totals[cat] = category_totals.get(cat, Decimal('0')) + Decimal(str(total))
    
    # Calculate grand total
    grand_total = sum(category_totals.values()) or Decimal('1')  # Avoid division by zero
    
    # Build category summaries with percentages
    categorias = []
    for categoria, valor in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        percentual = (float(valor) / float(grand_total)) * 100
        categorias.append(CategorySummary(
            categoria=categoria,
            valor_total=valor,
            percentual=round(percentual, 2)
        ))
    
    return DashboardCategorySummary(
        mes=mes,
        ano=ano,
        total=grand_total if grand_total != Decimal('1') else Decimal('0'),
        categorias=categorias
    )


@router.get("/recent-transactions", response_model=List[dict])
async def get_recent_transactions(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the most recent transactions for the dashboard.
    """
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).order_by(Transaction.data_compra.desc()).limit(limit).all()
    
    result = []
    for t in transactions:
        status = "CONFIRMADO"
        if t.tipo == TransactionType.ENTRADA:
            status = "RECEBIDO"
        elif t.tipo == TransactionType.SAIDA_CREDITO:
            pending = any(i.status_pagamento == PaymentStatus.PENDENTE for i in t.installments)
            status = "PENDENTE" if pending else "CONFIRMADO"
        
        result.append({
            "id": t.id,
            "descricao": t.descricao,
            "categoria": t.categoria,
            "tipo": t.tipo.value,
            "valor_total": float(t.valor_total),
            "data_compra": t.data_compra.isoformat(),
            "status": status
        })
    
    return result


@router.get("/savings-summary")
async def get_savings_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get summary of all savings goals.
    """
    goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == current_user.id,
        SavingsGoal.is_active == True
    ).all()
    
    total_guardado = sum(float(g.valor_atual) for g in goals)
    total_metas = sum(float(g.valor_meta) for g in goals)
    
    goals_summary = []
    for g in goals:
        goals_summary.append({
            "id": g.id,
            "nome": g.nome_objetivo,
            "valor_atual": float(g.valor_atual),
            "valor_meta": float(g.valor_meta),
            "progress": g.progress_percentage,
            "data_limite": g.data_limite.isoformat() if g.data_limite else None
        })
    
    return {
        "total_guardado": total_guardado,
        "total_metas": total_metas,
        "progress_geral": (total_guardado / total_metas * 100) if total_metas > 0 else 0,
        "goals": goals_summary
    }
