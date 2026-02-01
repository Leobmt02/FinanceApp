"""
Savings Goals Router for FinanceApp (Cofrinhos)

Endpoints:
- GET / - List all savings goals
- POST / - Create new savings goal
- GET /{id} - Get savings goal by ID
- PUT /{id} - Update savings goal
- DELETE /{id} - Delete savings goal
- POST /{id}/deposit - Deposit into savings goal
- POST /{id}/withdraw - Withdraw from savings goal
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from ..database import get_db
from ..models import SavingsGoal, User
from ..schemas import (
    SavingsGoalCreate, SavingsGoalRead, SavingsGoalUpdate,
    SavingsGoalDeposit, SavingsGoalWithdraw
)
from .auth import get_current_user

router = APIRouter()


# ============================================
# SAVINGS GOAL ENDPOINTS
# ============================================

@router.get("/", response_model=List[SavingsGoalRead])
async def list_savings_goals(
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all savings goals for the current user.
    
    - **active_only**: If true, only return active goals (default: true)
    """
    query = db.query(SavingsGoal).filter(SavingsGoal.user_id == current_user.id)
    
    if active_only:
        query = query.filter(SavingsGoal.is_active == True)
    
    goals = query.order_by(SavingsGoal.created_at.desc()).all()
    return goals


@router.post("/", response_model=SavingsGoalRead, status_code=status.HTTP_201_CREATED)
async def create_savings_goal(
    goal_data: SavingsGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new savings goal.
    
    - **nome_objetivo**: Goal name (e.g., "Viagem", "Reserva")
    - **descricao**: Goal description (optional)
    - **valor_meta**: Target amount
    - **valor_inicial**: Initial deposit (optional, default: 0)
    - **data_limite**: Target date (optional)
    """
    new_goal = SavingsGoal(
        user_id=current_user.id,
        nome_objetivo=goal_data.nome_objetivo,
        descricao=goal_data.descricao,
        valor_meta=goal_data.valor_meta,
        valor_atual=goal_data.valor_inicial,
        data_limite=goal_data.data_limite
    )
    
    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)
    
    return new_goal


@router.get("/{goal_id}", response_model=SavingsGoalRead)
async def get_savings_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific savings goal by ID.
    
    Returns the goal with progress_percentage and valor_restante calculated.
    """
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta não encontrada"
        )
    
    return goal


@router.put("/{goal_id}", response_model=SavingsGoalRead)
async def update_savings_goal(
    goal_id: int,
    goal_data: SavingsGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a savings goal.
    
    - **nome_objetivo**: Update name (optional)
    - **descricao**: Update description (optional)
    - **valor_meta**: Update target amount (optional)
    - **data_limite**: Update target date (optional)
    """
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta não encontrada"
        )
    
    if goal_data.nome_objetivo is not None:
        goal.nome_objetivo = goal_data.nome_objetivo
    if goal_data.descricao is not None:
        goal.descricao = goal_data.descricao
    if goal_data.valor_meta is not None:
        goal.valor_meta = goal_data.valor_meta
    if goal_data.data_limite is not None:
        goal.data_limite = goal_data.data_limite
    
    db.commit()
    db.refresh(goal)
    
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_savings_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a savings goal.
    
    Note: This permanently deletes the goal and its history.
    """
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta não encontrada"
        )
    
    db.delete(goal)
    db.commit()


# ============================================
# DEPOSIT / WITHDRAW ENDPOINTS
# ============================================

@router.post("/{goal_id}/deposit", response_model=SavingsGoalRead)
async def deposit_to_goal(
    goal_id: int,
    deposit: SavingsGoalDeposit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deposit money into a savings goal.
    
    - **valor**: Amount to deposit (must be positive)
    """
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta não encontrada"
        )
    
    if not goal.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta inativa não pode receber depósitos"
        )
    
    # Add deposit to current value
    goal.valor_atual = Decimal(str(goal.valor_atual)) + deposit.valor
    
    db.commit()
    db.refresh(goal)
    
    return goal


@router.post("/{goal_id}/withdraw", response_model=SavingsGoalRead)
async def withdraw_from_goal(
    goal_id: int,
    withdraw: SavingsGoalWithdraw,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Withdraw money from a savings goal.
    
    - **valor**: Amount to withdraw (must be positive and <= current value)
    """
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta não encontrada"
        )
    
    current_value = Decimal(str(goal.valor_atual))
    
    if withdraw.valor > current_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saldo insuficiente. Disponível: R$ {current_value:.2f}"
        )
    
    # Subtract withdrawal from current value
    goal.valor_atual = current_value - withdraw.valor
    
    db.commit()
    db.refresh(goal)
    
    return goal


@router.post("/{goal_id}/complete", response_model=SavingsGoalRead)
async def complete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a savings goal as completed/inactive.
    """
    goal = db.query(SavingsGoal).filter(
        SavingsGoal.id == goal_id,
        SavingsGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meta não encontrada"
        )
    
    goal.is_active = False
    db.commit()
    db.refresh(goal)
    
    return goal
