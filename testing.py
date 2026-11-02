import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
from sqlalchemy import create_engine,Integer,Column,String
from sqlalchemy.orm import sessionmaker,declarative_base

DATABASE_URl=os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URl)

 
Base = declarative_base()
 
class Student(Base):
    __tablename__="student"
    id=Column(String,primary_key=True)
    name=Column(String(50),nullable=False)
    age=Column(Integer,nullable=False)
    course=Column(String,nullable=False)
    marks=Column(Integer,nullable=False)
    email=Column(String,unique=True,nullable=False)

Base.metadata.create_all(bind=engine)    
LocalSession=sessionmaker(bind=engine)
db=LocalSession()

if db.get(Student,"S120") is None:
    db.add(Student(id="S120",name="ABC",age=22,course="ECE",marks=99,email="abc@gmail.com"))
db.commit()

# for i in db.query(Student).all():
#     print(i.id,i.name,i.age)

# ABC=db.get(Student,"S120")
# ABC.age=44
# db.commit()




