"""Make lesson completion unique within a module."""
from alembic import op
import sqlalchemy as sa
revision = "0006_lesson_scope"
down_revision = "0005_attempt_state"
def upgrade():
    op.drop_constraint("lesson_progress_user_id_course_id_lesson_id_key", "lesson_progress", type_="unique")
    op.create_unique_constraint("lesson_progress_user_course_module_lesson_key", "lesson_progress", ["user_id", "course_id", "module_id", "lesson_id"])
def downgrade():
    op.drop_constraint("lesson_progress_user_course_module_lesson_key", "lesson_progress", type_="unique")
    op.create_unique_constraint("lesson_progress_user_id_course_id_lesson_id_key", "lesson_progress", ["user_id", "course_id", "lesson_id"])
