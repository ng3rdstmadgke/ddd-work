from application.ports import UserRepository, UnitOfWork, PasswordHasher
from application.dto import CreateUserInput, UserOutput
from domain.errors import DuplicateEmailError
from domain.user import User, UserId

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