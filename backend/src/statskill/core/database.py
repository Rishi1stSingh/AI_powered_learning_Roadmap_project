"""SQLAlchemy database configuration and persistent application models."""
from __future__ import annotations
import os
from pathlib import Path
from statskill.core.config import DATABASE_URL
from sqlalchemy import create_engine, ForeignKey, String, Text, Integer, Float, Boolean, UniqueConstraint, DateTime
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    employee_skills: Mapped[list["EmployeeSkill"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), unique=True)
    skill_type: Mapped[str] = mapped_column(String(30))
    category: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(50))

class Role(Base):
    __tablename__ = "roles"
    onet_code: Mapped[str] = mapped_column(String(30), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    is_showcase: Mapped[bool] = mapped_column(Boolean, default=False)
    role_skills: Mapped[list["RoleSkill"]] = relationship(back_populates="role", cascade="all, delete-orphan")

class Course(Base):
    __tablename__ = "courses"
    course_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    domain: Mapped[str] = mapped_column(String(200), default="")
    institution: Mapped[str] = mapped_column(String(300), default="")
    difficulty_level: Mapped[str] = mapped_column(String(50), default="")
    duration: Mapped[str] = mapped_column(String(100), default="")
    rating: Mapped[float | None] = mapped_column(Float)
    reviews: Mapped[int | None] = mapped_column(Integer)

class EmployeeSkill(Base):
    __tablename__ = "employee_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    level: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)
    user: Mapped[User] = relationship(back_populates="employee_skills")

class SkillHistory(Base):
    __tablename__ = "skill_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    previous_level: Mapped[int] = mapped_column(Integer)
    new_level: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(80), default="manual")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class RoleSkill(Base):
    __tablename__ = "role_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.onet_code", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    required_level: Mapped[int] = mapped_column(Integer)
    importance: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[str] = mapped_column(String(20))
    role: Mapped[Role] = relationship(back_populates="role_skills")
    __table_args__ = (UniqueConstraint("role_code", "skill_id"),)

class CourseSkill(Base):
    __tablename__ = "course_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    raw_skill: Mapped[str] = mapped_column(String(300))
    mapped: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("course_id", "skill_id"),)

class SkillAlias(Base):
    __tablename__ = "skill_aliases"
    alias: Mapped[str] = mapped_column(String(300), primary_key=True)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skills.id"))
    match_method: Mapped[str] = mapped_column(String(50))

class SkillAssessment(Base):
    __tablename__ = "skill_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    level: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), default="self_reported")

class SkillGap(Base):
    __tablename__ = "skill_gaps"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.onet_code"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id"))
    gap: Mapped[int] = mapped_column(Integer)

class CourseRecommendation(Base):
    __tablename__ = "course_recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"))
    score: Mapped[float] = mapped_column(Float)

class LearningProgress(Base):
    __tablename__ = "learning_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id"))
    progress_percent: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default="not_started")

class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"))
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"))
    module_id: Mapped[str] = mapped_column(String(50))
    lesson_id: Mapped[str] = mapped_column(String(80))
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "course_id", "module_id", "lesson_id"),)

class ModuleAssessmentAttempt(Base):
    __tablename__ = "module_assessment_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"))
    module_id: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(Boolean)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    questions_json: Mapped[str] = mapped_column(Text, default="[]")
    answers_json: Mapped[str] = mapped_column(Text, default="[]")
    skill_signal_json: Mapped[str] = mapped_column(Text, default="{}")
    attempt_state: Mapped[str] = mapped_column(String(20), default="active")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
