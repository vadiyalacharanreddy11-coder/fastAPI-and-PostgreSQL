from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, FastAPI, Path, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import BaseModel, field_validator, Field, EmailStr, computed_field, ConfigDict
from sqlalchemy import (
    create_engine, Column, String, Integer,
    func, ForeignKey, UniqueConstraint
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from security import hash_password, verify_password

# ─────────────────────────────────────────────────────────────
# CONFIG  (fail fast if the deployment is misconfigured)
# ─────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# SQLAlchemy needs "postgresql://", some hosts give "postgres://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
LocalSession = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────
class Entries(Base):
    """A teacher account."""
    __tablename__ = "entries"
    firstName = Column(String, nullable=False)
    lastName = Column(String, nullable=False)
    emailId = Column(String, primary_key=True, nullable=False)
    password = Column(String, nullable=False)

class Student(Base):
    __tablename__ = "student"

    __table_args__ = (
        UniqueConstraint(
            "email",
            "user_email",
            name="uq_student_email_per_user"
        ),
    )

    id = Column(String, primary_key=True)
    user_email = Column(
        String,
        ForeignKey("entries.emailId"),
        primary_key=True
    )

    name = Column(String(50), nullable=False)
    age = Column(Integer, nullable=False)
    course = Column(String, nullable=False)
    marks = Column(Integer, nullable=False)
    email = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)


# ─────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/logIn")


def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.get(Entries, email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ─────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────
app = FastAPI(title="Student Management API")

# Set ALLOWED_ORIGINS="https://your-streamlit-app.streamlit.app" in production
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────
def _check_name(value):
    if value is None:
        return value
    if not value.replace(" ", "").isalpha():
        raise ValueError("Name should contain only letters and spaces")
    return value.title()


class CreateStudent(BaseModel):
    id: str = Field(..., min_length=1, description="Enter the Id here", examples=["S101"])
    name: str = Field(..., min_length=3, max_length=50)
    age: int = Field(..., ge=0, le=100)
    course: str = Field(..., min_length=5, max_length=30)
    marks: int = Field(..., ge=0, le=100)
    email: EmailStr

    @field_validator("name")
    @classmethod
    def check_name(cls, value):
        return _check_name(value)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value):
        return value.lower()


class UpdateStudent(BaseModel):
    name: str | None = Field(None, min_length=3, max_length=50)
    age: int | None = Field(None, ge=0, le=100)
    course: str | None = Field(None, min_length=5, max_length=30)
    marks: int | None = Field(None, ge=0, le=100)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def check_name(cls, value):
        return _check_name(value)

    @field_validator("email")
    @classmethod
    def lower_email(cls, value):
        return value.lower() if value else value


class StudentOutput(CreateStudent):
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def grade(self) -> str:
        if self.marks >= 90:
            return "A+"
        if self.marks >= 80:
            return "A"
        if self.marks >= 70:
            return "B"
        return "C"


class SignUpCheck(BaseModel):
    firstName: str = Field(..., min_length=1, description="Enter your first name", examples=["Charan"])
    lastName: str = Field(..., min_length=1, description="Enter your last name", examples=["Reddy"])
    emailId: EmailStr
    password: str = Field(..., min_length=8, description="Enter your password")

    @field_validator("firstName", "lastName")
    @classmethod
    def check_names(cls, value):
        if not value.replace(" ", "").isalpha():
            raise ValueError("Name should contain only letters and spaces")
        return value.title()


class LoginCheck(BaseModel):
    emailId: EmailStr
    password: str


