"""split_datasets_into_header_and_rows

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade():
    # 1) Adicionar coluna 'name' ao dataset (agora é container)
    op.add_column('llm_datasets', sa.Column('name', sa.String(255), nullable=True))

    # 2) Preencher name com prompt_text truncado (dados existentes)
    op.execute("""
        UPDATE llm_datasets
        SET name = LEFT(prompt_text, 100)
    """)
    op.alter_column('llm_datasets', 'name', nullable=False)

    # 3) Criar tabela de linhas
    op.create_table(
        'llm_dataset_rows',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('dataset_id', sa.Integer,
                  sa.ForeignKey('llm_datasets.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('prompt_text', sa.Text, nullable=False),
        sa.Column('response_text', sa.Text, nullable=False),
        sa.Column('category', sa.String(255), nullable=False, server_default=''),
        sa.Column('semantics', sa.String(255), nullable=False, server_default=''),
        sa.Column('order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('inserted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # 4) Migrar dados existentes: cada dataset vira 1 row
    op.execute("""
        INSERT INTO llm_dataset_rows (dataset_id, prompt_text, response_text, category, semantics, "order")
        SELECT id, prompt_text, response_text, '', '', 0
        FROM llm_datasets
    """)

    # 5) Remover colunas prompt/response do dataset (agora vivem em rows)
    op.drop_column('llm_datasets', 'prompt_text')
    op.drop_column('llm_datasets', 'response_text')


def downgrade():
    op.add_column('llm_datasets', sa.Column('prompt_text', sa.Text, nullable=True))
    op.add_column('llm_datasets', sa.Column('response_text', sa.Text, nullable=True))

    op.execute("""
        UPDATE llm_datasets d
        SET prompt_text = r.prompt_text, response_text = r.response_text
        FROM (
            SELECT DISTINCT ON (dataset_id) dataset_id, prompt_text, response_text
            FROM llm_dataset_rows ORDER BY dataset_id, "order"
        ) r
        WHERE d.id = r.dataset_id
    """)

    op.alter_column('llm_datasets', 'prompt_text', nullable=False)
    op.alter_column('llm_datasets', 'response_text', nullable=False)
    op.drop_table('llm_dataset_rows')
    op.drop_column('llm_datasets', 'name')