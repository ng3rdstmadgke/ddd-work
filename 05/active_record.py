class CreateUser:
    @staticmethod
    def execute(user_details: UserDetails) -> int:
        try:
            db.begin_transaction()
            user = new User()
            user.name = user_details.name
            user.email = user_details.email
            user.save()
            
            db.commit()
            db.refresh(user)
            return user.id
        except Exception as e:
            db.rollback()
            raise e