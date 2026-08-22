import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, Any

from jose import jwt
from src.config import Settings, get_settings
from src.database import User

cfg: Settings = get_settings()

def create_jwt_token(payload: Dict[str, Any], kind: str = "access") -> dict:
    to_encode = payload.copy()
    now = datetime.now(UTC)
    
    if kind == "access":
        expire = now + timedelta(minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES)
    else:
        expire = now + timedelta(minutes=cfg.REFRESH_TOKEN_EXPIRES_MINUTES)
        
    to_encode.update({
        cfg.EXP: expire,
        cfg.IAT: now,
        cfg.JTI: str(uuid.uuid4())
    })
    
    encoded_jwt = jwt.encode(to_encode, cfg.SECRET_KEY, algorithm=cfg.ALGORITHM)
    return {"token": encoded_jwt, "expire": expire, "jti": to_encode[cfg.JTI]}

def create_token_pair(user: User) -> dict:
    payload = {cfg.SUB: str(user.id)}
    access = create_jwt_token(payload, kind="access")
    refresh = create_jwt_token(payload, kind="refresh")
    return {"access": access, "refresh": refresh}
