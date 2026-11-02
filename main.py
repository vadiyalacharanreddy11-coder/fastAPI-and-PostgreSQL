from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine,Column,String,Integer,func
from sqlalchemy.orm import declarative_base,sessionmaker,Session
from pydantic import BaseModel,field_validator,Field,EmailStr,computed_field,ConfigDict
from sqlalchemy.exc import IntegrityError

DATABASE_URL=os.getenv("DATABASE_URL")

engine=create_engine(DATABASE_URL)

Base=declarative_base()

LocalSession=sessionmaker(bind=engine)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
class Student(Base):
    __tablename__="student"
    id=Column(String,primary_key=True)
    name=Column(String(50),nullable=False)
    age=Column(Integer,nullable=False)
    course=Column(String,nullable=False)
    marks=Column(Integer,nullable=False)
    email=Column(String,unique=True,nullable=False)

Base.metadata.create_all(bind=engine)   

# Input Pydantic Validation
class CreateStudent(BaseModel):
    id:str=Field(...,description="Enter the Id here",examples=["S101"])
    name:str=Field(...,min_length=3,max_length=50)
    age:int=Field(...,ge=0,le=100)
    course:str=Field(...,min_length=5,max_length=30)
    marks:int=Field(...,ge=0,le=100)
    email:EmailStr 

    @field_validator("name")
    @classmethod
    def check_name(cls,value):
        if value is None:
            return value
        if not value.replace(" ","").isalpha():
            raise ValueError("Name shouldn't contain any number characters")
        return value.title()
class UpdateStudent(BaseModel):
    name:str|None=Field(None,min_length=3,max_length=50)
    age:int|None=Field(None,gt=0,le=100)
    course:str|None=Field(None,min_length=5,max_length=30)
    marks:int|None=Field(None,gt=0,le=100)
    email:EmailStr|None=None
    @field_validator("name")
    @classmethod
    def check_name(cls,value):
        if value is None:
            return value
        if not value.replace(" ","").isalpha():
            raise ValueError("Name shouldn't contain any number characters")
        return value.title()

# Output Pydantic Validation 
class StudentOutput(CreateStudent):
    model_config=ConfigDict(from_attributes=True)

    @computed_field
    @property
    def grade(self)->str:
        score=self.marks
        if score>=90 :
            return "A+"
        elif score>=80:
            return "A"
        elif score>=70:
            return "B"
        else:
            return "C"

# Creating a localsession from endpoint goes to DB and returns 
def get_db():
    db=LocalSession()
    try:
        yield db
    finally:
        db.close()

# Creating a fastAPI app  
from fastapi import HTTPException,FastAPI,Path,Query,Depends
app=FastAPI()

# GET one student (ENDPOINT)
@app.get("/student/{student_id}",response_model=StudentOutput)
def get_student(student_id:str=Path(...,description="Enter ID of the student to want to see details!!"),db:Session=Depends(get_db)):
    data=db.get(Student,student_id)
    if data is None:
        raise HTTPException(status_code=404,detail=f"The user with id {student_id} does not exist!!")
    return data

# POST ROute(ENDPOINT)
@app.post("/Create",response_model=StudentOutput,status_code=201)
def create_student(item:CreateStudent,db:Session=Depends(get_db)):
    if db.get(Student,item.id):
        raise HTTPException(status_code=400,detail=f"Student with id {item.id} already exists!!")
    newItem=Student(**item.model_dump())
    db.add(newItem)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400,detail=f"The same mailID exists!!")
    db.refresh(newItem)
    return newItem

#PUT Method(ENDPOINT)
@app.put("/Update/{student_id}",response_model=StudentOutput,status_code=201)
def update_student(item:UpdateStudent,student_id:str=Path(...),db:Session=Depends(get_db)):
    pres_stu=db.get(Student,student_id)
    if pres_stu is None :
        raise HTTPException(status_code=400,detail=f"The student with id {student_id} does not exist")
    changes=item.model_dump(exclude_unset=True,exclude_none=True)
    for key,value in changes.items():
        setattr(pres_stu,key,value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400,detail=f"The same mailID exists!!")
    db.refresh(pres_stu) 
    return pres_stu  

#DELETE (ENDPOINTS)
@app.delete("/delete/{student_id}",response_model=StudentOutput)
def delete(student_id:str=Path(...),db:Session=Depends(get_db)):
    student=db.get(Student,student_id)
    if student is None:
        raise HTTPException(status_code=400,detail=f"The id {student_id} does not exist!!")
    db.delete(student)
    db.commit()
    return student

#SORT,GROUP,PAGINATE
SORT_BY=["name","age","marks"]
ORDER_BY=["ascending","descending"]
@app.get("/students")
def get_all(
    course:str|None=Query(None,description="The course upon which you wnat to filter",examples=["Python"]),
    sort_by:str|None=Query(None,description="Sort by what parameters",examples=["Maths"]),
    order_by:str|None=Query(None,description="Group by ascending or descending",examples=["asc"]),
    page:int|None=Query(None,description="At which page you want to go"),
    limit:int|None=Query(None,description="how many entries in one page"),
    db:Session=Depends(get_db)
):
    if sort_by is not None and sort_by not in SORT_BY:
        raise ValueError(f"The sort_by by {sort_by} is not in our List")
    if order_by is not None and order_by not in ORDER_BY:
        raise ValueError(f"The Order by is in valid")

    query=db.query(Student)
    totalStu=query.count()

    if course:
        query=query.filter(func.lower(Student.course)==course.lower())

    if sort_by:
        column=getattr(Student,sort_by)

        if order_by=='descending':
            query=query.order_by(column.desc())
        else:
            query=query.order_by(column.asc())
    else:
        query=query.order_by(Student.id)

    start=(page-1)*limit
    currPage=query.offset(start).limit(limit).all()
    return {
        "page":page,
        "limit":limit,
        "Totalstudents":totalStu,
        "currentPage":currPage
    }

            
    

