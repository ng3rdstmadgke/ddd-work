from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # リレーション
    orders: Mapped[list["Order"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="joined"
    )

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)           # UUIDをstr保存（RDBに合わせて型は調整）
    user_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1) # 楽観的な排他制御用のバージョン番号

    # リレーション
    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="joined"
    )

class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True
    )
    product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)

    # リレーション
    order: Mapped[Order] = relationship(back_populates="items")