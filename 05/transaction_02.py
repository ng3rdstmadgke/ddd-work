class LogVisit:
    @staticmethod
    def execute(user_id: int, visited_on: datetime) -> None:
        db.execute(
            "UPDATE Users SET last_visit = ? WHERE id = ?",
            (visited_on, user_id)
        )
        message_bus.publish(
            "VISITS_TOPIC",
            {"user_id": user_id, "visited_on": visited_on }
        )


class LogVisit:
    @staticmethod
    def execute(user_id: int) -> None:
        db.execute(
            "UPDATE Users SET visit = visits + 1 WHERE id = ?",
            (user_id)
        )

class LogVisit:
    @staticmethod
    def execute(user_id: int, visits: int) -> None:
        db.execute(
            "UPDATE Users SET visits = ? WHERE id = ?",
            (visits, user_id)
        )

class LogVisit:
    @staticmethod
    def execute(user_id: int, expected_visits: int) -> None:
        db.execute(
            "UPDATE Users SET visits = visits + 1 WHERE id = ? AND visits = ?",
            (user_id, expected_visits)
        )