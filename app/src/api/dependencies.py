from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.src.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    settings = get_settings()
    valid_keys = {k.strip() for k in settings.api_keys.split(",") if k.strip()}
    if not valid_keys:
        return  # auth disabled — no keys configured
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
