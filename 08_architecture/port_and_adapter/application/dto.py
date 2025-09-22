from pydantic import BaseModel

# DOT (Data Transfer Object - データ転送オブジェクト)

class CreateUserInput(BaseModel):
    name: str
    email: str
    password: str

class UserOutput(BaseModel):
    id: str
    name: str
    email: str
