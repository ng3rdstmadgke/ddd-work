from pydantic import BaseModel, Field

class Message(BaseModel):
    from_user: int
    to: int
    content: str
    was_read: bool = False

    def mark_as_read(self):
        self.was_read = True

class Ticket(BaseModel):

    is_escalated: bool
    remaining_time_percentage: float
    assigned_agent: int

    messages: list[Message] = Field(default_factory=list)

    def evaluate_automatic_actions(self):
        if (
            self.is_escalated and
            self.remaining_time_percentage < 0.5 and
            self.get_unread_messages_count(self.assigned_agent) > 0
        ):
            agent = self.assign_new_agent()
        
    
    def get_unread_messages_count(self, user_id: int) -> int:
        count = len([
            msg for msg in self.messages 
            if msg.to == user_id and not msg.was_read
        ])
        return count

    def assign_new_agent(self) -> int:
        return 1
    
    