from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import uuid4, UUID

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
