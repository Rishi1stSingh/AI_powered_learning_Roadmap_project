from alembic import op
import sqlalchemy as sa
revision = "0005_attempt_state"
down_revision = "0004_skill_history"
def upgrade(): op.add_column("module_assessment_attempts", sa.Column("attempt_state", sa.String(20), nullable=False, server_default="submitted"))
def downgrade(): op.drop_column("module_assessment_attempts", "attempt_state")
