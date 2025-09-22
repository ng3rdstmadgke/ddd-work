from sqlalchemy.orm import sessionmaker, Session
from application.ports import UserRepository, UnitOfWork, PasswordHasher
from domain.user import User, UserId
from adapters.db.sqlalchemy import models

from uuid import uuid4, UUID


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
