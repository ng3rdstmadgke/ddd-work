from pydantic import BaseModel, Field, computed_field, ConfigDict
from datetime import datetime
from functools import singledispatchmethod
import enum
from uuid import uuid4, UUID

class TicketID(BaseModel):
    value: UUID = Field(default_factory=uuid4)
    model_config = ConfigDict(frozen=True)

class DomainEvent(BaseModel):
    timestamp: datetime

class InitializedEvent(DomainEvent):
    pass

class EscalatedEvent(DomainEvent):
    pass

class ClosedEvent(DomainEvent):
    pass

class TicketStateEnum(str, enum.Enum):
    OPEN = "open"
    ESCALATED = "escalated"
    CLOSED = "closed"

################################
# Entity
################################

class TicketState(BaseModel):
    id: TicketID
    version: int = Field(default=0)
    state: TicketStateEnum = Field(default=TicketStateEnum.OPEN)
    remaining_time_percentage: float = Field(default=100.0)
    is_escalated: bool = Field(default=False)

    @singledispatchmethod
    def apply(self, event: DomainEvent):
        raise NotImplementedError("Subclasses must implement apply method")

    @apply.register
    def _(self, event: InitializedEvent):
        # 初期化イベント: OPEN に設定しエスカレートフラグは False
        self.state = TicketStateEnum.OPEN
        self.version = 0
        self.is_escalated = False

    @apply.register
    def _(self, event: EscalatedEvent):
        self.state = TicketStateEnum.ESCALATED
        self.version += 1
        self.is_escalated = True

    @apply.register
    def _(self, event: ClosedEvent):
        self.state = TicketStateEnum.CLOSED
        self.version += 1

################################
# 集約
################################
class Ticket(BaseModel):
    domain_events: list[DomainEvent] = Field(default_factory=list)
    state: TicketState

    @classmethod
    def from_events(cls, ticket_id: TicketID, events: list[DomainEvent]):
        ticket = cls(state=TicketState(id=ticket_id), domain_events=[])
        # 永続化されている過去イベントで状態を再構築 (domain_events には積まない)
        for event in events:
            ticket.state.apply(event)
        return ticket

    def append_event(self, event: DomainEvent, record: bool = True):
        if record:
            self.domain_events.append(event)
        self.state.apply(event)

    def request_escalation(self):
        # OPEN かつまだエスカレートしていない場合にのみエスカレート
        if self.state.state == TicketStateEnum.OPEN and not self.state.is_escalated:
            escalated_event = EscalatedEvent(timestamp=datetime.now())
            self.append_event(escalated_event)

    @property
    def version(self) -> int:
        return self.state.version



################################
# リポジトリ
################################
class TicketsRepository:
    def __init__(self):
        self.store = {}  # In-memory store, in real-world use a database

    def load_events(self, ticket_id: TicketID) -> list[DomainEvent]:
        return self.store.get(ticket_id.value, [])

    def save_events(self, ticket_id: TicketID, events: list[DomainEvent], expected_version: int):
        current_events = self.store.get(ticket_id.value, [])

        if len(current_events) != expected_version:
            raise ValueError("Concurrency conflict detected")
        current_events.extend(events)
        self.store[ticket_id.value] = current_events

    def commit_changes(self, ticket: Ticket, original_version: int):
        self.save_events(ticket.state.id, ticket.domain_events, original_version)
        ticket.domain_events.clear()

class TicketAPI:
    def __init__(self, tickets_repository: TicketsRepository):
        self.tickets_repository = tickets_repository

    def request_escalation(self, id: TicketID):
        # イベントを取得
        events = self.tickets_repository.load_events(id)
        # 集約を再構築
        ticket = Ticket.from_events(id, events)
        # 楽観的排他制御のため、現在のバージョンを保存
        original_version = ticket.version
        # エスカレーションコマンドを実行
        ticket.request_escalation()
        # 変更を保存
        self.tickets_repository.commit_changes(ticket, original_version)


if __name__ == "__main__":
    repo = TicketsRepository()
    ticket_id = TicketID()

    # チケットIDを生成
    events: list[DomainEvent] = [
        InitializedEvent(timestamp=datetime.now())
    ]
    ticket = Ticket.from_events(ticket_id, events)
    print(ticket.state)  # id=TicketID(value=UUID('...')) version=0 state=<TicketStateEnum.OPEN: 'open'> remaining_time_percentage=100.0 is_escalated=False

    # チケットの初期化イベントを保存
    repo.commit_changes(ticket, original_version=0)

    # エスカレーション要求
    api = TicketAPI(tickets_repository=repo)
    api.request_escalation(ticket_id)

    # チケットの状態を確認
    events = repo.load_events(ticket_id)
    ticket = Ticket.from_events(ticket_id, events)
    print(ticket.state)  # id=TicketID(value=UUID('...')) version=1 state=<TicketStateEnum.ESCALATED: 'escalated'> remaining_time_percentage=100.0 is_escalated=True