from pydantic import BaseModel, field_validator, Field, ConfigDict , PrivateAttr, computed_field
from db import models as sa_models
from sqlalchemy import create_engine
from typing import Iterable
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

    # NOTE: ドメインのルールを破らずに永続化から復元するためのファクトリメソッド
    @classmethod
    def from_persistence(cls, id: OrderID, status: Status, items: Iterable[OrderItem]) -> "Order":
        o = cls(id=id)  # PENDING で初期化されるが、ここで上書きする
        setattr(o, f"_{cls.__name__}__status", status)  # PrivateAttr に直接セット
        setattr(o, f"_{cls.__name__}__items", list(items))
        return o

################################
# ドメインとSQLAlchemyの変換ヘルパ
################################

def _sa_to_domain_item(ri: sa_models.OrderItem) -> OrderItem:
    return OrderItem(
        id=OrderItemID(value=uuid.UUID(ri.id)),
        product_id=ProductID(value=uuid.UUID(ri.product_id)),
        quantity=Quantity(value=ri.quantity),
        unit_price=Money(amount=ri.unit_price),
    )

def _domain_to_sa_items(order_id: OrderID, items: Iterable[OrderItem]) -> list[sa_models.OrderItem]:
    out: list[sa_models.OrderItem] = []
    for it in items:
        out.append(
            sa_models.OrderItem(
                id=str(it.id.value),
                order_id=str(order_id.value),
                product_id=str(it.product_id.value),
                quantity=it.quantity.value,
                unit_price=it.unit_price.amount,
            )
        )
    return out

################################
# リポジトリ
################################
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

class OrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, order_id: OrderID) -> Order | None:
        sa = self.session.get(sa_models.Order, str(order_id.value))
        if not sa: return None
        dom_items = [_sa_to_domain_item(ri) for ri in sa.items]
        status = Status(value=StatusEnum(sa.status))
        return Order.from_persistence(id=OrderID(value=uuid.UUID(sa.id)), status=status, items=dom_items)

    def save(self, order: Order) -> None:
        # upsert 的に保存（子は置き換え。差分同期したければ工夫する）
        existing = self.session.get(sa_models.Order, str(order.id.value))
        if not existing:
            sa = sa_models.Order(
                id=str(order.id.value),
                status=order.status.value.value,  # Status(StatusEnum) → str
                items=_domain_to_sa_items(order.id, order.items),
            )
            self.session.add(sa)
        else:
            existing.status = order.status.value.value
            # 子の差し替え（delete-orphan が効く）
            existing.items[:] = _domain_to_sa_items(OrderID(value=uuid.UUID(existing.id)), order.items)

################################
# Unit of Work (トランザクション境界)
################################
class UnitOfWork:
    def __init__(self, session_factory):
        self._session_factory = session_factory
        self.session: Session | None = None
        self.orders: OrderRepository | None = None

    # __enter__ は with 文で使うときに呼ばれる
    def __enter__(self):
        self.session = self._session_factory()
        if not self.session:
            raise RuntimeError("failed to create session")
        self.orders = OrderRepository(self.session)
        return self

    # __exit__ は with 文で抜けるときに呼ばれる
    def __exit__(self, exc_type, exc, tb):
        if self.session is None:
            return
        if exc: 
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()

if __name__ == "__main__":
    engine = create_engine("mysql+pymysql://root:root1234@127.0.0.1:3306/sample?charset=utf8mb4", echo=False)
    sa_models.Base.metadata.create_all(engine)
    session_factory = lambda: Session(engine)

    # 1) ドメイン操作 (DBを意識しない)
    order = Order()
    order.add_item(product_id=ProductID(), quantity=Quantity(value=2), unit_price=Money(amount=1000))
    order.add_item(product_id=ProductID(), quantity=Quantity(value=1), unit_price=Money(amount=500))
    order.confirm()
    print(f"Order total: {order.total.amount}")  # 2500
    print(f"Order status: {order.status.value.value}")  # confirmed

    # 2) 永続化 (集約ルート単位で保存)
    with UnitOfWork(session_factory) as uow:
        if uow.orders is None:
            raise RuntimeError("repository not initialized")
        uow.orders.save(order)

    # 3) 復元 (集約ルート単位で取得)
    with UnitOfWork(session_factory) as uow:
        if uow.orders is None:
            raise RuntimeError("repository not initialized")
        loaded = uow.orders.get(order.id)
        assert loaded is not None
        print(f"Loaded order total: {loaded.total.amount}")  # 2500
        print(f"Loaded order status: {loaded.status.value.value}")  # confirmed