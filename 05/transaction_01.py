from datetime import datetime
class LogVisit:
    @staticmethod
    def execute(user_id: int, visited_on: datetime) -> None:
        try:
            db.begin_transaction()
            db.execute(
                "UPDATE Users SET last_visit = ? WHERE id = ?",
                (visited_on, user_id)
            )
            db.execute(
                "INSERT INTO VisitsLog(user_id, visited_on) VALUES (?, ?)",
                (user_id, visited_on)
            )
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        
            
