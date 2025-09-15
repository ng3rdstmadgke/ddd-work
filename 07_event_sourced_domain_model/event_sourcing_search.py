from functools import singledispatchmethod
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, computed_field
from datetime import datetime
import enum
import json


#################################################
# Value Object
#################################################

class LeadID(BaseModel):
    value: str
    model_config = ConfigDict(frozen=True)

class Name(BaseModel):
    value: str
    model_config = ConfigDict(frozen=True)
    
class LeadStatusEnum(str, enum.Enum):
    NEW_LEAD = "new_lead"
    FOLLOWUP_SET = "followup_set"
    PENDING_PAYMENT = "pending_payment"
    CONVERTED = "converted"
    CLOSED = "closed"

class LeadStatus(BaseModel):
    value: LeadStatusEnum
    model_config = ConfigDict(frozen=True)

class PhoneNumber(BaseModel):
    value: str
    model_config = ConfigDict(frozen=True)


class LeadEvent(BaseModel):
    lead_id: LeadID
    event_id: int
    timestamp: datetime
    model_config = ConfigDict(frozen=True)

class LeadInitializedEvent(LeadEvent):
    name: Name
    phone_number: PhoneNumber
    status: LeadStatus = Field(default=LeadStatus(value=LeadStatusEnum.NEW_LEAD))

class ContactedEvent(LeadEvent):
    pass

class FollowupSetEvent(LeadEvent):
    status: LeadStatus = Field(default=LeadStatus(value=LeadStatusEnum.FOLLOWUP_SET))

class ContactDetailsChangedEvent(LeadEvent):
    name: Name
    phone_number: PhoneNumber

class OrderSubmittedEvent(LeadEvent):
    status: LeadStatus = Field(default=LeadStatus(value=LeadStatusEnum.PENDING_PAYMENT))

class PaymentConfirmedEvent(LeadEvent):
    status: LeadStatus = Field(default=LeadStatus(value=LeadStatusEnum.CONVERTED))


#################################################
# Entity・Aggregate
#################################################
class LeadStateModelProjection(BaseModel):
    lead_id: LeadID
    __names: dict[Name, bool] = PrivateAttr(default_factory=dict)
    status: LeadStatus
    __phone_numbers: dict[PhoneNumber, bool] = PrivateAttr(default_factory=dict)
    follow_up_on: datetime | None = Field(default=None)
    created_on: datetime | None = Field(default=None)
    updated_on: datetime | None = Field(default=None)
    version: int = Field(default=0)

    model_config = ConfigDict(
        extra="forbid",           # インスタンス化時に未定義の属性があるとエラーにする
        validate_assignment=True, # 属性の再代入時にもバリデーションを行う
    )

    @computed_field
    @property
    def name(self) -> Name | None:
        if self.__names:
            return next(reversed(self.__names))
        return None

    @computed_field
    @property
    def phone_number(self) -> PhoneNumber | None:
        if self.__phone_numbers:
            return next(reversed(self.__phone_numbers))
        return None

    def search_name(self, name: Name) -> bool:
        return name in self.__names

    def search_phone_number(self, phone_number: PhoneNumber) -> bool:
        return phone_number in self.__phone_numbers

    # NOTE: メソッドのオーバーロードにsingledispatchmethodを使用
    @singledispatchmethod
    def apply(self, event):
        raise TypeError("Unsupported event type")

    # NOTE: 各イベントに対応するapplyメソッドを定義
    @apply.register
    def _(self, event: LeadInitializedEvent):
        self.lead_id = event.lead_id
        self.__names[event.name] = True
        self.status = event.status
        self.__phone_numbers[event.phone_number] = True
        self.created_on = event.timestamp
        self.updated_on = event.timestamp
        self.version = 0

    @apply.register
    def _(self, event: ContactedEvent):
        self.updated_on = event.timestamp
        self.follow_up_on = None
        self.version += 1

    @apply.register
    def _(self, event: FollowupSetEvent):
        self.updated_on = event.timestamp
        self.follow_up_on = event.timestamp
        self.status = event.status
        self.version += 1

    @apply.register
    def _(self, event: ContactDetailsChangedEvent):
        self.__names[event.name] = True
        self.__phone_numbers[event.phone_number] = True
        self.updated_on = event.timestamp
        self.version += 1

    @apply.register
    def _(self, event: OrderSubmittedEvent):
        self.status = event.status
        self.updated_on = event.timestamp
        self.version += 1

    @apply.register
    def _(self, event: PaymentConfirmedEvent):
        self.status = event.status
        self.updated_on = event.timestamp
        self.version += 1

if __name__ == "__main__":
    # events.jsonからイベントを読み込む
    script_dir = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
    with open(f"{script_dir}/events.json", "r", encoding="utf-8") as f:
        events_json = json.load(f)

    # イベントをLeadEventインスタンスに変換
    events = []
    for event in events_json:
        event_type = event["event-type"]
        lead_id = LeadID(value=str(event["lead-id"]))
        event_id = event["event-id"]
        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
        if event_type == "新規登録":
            e = LeadInitializedEvent(
                lead_id=lead_id,
                event_id=event_id,
                name=Name(value=event["name"]),
                phone_number=PhoneNumber(value=event["phone-number"]),
                timestamp=timestamp,
            )
        elif event_type == "架電":
            e = ContactedEvent(lead_id=lead_id, event_id=event_id, timestamp=timestamp)
        elif event_type == "商談予定設定":
            e = FollowupSetEvent(lead_id=lead_id, event_id=event_id, timestamp=timestamp)
        elif event_type == "連絡先変更":
            e = ContactDetailsChangedEvent(
                lead_id=lead_id,
                event_id=event_id,
                name=Name(value=event["name"]),
                phone_number=PhoneNumber(value=event["phone-number"]),
                timestamp=timestamp,
            )
        elif event_type == "注文受領":
            e = OrderSubmittedEvent(lead_id=lead_id, event_id=event_id, timestamp=timestamp)
        elif event_type == "支払完了":
            e = PaymentConfirmedEvent(lead_id=lead_id, event_id=event_id, timestamp=timestamp)
        else:
            raise ValueError(f"Unknown event type: {event_type}")
        events.append(e)

    # イベントID順でソート
    sorted(events, key=lambda e: e.event_id)


    lead_state = LeadStateModelProjection(
        lead_id=LeadID(value=""),
        status=LeadStatus(value=LeadStatusEnum.NEW_LEAD),
    )

    # イベントを適用して状態を再構築
    for e in events:
        lead_state.apply(e)

    print(lead_state)