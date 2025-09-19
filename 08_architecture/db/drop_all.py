from models import Base

from sqlalchemy import create_engine
engine = create_engine("mysql+pymysql://root:root1234@127.0.0.1:3306/sample?charset=utf8mb4", echo=False)
Base.metadata.drop_all(engine)