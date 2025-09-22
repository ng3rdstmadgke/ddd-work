from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import hashlib

from domain.errors import DuplicateEmailError
from application.ports import PasswordHasher
from application.dto import CreateUserInput, UserOutput
from application.use_cases.list_users import ListUsersUseCase, CreateUserUseCase
from application.http.fastapi.schemas import CreateUserRequest, UserResponse
from adapters.db.sqlalchemy.uow import SQLAlchemyUnitOfWork

app = FastAPI()

engine = create_engine("mysql+pymysql://root:root1234@127.0.0.1:3306/sample?charset=utf8mb4", echo=False)
SessionLocal = sessionmaker(autocommit = False, autoflush = True, bind=engine)

class SimplePasswordHasher(PasswordHasher):
    def hash(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

def get_create_user_uc():
    return CreateUserUseCase(
        uow=SQLAlchemyUnitOfWork(SessionLocal),
        hasher=SimplePasswordHasher(),
    )

def get_list_users_uc():
    return ListUsersUseCase(uow=SQLAlchemyUnitOfWork(SessionLocal))


@app.get("/api/users", response_model=list[UserResponse])
def users(uc: ListUsersUseCase = Depends(get_list_users_uc)):
    return uc.execute()


@app.post("/api/users", response_model=UserResponse)
def create_user(
    data: CreateUserRequest,
    uc: CreateUserUseCase = Depends(get_create_user_uc)
):
    try:
        out = uc.execute(CreateUserInput(**data.model_dump()))
        return out
    except DuplicateEmailError as e:
        raise HTTPException(status_code=409, detail="email already exists")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal server error")
