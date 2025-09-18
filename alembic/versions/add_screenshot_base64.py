"""Add screenshot_base64 to Camera

Revision ID: add_screenshot_base64
Revises: add_onvif_fields
Create Date: 2025-08-18 15:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_screenshot_base64'
down_revision = 'add_onvif_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona a coluna screenshot_base64 à tabela cameras
    op.add_column('cameras', sa.Column('screenshot_base64', sa.Text(), nullable=True))


def downgrade():
    # Remove a coluna screenshot_base64 da tabela cameras
    op.drop_column('cameras', 'screenshot_base64')
