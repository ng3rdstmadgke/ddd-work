from pydantic import BaseModel, ConfigDict

class UserId(BaseModel);
    value: int
    model_config = ConfigDict(frozen=True)

class ProductId(BaseModel):
    value: int
    model_config = ConfigDict(frozen=True)

class Message(BaseModel):
    pass

class Ticket(BaseModel):
    customer: UserId
    products: list[ProductId]
    assigned_agent: UserId
    messages: list[Message]