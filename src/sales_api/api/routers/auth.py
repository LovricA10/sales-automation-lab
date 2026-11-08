from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from sales_api.api.deps import AuthServiceDep, CurrentUser
from sales_api.schemas import TokenOut, UserIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: UserIn, auth: AuthServiceDep) -> UserOut:
    user = auth.register(data)
    return UserOut(id=user.id, email=user.email)


@router.post("/token", response_model=TokenOut)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], auth: AuthServiceDep) -> TokenOut:
    # The OAuth2 standard calls this field "username"; here it holds the email.
    return TokenOut(access_token=auth.authenticate(form.username, form.password))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut(id=user.id, email=user.email)
