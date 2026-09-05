from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
import os, requests

security = HTTPBearer()
SECRET_KEY= os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def auth_token_validation(token):
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        os.getenv("AUTH_VALIDATOR"),
        headers=headers,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return data

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_signature": False},
        )

        auth_service_response = auth_token_validation(token)

        user_data = auth_service_response.get("data").get("user_data")
        user_id = auth_service_response.get("data").get("user_data").get("id")

        # print(user_email,user_id)

        if auth_service_response.get("status") and auth_service_response.get("status") == "success":
            pass
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        return user_data

    except HTTPException:
        raise

    except Exception as e:
        print(str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

def get_agent_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_signature": False},
        )

        auth_service_response = auth_token_validation(token)

        user_data = auth_service_response.get("data").get("user_data")
        user_id = auth_service_response.get("data").get("user_data").get("id")

        # print(user_email,user_id)

        if auth_service_response.get("status") and auth_service_response.get("status") == "success":
            pass
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        if user_data.get("type") == "AGENT":
            return user_data

        else:
            print(str(e))
            raise HTTPException(
                status_code=401,
                detail="Invalid token For agent"
            )

    except HTTPException:
        raise

    except Exception as e:
        print(str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )