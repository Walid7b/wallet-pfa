from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(tags=["wallet"])


@router.get("/accounts/me/balance", response_model=schemas.BalanceResponse)
def get_balance(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    account = db.query(models.Account).filter(models.Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    return {"username": current_user.username, "balance": account.balance, "currency": "MAD"}


@router.post("/transfer", response_model=schemas.TransferResponse)
def transfer(
    payload: schemas.TransferRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if payload.to_username == current_user.username:
        raise HTTPException(status_code=400, detail="Impossible de se transférer à soi-même")

    sender_acc = db.query(models.Account).filter(models.Account.user_id == current_user.id).first()
    if not sender_acc:
        raise HTTPException(status_code=404, detail="Compte émetteur introuvable")

    if sender_acc.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Solde insuffisant")

    receiver_user = db.query(models.User).filter(models.User.username == payload.to_username).first()
    if not receiver_user:
        raise HTTPException(status_code=404, detail="Destinataire introuvable")

    receiver_acc = db.query(models.Account).filter(models.Account.user_id == receiver_user.id).first()
    if not receiver_acc:
        raise HTTPException(status_code=404, detail="Compte destinataire introuvable")

    sender_acc.balance -= payload.amount
    receiver_acc.balance += payload.amount

    tx = models.Transaction(
        sender_id=sender_acc.id,
        receiver_id=receiver_acc.id,
        amount=payload.amount,
        transaction_type=models.TransactionType.TRANSFER,
        description=payload.description,
    )
    db.add(tx)
    db.commit()

    return {
        "message": "Virement effectué avec succès",
        "amount": payload.amount,
        "from_username": current_user.username,
        "to_username": payload.to_username,
        "new_balance": sender_acc.balance,
    }
