from domain.user import User

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