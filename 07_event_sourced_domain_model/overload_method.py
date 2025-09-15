from functools import singledispatchmethod
from dataclasses import dataclass, field

@dataclass(frozen=True)
class CreateEvent:
    title: str
    body: str
    
@dataclass(frozen=True)
class CommentEvent:
    comment: str

@dataclass(frozen=True)
class CloseEvent:
    pass

@dataclass
class TicketState:
    title: str = field(default="")
    body: str = field(default="")
    comments: list[str] = field(default_factory=list)
    state: str = field(default="new")

    @singledispatchmethod
    def apply(self, arg):
        raise NotImplementedError("Unsupported type")

    @apply.register
    def _(self, event: CreateEvent):
        self.title = event.title
        self.body = event.body
        self.state = "open"
    
    @apply.register
    def _(self, event: CommentEvent):
        self.comments.append(event.comment)

    
    @apply.register
    def _(self, event: CloseEvent):
        self.state = "closed"



if __name__ == "__main__":
    ticket = TicketState()
    ticket.apply(CreateEvent(title="Bug #1", body="There is a bug"))
    ticket.apply(CommentEvent(comment="I am working on it"))
    ticket.apply(CommentEvent(comment="This is taking longer than expected"))
    ticket.apply(CommentEvent(comment="Almost done"))
    ticket.apply(CommentEvent(comment="Fixed!"))
    ticket.apply(CloseEvent())
    print(ticket) # TicketState(title='Bug #1', body='There is a bug', comments=['I am working on it', 'This is taking longer than expected', 'Almost done', 'Fixed!'], state='closed')