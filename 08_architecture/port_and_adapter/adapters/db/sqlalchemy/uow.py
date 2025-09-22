from sqlalchemy.orm import sessionmaker, Session

from application.ports import UserRepository, UnitOfWork, PasswordHasher
from adapters.db.sqlalchemy.user_repository import SQLAlchemyUserRepository

# データベースの変更を伴う単一のビジネスロジック全体をラップするデザインパターン
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
