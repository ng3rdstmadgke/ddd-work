from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from db import models
from uuid import uuid4

# (cd 08_architecture && poetry run uvicorn 4_layered_architecture:app --reload)
# http://127.0.0.1:8000/docs

engine = create_engine("mysql+pymysql://root:root1234@127.0.0.1:3306/sample?charset=utf8mb4", echo=False)
SessionLocal = sessionmaker(autocommit = False, autoflush = True, bind=engine)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

class UserSchema(BaseModel):
    name: str
    email: str

class CreateUserSchema(UserSchema):
    password: str

###################################
# サービス層
###################################

class UserService:
    @staticmethod
    def create_user(session: Session, data: CreateUserSchema) -> models.User:
        try:
            session.begin()
            user = models.User(
                id=str(uuid4()),
                name=data.name,
                email=data.email,
                password_hash=data.password
            )
            session.add(user)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        session.refresh(user)
        return user
    
    @staticmethod
    def list_users(session: Session) -> list[models.User]:
        return session.query(models.User).all()
    

####################################
# プレゼンテーション層
####################################

@app.get("/api/users", response_model=list[UserSchema])
def users(session: Session = Depends(get_session)):
    users = UserService.list_users(session)
    return users


@app.post("/api/users", response_model=UserSchema)
def create_user(
    data: CreateUserSchema,
    session: Session = Depends(get_session)
):
    user = UserService.create_user(session, data)
    return user
