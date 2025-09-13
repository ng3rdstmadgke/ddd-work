from pydantic import BaseModel, field_validator, ConfigDict, Field
import uuid

##################################
# 値オブジェクト （エンティティの属性として使用）
##################################

class PersonID(BaseModel):
    value: uuid.UUID
    model_config = ConfigDict(frozen=True)

class Name(BaseModel):
    first_name: str
    last_name: str
    model_config = ConfigDict(frozen=True)


class PhoneNumber(BaseModel):
    number: str
    model_config = ConfigDict(frozen=True)

    @field_validator('number')
    @classmethod
    def check_phone_number_format(cls, v: str) -> str:
        if not v.isdigit() or len(v) not in {10, 11}:
            raise ValueError("Phone number must be 10 or 11 digits")
        return v

##################################
# エンティティ
##################################
class Person(BaseModel):
    id: PersonID = Field(default_factory=lambda: PersonID(value=uuid.uuid4()))
    name: Name
    phone_number: PhoneNumber

if __name__ == "__main__":
    person = Person(
        name=Name(first_name="John", last_name="Doe"),
        phone_number=PhoneNumber(number="09012345678")
    )
    print(person)