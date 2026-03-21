from fastapi import Depends, HTTPException, Request

from app.exceptions import AccountBlockedError, InvalidTokenError
from app.repositories.account_repository import AccountRepository
from app.schemas import Account
from app.services.auth_service import AuthService


def get_account_repository() -> AccountRepository:
    """Dependency to get AccountRepository instance."""
    return AccountRepository()


def get_auth_service(
    repository: AccountRepository = Depends(get_account_repository),
) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(repository)


async def get_current_account(request: Request) -> Account:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    repository = get_account_repository()
    auth_service = get_auth_service(repository=repository)

    try:
        payload = auth_service.verify_token(token)
        user_id = payload.get("user_id")
        if not isinstance(user_id, int):
            raise HTTPException(status_code=401, detail="Unauthorized")
        account = await repository.get_by_id(user_id)
        if account is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        if account.is_blocked:
            raise AccountBlockedError("Account is blocked")
        return account
    except (InvalidTokenError, AccountBlockedError):
        raise HTTPException(status_code=401, detail="Unauthorized")
