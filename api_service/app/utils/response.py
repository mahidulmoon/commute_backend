from typing import Any, Optional, Dict
from fastapi.responses import JSONResponse
from fastapi import status

def success_response(
    message: str = "Success",
    data: Optional[Any] = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "success",
            "message": message,
            "data": data
        }
    )

def error_response(
    message: str = "An error occurred",
    error: Optional[Any] = None,
    status_code: int = status.HTTP_400_BAD_REQUEST
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error",
            "message": message,
            "error": error
        }
    )
