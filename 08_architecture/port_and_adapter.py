from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import uuid4, UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db import models
import hashlib

# (cd 08_architecture && poetry run uvicorn port_and_adapter:app --reload)
# http://127.0.0.1:8000/docs

engine = create_engine("mysql+pymysql://root:root1234@127.0.0.1:3306/sample?charset=utf8mb4", echo=False)
SessionLocal = sessionmaker(autocommit = False, autoflush = True, bind=engine)


###################################
# 例外 (domain/errors.py)
###################################

class DomainError(Exception): ...
class DuplicateEmailError(DomainError): ...

###################################
# ドメインモデル
###################################

#
# 値オブジェクト
#
class UserId(BaseModel):
    value: UUID = Field(default_factory=uuid4)
    model_config = ConfigDict(frozen=True)

#
# エンティティ
#
class User(BaseModel):
    id: UserId
    name: str
    email: str
    password_hash: str
    
    def change_name(self, new_name: str):
        self.name = new_name

    @field_validator("email")
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v


###################################
# アプリケーション層
###################################

#
# ポート (application/ports.py)
#

from abc import ABC, abstractmethod

class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None: ...
    
    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...
    
    @abstractmethod
    def list_all(self) -> list[User]: ...

class UnitOfWork(ABC):
    @abstractmethod
    def __enter__(self) -> "UnitOfWork": ...

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback) -> None: ...

    @property
    @abstractmethod
    def users(self) -> UserRepository: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...

class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, raw: str) -> str: ...

#
# DTO(Data Transfer Object - データ転送オブジェクト) (application/dto.py)
#
class CreateUserInput(BaseModel):
    name: str
    email: str
    password: str

class UserOutput(BaseModel):
    id: str
    name: str
    email: str

#
# ユースケース
#

# application/use_cases/list_users.py
class CreateUserUseCase:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher):
        self.uow = uow
        self.hasher = hasher

    def execute(self, input: CreateUserInput) -> UserOutput:
        with self.uow:
            existing_user = self.uow.users.get_by_email(input.email)
            if existing_user:
                raise DuplicateEmailError(f"Email {input.email} is already in use.")
            user = User(
                id=UserId(),
                name=input.name,
                email=input.email,
                password_hash=self.hasher.hash(input.password)
            )
            self.uow.users.add(user)
            self.uow.commit()
            return UserOutput(
                id=str(user.id.value),
                name=user.name,
                email=user.email
            )

# application/use_cases/list_users.py
class ListUsersUseCase:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self) -> list[UserOutput]:
        with self.uow:
            users = self.uow.users.list_all()
            return [
                UserOutput(
                    id=str(user.id.value),
                    name=user.name,
                    email=user.email
                ) for user in users
            ]

###################################
# アダプター層
###################################

#
# リポジトリ (adapters/db/sqlalchemy/user_repository.py)
#
class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, user: User) -> None:
        user_model = models.User(
            id=str(user.id.value),
            name=user.name,
            email=user.email,
            password_hash=user.password_hash
        )
        self.session.add(user_model)

    def get_by_email(self, email: str) -> User | None:
        user_model = self.session.query(models.User).filter_by(email=email).first()
        if user_model:
            return User(
                id=UserId(value=UUID(user_model.id)),
                name=user_model.name,
                email=user_model.email,
                password_hash=user_model.password_hash
            )
        return None

    def list_all(self) -> list[User]:
        user_models = self.session.query(models.User).all()
        return [
            User(
                id=UserId(value=UUID(user_model.id)),
                name=user_model.name,
                email=user_model.email,
                password_hash=user_model.password_hash
            ) for user_model in user_models
        ]

#
# Unit of Work (adapters/db/sqlalchemy/uow.py)
# データベースの変更を伴う単一のビジネスロジック全体をラップするデザインパターン
#
class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory
        self.session: Session | None = None
        self._users: UserRepository | None = None

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        self.session = self._session_factory()
        assert self.session is not None, "UnitOfWork is not entered."
        self.session.begin()
        self._users = SQLAlchemyUserRepository(self.session)
        return self 

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        try:
            if exc_type:
                self.rollback()
            else:
                pass
        finally:
            if self.session:
                self.session.close()

    @property
    def users(self) -> UserRepository:
        assert self._users is not None, "UnitOfWork is not entered."
        return self._users

    def commit(self) -> None:
        assert self.session is not None, "UnitOfWork is not entered."
        self.session.commit()

    def rollback(self) -> None:
        assert self.session is not None, "UnitOfWork is not entered."
        self.session.rollback()

###################################
# 駆動アダプタ 
###################################

from fastapi import FastAPI, Depends, HTTPException

app = FastAPI()

#
# スキーマ (adapters/http/fastapi/schemas.py)
#
class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str

#
# API (adapters/http/fastapi/api.py)
#
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