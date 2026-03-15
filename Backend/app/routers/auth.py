from fastapi import APIRouter, HTTPException, Response

from app.exceptions import AccountBlockedError, AuthenticationError
from app.repositories.account_repository import AccountRepository
from app.schemas import LoginRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login")
async def login(payload: LoginRequest, response: Response) -> dict[str, str | int]:
    repository = AccountRepository()
    auth_service = AuthService(repository)

    try:
        account = await auth_service.authenticate(payload.login, payload.password)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except AccountBlockedError:
        raise HTTPException(status_code=403, detail="Account is blocked")

    token = auth_service.create_token(account)
    response.set_cookie(key="access_token", value=token, httponly=True, path="/")
    return {"message": "Authorized", "user_id": account.id}
