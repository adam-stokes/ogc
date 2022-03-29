"""add timestamps

Revision ID: 88ed8d6d9d75
Revises: 
Create Date: 2022-03-28 16:39:09.052562

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '88ed8d6d9d75'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("actions", sa.Column("created", sa.DateTime(), server_default=sa.sql.func.now()))
    op.add_column("node", sa.Column("created", sa.DateTime(), server_default=sa.sql.func.now()))


def downgrade():
    op.drop_column("actions", "created")
    op.drop_column("node", "created")
