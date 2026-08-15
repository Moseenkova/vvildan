from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.config import Settings, get_settings
from src.dao import UserDAO
from src.database import User
from src.exceptions import (
    TokenNotFoundException,
    UserNotFoundException,
)

cfg: Settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
    except JWTError:
        raise TokenNotFoundException

    return payload

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = await decode_access_token(token=token)
    user_id = int(payload.get(cfg.SUB))
    user = await UserDAO.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException
    return user
