from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db_global
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
import os
from app.models.wo_user import User

security = HTTPBearer()
SECRET_KEY= os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_global),
):
    try:
        token = credentials.credentials

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_signature": False},
        )

        user_email = payload.get("sub")
        user_id = payload.get("user_id")

        if not user_email or not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user = (
            db.query(User)
            .filter(
                User.user_id == user_id,
                User.email == user_email
            )
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except HTTPException:
        raise

    except Exception as e:
        print(str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )