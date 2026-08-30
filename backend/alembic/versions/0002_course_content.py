"""Persist demo course enrollment and assessments."""
from alembic import op
import sqlalchemy as sa
revision = "0002_course_content"
down_revision = "0001_initial"
def upgrade():
    op.create_table("course_enrollments", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("course_id", sa.String(50), sa.ForeignKey("courses.course_id", ondelete="CASCADE")), sa.Column("enrolled_at", sa.DateTime), sa.UniqueConstraint("user_id", "course_id"))
    op.create_table("lesson_progress", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("course_id", sa.String(50), sa.ForeignKey("courses.course_id", ondelete="CASCADE")), sa.Column("module_id", sa.String(50)), sa.Column("lesson_id", sa.String(80)), sa.Column("completed_at", sa.DateTime), sa.UniqueConstraint("user_id", "course_id", "lesson_id"))
    op.create_table("module_assessment_attempts", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("course_id", sa.String(50), sa.ForeignKey("courses.course_id", ondelete="CASCADE")), sa.Column("module_id", sa.String(50)), sa.Column("score", sa.Float), sa.Column("passed", sa.Boolean), sa.Column("submitted_at", sa.DateTime))
def downgrade():
    op.drop_table("module_assessment_attempts"); op.drop_table("lesson_progress"); op.drop_table("course_enrollments")
