from alembic import op
import sqlalchemy as sa
revision = "0004_skill_history"
down_revision = "0003_quiz_payload"
def upgrade():
    op.create_table("skill_history", sa.Column("id", sa.Integer, primary_key=True), sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("skill_id", sa.String(120), sa.ForeignKey("skills.id")), sa.Column("previous_level", sa.Integer), sa.Column("new_level", sa.Integer), sa.Column("source", sa.String(80)), sa.Column("recorded_at", sa.DateTime))
def downgrade(): op.drop_table("skill_history")