# ─────────────────────────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────────────────────────
@app.post("/signUp", status_code=201)
def sign_up(item: SignUpCheck, db: Session = Depends(get_db)):
    email = item.emailId.lower()
    if db.get(Entries, email) is not None:
        raise HTTPException(status_code=409, detail=f"A user with the email {email} already exists")

    new_user = Entries(
        firstName=item.firstName,
        lastName=item.lastName,
        emailId=email,
        password=hash_password(item.password),
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    return {
        "message": "User registered successfully",
        "access_token": create_access_token({"sub": email}),
        "token_type": "bearer",
    }


@app.post("/logIn")
def log_in(item: LoginCheck, db: Session = Depends(get_db)):
    email = item.emailId.lower()
    user = db.get(Entries, email)

    # One generic message so attackers can't discover which emails are registered
    if user is None or not verify_password(item.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {
        "message": "Login successful",
        "access_token": create_access_token({"sub": email}),
        "token_type": "bearer",
    }


# ─────────────────────────────────────────────────────────────
# STUDENT ROUTES  (every query is scoped to the logged-in teacher)
# ─────────────────────────────────────────────────────────────
def find_student(db: Session, student_id: str, teacher_email: str):
    return db.query(Student).filter(
        Student.id == student_id, Student.user_email == teacher_email
    ).first()


@app.get("/student/{student_id}", response_model=StudentOutput)
def get_student(
    student_id: str = Path(..., description="ID of the student"),
    db: Session = Depends(get_db),
    user: Entries = Depends(get_current_user),
):
    student = find_student(db, student_id, user.emailId)
    if student is None:
        raise HTTPException(status_code=404, detail=f"The student with id {student_id} does not exist")
    return student


@app.post("/Create", response_model=StudentOutput, status_code=201)
def create_student(
    item: CreateStudent,
    db: Session = Depends(get_db),
    user: Entries = Depends(get_current_user),
):
    if find_student(db, item.id, user.emailId):
        raise HTTPException(status_code=400, detail=f"Student with id {item.id} already exists")

    new_student = Student(**item.model_dump(), user_email=user.emailId)
    db.add(new_student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A student with this email already exists")
    db.refresh(new_student)
    return new_student


@app.put("/Update/{student_id}", response_model=StudentOutput)
def update_student(
    item: UpdateStudent,
    student_id: str = Path(...),
    db: Session = Depends(get_db),
    user: Entries = Depends(get_current_user),
):
    student = find_student(db, student_id, user.emailId)
    if student is None:
        raise HTTPException(status_code=404, detail=f"The student with id {student_id} does not exist")

    for key, value in item.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(student, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="A student with this email already exists")
    db.refresh(student)
    return student


@app.delete("/delete/{student_id}", response_model=StudentOutput)
def delete_student(
    student_id: str = Path(...),
    db: Session = Depends(get_db),
    user: Entries = Depends(get_current_user),
):
    student = find_student(db, student_id, user.emailId)
    if student is None:
        raise HTTPException(status_code=404, detail=f"The student with id {student_id} does not exist")

    result = StudentOutput.model_validate(student)  # copy the data before the row is gone
    db.delete(student)
    db.commit()
    return result


SORT_BY = ["name", "age", "marks"]
ORDER_BY = ["ascending", "descending"]


@app.get("/students")
def get_all(
    course: str | None = Query(None, description="Filter by course", examples=["Python"]),
    sort_by: str | None = Query(None, description="One of: name, age, marks", examples=["marks"]),
    order_by: str | None = Query(None, description="ascending or descending", examples=["descending"]),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Entries = Depends(get_current_user),
):
    if sort_by is not None and sort_by not in SORT_BY:
        raise HTTPException(status_code=400, detail=f"sort_by must be one of {SORT_BY}")
    if order_by is not None and order_by not in ORDER_BY:
        raise HTTPException(status_code=400, detail=f"order_by must be one of {ORDER_BY}")

    query = db.query(Student).filter(Student.user_email == user.emailId)

    if course:
        query = query.filter(func.lower(Student.course) == course.lower())

    total = query.count()  # counted AFTER filtering so pagination is correct

    if sort_by:
        column = getattr(Student, sort_by)
        column = column.desc() if order_by == "descending" else column.asc()
        query = query.order_by(column, Student.id)  # Student.id keeps page order stable
    else:
        query = query.order_by(Student.id)

    students = query.offset((page - 1) * limit).limit(limit).all()
    return {
        "page": page,
        "limit": limit,
        "Totalstudents": total,
        "currentPage": students,
    }