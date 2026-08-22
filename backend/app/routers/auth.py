from fastapi import APIRouter, Depends, HTTPException, Body
from app.config.auth import create_access_token, get_current_user_id

router = APIRouter()

@router.post("/token")
def get_auth_token(payload: dict = Body(default={})):
    """
    Generates a cryptographically signed JWT access token for the given user_id.
    """
    user_id = payload.get("user_id", "user_default").strip()
    if not user_id:
        user_id = "user_default"
    
    token = create_access_token(user_id=user_id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id
    }

@router.get("/me")
def get_authenticated_user(user_id: str = Depends(get_current_user_id)):
    """
    Returns authenticated user profile details.
    """
    return {
        "user_id": user_id,
        "status": "authenticated"
    }
