import os
import requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from app.logger import logger

security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY", "d2bcbac0d9e7f5ffaf6b0fd44d8042f7fd438d7b24ec5e2f31e3c74a6233bcf9")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
AUTH_VALIDATOR = os.getenv("AUTH_VALIDATOR", "http://192.168.0.100:8000/api/auth/verify_authentication")


def auth_token_validation(token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        AUTH_VALIDATOR,
        headers=headers,
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def validate_token_string(token: str) -> dict:
    try:
        try:
            auth_service_response = auth_token_validation(token)
            if (
                auth_service_response.get("status") == "success"
                and "data" in auth_service_response
                and "user_data" in auth_service_response["data"]
            ):
                return auth_service_response["data"]["user_data"]
        except Exception as net_err:
            logger.warning(f"Remote token verification failed or timed out: {net_err}. Attempting local decode.")

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_signature": True},
        )
        user_id = payload.get("id") or payload.get("user_id") or payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload: missing user identification")

        return {
            "id": int(user_id),
            "email": payload.get("email"),
            "username": payload.get("username"),
            "type": payload.get("type", "USER"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    return validate_token_string(token)
