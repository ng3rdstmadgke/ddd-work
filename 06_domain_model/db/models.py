from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

class Base(DeclarativeBase): pass

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)           # UUIDをstr保存（RDBに合わせて型は調整）
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="joined"
    )

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(255), ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[Order] = relationship(back_populates="items")