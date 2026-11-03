from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import HTTPException,FastAPI,Path,Query,Depends
from sqlalchemy import create_engine,Column,String,Integer,func,CheckConstraint,ForeignKey
from sqlalchemy.orm import declarative_base,sessionmaker,Session
from pydantic import BaseModel,field_validator,Field,EmailStr,computed_field,ConfigDict
from sqlalchemy.exc import IntegrityError
from security import hash_password
from security import verify_password
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer

# JWT TOKEN DECODING CODE
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL=os.getenv("DATABASE_URL")

engine=create_engine(DATABASE_URL, pool_pre_ping=True)

# Creating a localsession from endpoint goes to DB and returns 
LocalSession=sessionmaker(bind=engine)
def get_db():
    db=LocalSession()
    try:
        yield db
    finally:
        db.close()
   
Base=declarative_base()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/logIn") 

# This function returns which user by extraction the token and filtering by the emailid
def get_current_user(
        token:str = Depends(oauth2_scheme),
        db:Session=Depends(get_db)
):
    # Check the validity of the token
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])

        email=payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401,detail="Invalid token")
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )
    user=db.get(Entries,email)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    return user


app=FastAPI()
 
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Entries(Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("length(password) >= 8", name="password_min_length"),
    )
    firstName = Column(String, nullable=False)
    lastName = Column(String, nullable=False)
    emailId = Column(String, primary_key=True, unique=True, nullable=False)
    password = Column(String,nullable=False)
   
class Student(Base):
    __tablename__="student"
    id=Column(String,primary_key=True)
    name=Column(String(50),nullable=False)
    age=Column(Integer,nullable=False)
    course=Column(String,nullable=False)
    marks=Column(Integer,nullable=False)
    email=Column(String,unique=True,nullable=False)
    user_email=Column(String,ForeignKey("entries.emailId"),nullable=False)

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

 

# GET one student (ENDPOINT)
@app.get("/student/{student_id}",response_model=StudentOutput)
def get_student(student_id:str=Path(...,description="Enter ID of the student to want to see details!!"),db:Session=Depends(get_db),user:Entries=Depends(get_current_user)):
    data=db.query(Student).filter(
        Student.id==student_id , Student.user_email==user.emailId
    ).first()

    if data is None:
        raise HTTPException(status_code=404,detail=f"The user with id {student_id} does not exist!!")
    return data

# POST ROute(ENDPOINT)
@app.post("/Create",response_model=StudentOutput,status_code=201)
def create_student(item:CreateStudent,db:Session=Depends(get_db),curr_user:Entries=Depends(get_current_user)):
    data=db.query(Student).filter(
            Student.id==item.id , Student.user_email==curr_user.emailId
        ).first()
    if data:
        raise HTTPException(status_code=400,detail=f"Student with id {item.id} already exists!!")
    newItem=Student(**item.model_dump(),user_email=curr_user.emailId)
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
def update_student(item:UpdateStudent,student_id:str=Path(...),db:Session=Depends(get_db),curr_user:Entries=Depends(get_current_user)):
    pres_stu=db.query(Student).filter(
        Student.id==student_id , Student.user_email==curr_user.emailId
    ).first()
     
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
def delete(student_id:str=Path(...),db:Session=Depends(get_db),curr_user:Entries=Depends(get_current_user)):
    student=db.query(Student).filter(
            Student.id==student_id , Student.user_email==curr_user.emailId
        ).first()
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
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db:Session=Depends(get_db),
    curr_user:Entries=Depends(get_current_user)
):
 
    if sort_by is not None and sort_by not in SORT_BY:
        raise ValueError(f"The sort_by by {sort_by} is not in our List")
    if order_by is not None and order_by not in ORDER_BY:
        raise ValueError(f"The Order by is in valid")

    query = db.query(Student).filter(
    Student.user_email == curr_user.emailId
    )
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


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt

#Login pydantic model

class SignUpCheck(BaseModel):
    firstName:str=Field(...,description="Enter your first name",examples=["Charan"])
    lastName:str=Field(...,description="Enter you last name",examples=["Reddy"])
    emailId:EmailStr=Field(...)
    password:str=Field(...,min_length=8,description="Enter your password")

    @field_validator("firstName")
    @classmethod
    def check_name(clas,value):
        if not value.replace(" ","").isalpha():
            raise HTTPException(status_code=401,detail="The name shouldn't contain any numeric values")

        return value.title()

class LoginCheck(BaseModel):
    emailId:EmailStr=Field(...)
    password:str=Field(...)


  

@app.post("/signUp",status_code=201)
def create_entry(item:SignUpCheck,db:Session=Depends(get_db)):
    # Email shouldn't be dup--->check in DB if any
    user=db.get(Entries,item.emailId)
    if user is not None:
        raise HTTPException(status_code=401,detail=f"A user with the emailId {item.emailId} already exists!!")
    passwordCurr=item.password
    hashed_password = hash_password(passwordCurr)
    new_user=Entries(firstName=item.firstName,lastName=item.lastName,emailId=item.emailId,password=hashed_password)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409,detail=f"The same mailID exists!!")
    db.refresh(new_user) 
    token=create_access_token({
        "sub":item.emailId,
        
    })
    return {
        "message": "User registered successfully",
        "access_token":token,
        "token_type":"bearer"
    }

@app.post("/logIn")
def login_check(item:LoginCheck,db:Session=Depends(get_db)):
    plain=item.password
    user=db.get(Entries,item.emailId)
    if user is None:
        # Go to SigUp route
        raise HTTPException(status_code=404,detail=f"There doesn't exist any users with emialid {item.emailId}")

    if not verify_password(plain,user.password):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token=create_access_token({
        "sub":item.emailId
    })
    return {
        "message": "Login successful",
        "access_token":token,
        "token_type":"bearer"

    }
 






 