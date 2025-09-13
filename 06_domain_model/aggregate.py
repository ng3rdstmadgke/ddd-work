from pydantic import BaseModel, field_validator, Field, ConfigDict , PrivateAttr, computed_field
import uuid
import enum
import copy

##################################
# 値オブジェクト （エンティティの属性として使用）
##################################
class Money(BaseModel):
    amount: int
    model_config = ConfigDict(frozen=True)

    @field_validator('amount')
    @classmethod
    def check_amount_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    def __add__(self, other: "Money") -> "Money":
        return Money(amount=self.amount + other.amount)
    

class Quantity(BaseModel):
    value: int
    model_config = ConfigDict(frozen=True)

    @field_validator('value')
    @classmethod
    def check_quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class OrderItemID(BaseModel):
    value: uuid.UUID = Field(default_factory=uuid.uuid4)
    model_config = ConfigDict(frozen=True)

class ProductID(BaseModel):
    value: uuid.UUID = Field(default_factory=uuid.uuid4)
    model_config = ConfigDict(frozen=True)

class OrderID(BaseModel):
    value: uuid.UUID = Field(default_factory=uuid.uuid4)
    model_config = ConfigDict(frozen=True)


class StatusEnum(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELED = "canceled"

# Enumはそのまま利用せずラップする
class Status(BaseModel):
    value: StatusEnum
    model_config = ConfigDict(frozen=True)

##################################
# エンティティ
##################################

class OrderItem(BaseModel):
    id: OrderItemID = Field(default_factory=OrderItemID)
    product_id: ProductID
    quantity: Quantity
    unit_price: Money
    model_config = ConfigDict(
        extra="forbid",           # インスタンス化時に未定義の属性があるとエラーにする
        validate_assignment=True, # 属性の再代入時にもバリデーションを行う
    )

    def change_quantity(self, new_quantity: Quantity):
        self.quantity = new_quantity
    
    @computed_field  # シリアライズ時にも "subtotal" として出力される
    @property
    def subtotal(self) -> Money:
        return Money(amount=self.unit_price.amount * self.quantity.value)

###################################
# 集約ルート (OrderItemはOrderを通じてのみ操作可能)
###################################

class Order(BaseModel):
    id: OrderID = Field(default_factory=OrderID)
    # PrivateAttr は pydantic のモデルフィールドとして扱われない非公開属性を定義する
    __items: list[OrderItem] = PrivateAttr(default_factory=list) 
    __status: Status = PrivateAttr(default_factory=lambda: Status(value=StatusEnum.PENDING))
    model_config = ConfigDict(
        extra="forbid",           # インスタンス化時に未定義の属性があるとエラーにする
        validate_assignment=True, # 属性の再代入時にもバリデーションを行う
    )

    def add_item(self, product_id: ProductID, quantity: Quantity, unit_price: Money):
        if self.__status.value != StatusEnum.PENDING:
            raise ValueError("cannot modify a non-pending order")
        
        for item in self.__items:
            if item.product_id == product_id:
                if item.unit_price != unit_price:
                    raise ValueError("unit price mismatch for the same product")
                item.change_quantity(
                    Quantity(value=item.quantity.value + quantity.value)
                )
                return
        item = OrderItem(
            id=OrderItemID(),
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price
        )
        self.__items.append(item)
    

    def confirm(self):
        if not self.__items:
            raise ValueError("cannot confirm empty order")
        self.__status = Status(value=StatusEnum.CONFIRMED)

    @computed_field  # シリアライズ時にも "status" として出力される
    @property
    def status(self) -> Status:
        return self.__status

    @computed_field  # シリアライズ時にも "items" として出力される
    @property
    def items(self) -> list[OrderItem]:
        # 外にリストを直接渡すと変更されてしまうのでコピーを返す
        return copy.deepcopy(self.__items)
    
    @computed_field
    @property
    def total(self) -> Money:
        total = Money(amount=0)
        for item in self.__items:
            total += item.subtotal
        return total

################################
# リポジトリ
################################

class OrderRepository:
    def __init__(self):
        self._orders = {}

    def save(self, order: Order):
        self._orders[order.id.value] = order

    def get(self, order_id: OrderID) -> Order | None:
        return self._orders.get(order_id.value)

if __name__ == "__main__":
    repo = OrderRepository()
    order = Order()
    order.add_item(product_id=ProductID(), quantity=Quantity(value=2), unit_price=Money(amount=1000))
    order.add_item(product_id=ProductID(), quantity=Quantity(value=1), unit_price=Money(amount=500))
    print(f"Order total before confirm: {order.total.amount}")  # 2500
    order.confirm()
    print(f"Order status after confirm: {order.status.value}")  # confirmed
    repo.save(order)
    fetched_order = repo.get(order.id)
    if fetched_order:
        print(f"Fetched order total: {fetched_order.total.amount}")  # 2500