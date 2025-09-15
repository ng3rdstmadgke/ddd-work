from pydantic import BaseModel, Field, ConfigDict

class DomainEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

class TicketEscalated(DomainEvent):
    id: int
    reason: str

class Ticket(BaseModel):
    id: int
    is_escalated: bool
    remaining_time_percentage: float
    domain_events: list[DomainEvent] = Field(default_factory=list)  # ドメインイベントのリスト

    model_config = ConfigDict(frozen=True)

    # チケットをエスカレーションするために、ドメインイベントを追加
    def request_escalation(self, reason: str):
        if (not self.is_escalated and self.remaining_time_percentage <= 0):
            self.is_escalated = True
            escalated_event = TicketEscalated(id=self.id, reason=reason)
            self.domain_events.append(escalated_event)