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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload = jwt.decode(token, cfg.SECRET_KEY, algorithms=[cfg.ALGORITHM])
    except JWTError as exc:
        raise TokenNotFoundException() from exc

    return payload


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = await decode_access_token(token=token)
    subject = payload.get(cfg.SUB)
    if not isinstance(subject, (str, int)) or isinstance(subject, bool):
        raise TokenNotFoundException()

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise TokenNotFoundException() from exc

    user = await UserDAO.get_by_user_id(user_id)
    if not user:
        raise UserNotFoundException
    return user
