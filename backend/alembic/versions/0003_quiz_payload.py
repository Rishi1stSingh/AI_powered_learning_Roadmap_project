from alembic import op
import sqlalchemy as sa
revision = "0003_quiz_payload"
down_revision = "0002_course_content"
def upgrade():
    for name in ("questions_json", "answers_json", "skill_signal_json"):
        op.add_column("module_assessment_attempts", sa.Column(name, sa.Text(), nullable=False, server_default="{}" if name == "skill_signal_json" else "[]"))
def downgrade():
    for name in ("skill_signal_json", "answers_json", "questions_json"): op.drop_column("module_assessment_attempts", name)
