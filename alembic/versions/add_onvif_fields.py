"""Add onvif_url to Camera and preset_token to CameraPreset

Revision ID: add_onvif_fields
Revises: 
Create Date: 2025-08-18 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_onvif_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona a coluna onvif_url à tabela cameras
    op.add_column('cameras', sa.Column('onvif_url', sa.String(), nullable=True))
    
    # Adiciona a coluna preset_token à tabela camera_presets
    op.add_column('camera_presets', sa.Column('preset_token', sa.String(), nullable=True))
    
    # Adiciona a coluna description à tabela camera_presets
    op.add_column('camera_presets', sa.Column('description', sa.String(), nullable=True))
    
    # Altera a coluna position para ser nullable
    op.alter_column('camera_presets', 'position', nullable=True)
    
    # Atualiza os registros existentes para ter um valor padrão para preset_token
    op.execute("UPDATE camera_presets SET preset_token = 'default' WHERE preset_token IS NULL")
    
    # Altera a coluna preset_token para não ser nullable após atualizar os registros existentes
    op.alter_column('camera_presets', 'preset_token', nullable=False)


def downgrade():
    # Remove a coluna onvif_url da tabela cameras
    op.drop_column('cameras', 'onvif_url')
    
    # Remove a coluna description da tabela camera_presets
    op.drop_column('camera_presets', 'description')
    
    # Remove a coluna preset_token da tabela camera_presets
    op.drop_column('camera_presets', 'preset_token')
    
    # Altera a coluna position para não ser nullable
    op.alter_column('camera_presets', 'position', nullable=False)
