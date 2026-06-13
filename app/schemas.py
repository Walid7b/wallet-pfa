from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BalanceResponse(BaseModel):
    username: str
    balance: float
    currency: str = "MAD"


class TransferRequest(BaseModel):
    to_username: str
    amount: float = Field(..., gt=0, description="Montant à transférer (> 0)")
    description: Optional[str] = None


class TransferResponse(BaseModel):
    message: str
    amount: float
    from_username: str
    to_username: str
    new_balance: float
