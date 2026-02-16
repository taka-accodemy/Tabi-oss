from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from app.core.config import settings
from app.core.security import verify_token, get_password_hash, verify_password, User, UserInDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

# Mock user database - in production, this would be in a real database
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@chatbi.com",
        "hashed_password": get_password_hash("admin123"),
        "disabled": False,
    },
    "demo": {
        "username": "demo",
        "full_name": "Demo User",
        "email": "demo@chatbi.com",
        "hashed_password": get_password_hash("demo123"),
        "disabled": False,
    }
}

def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(token, credentials_exception)
    user = get_user(username=token_data.username)
    if user is None:
        # User might be a Google OAuth user whose session survived a server restart.
        # Return a basic user from token data since the JWT is valid.
        return User(
            username=token_data.username,
            email=token_data.username,
            full_name=None,
            disabled=False
        )
    return User(**user.dict())

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
