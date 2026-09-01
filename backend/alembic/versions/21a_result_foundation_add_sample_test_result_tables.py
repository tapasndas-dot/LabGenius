"""Add sample test result foundation

Revision ID: 21a_result_foundation
Revises: 0af626218d6c
Create Date: 2026-09-01 08:35:00.000000

Sprint 21A: Result entry/capture domain foundation
- SampleTestResult: execution/result header with lifecycle (DRAFT/ENTERED/REVIEWED/FINALIZED/REJECTED/CANCELLED)
- ParameterResult: typed parameter values (TEXT/NUMBER/INTEGER/BOOLEAN/DATE/DATETIME)
- ResultInstrumentUsage: historical instrument usage during execution

Design principles:
- Historical basis frozen: results reference exact frozen MethodVersion/MethodParameter
- Result model flexible: supports multiple parameter types, not pharmaceutical-only
- Result data traceable: each parameter result links to exact MethodParameter
- Instrument usage historical: captures exact instrument used, independent of status changes
- Append-safe: supports result history/corrections without destroying prior finalized records
- Optimistic concurrency: version columns present for expected-version mutation patterns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21a_result_foundation'
down_revision: Union[str, Sequence[str], None] = '0af626218d6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SampleTestResult: execution/result header
    op.create_table('sample_test_results',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('sample_test_id', sa.UUID(), nullable=False),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('entered_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('entered_by_user_id', sa.UUID(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
    sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finalized_by_user_id', sa.UUID(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.CheckConstraint("status IN ('DRAFT', 'ENTERED', 'REVIEWED', 'FINALIZED', 'REJECTED', 'CANCELLED')", name='ck_sample_test_results_status'),
    sa.CheckConstraint('sequence_number > 0', name='ck_sample_test_results_sequence_positive'),
    sa.CheckConstraint('version > 0', name='ck_sample_test_results_version_positive'),
    sa.CheckConstraint('completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at', name='ck_sample_test_results_timing'),
    sa.ForeignKeyConstraint(['entered_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['finalized_by_user_id'], ['users.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['sample_test_id'], ['sample_tests.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sample_test_id', 'sequence_number', name='uq_sample_test_results_test_sequence'),
    )
    op.create_index('ix_sample_test_results_sample_test_status', 'sample_test_results', ['sample_test_id', 'status'])
    op.create_index('ix_sample_test_results_effective', 'sample_test_results', ['sample_test_id', 'sequence_number'])
    op.create_index('ix_sample_test_results_entered_by_user_id', 'sample_test_results', ['entered_by_user_id'])
    op.create_index('ix_sample_test_results_reviewed_by_user_id', 'sample_test_results', ['reviewed_by_user_id'])
    op.create_index('ix_sample_test_results_finalized_by_user_id', 'sample_test_results', ['finalized_by_user_id'])

    # ParameterResult: typed parameter values
    op.create_table('qc_parameter_results',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('sample_test_result_id', sa.UUID(), nullable=False),
    sa.Column('method_parameter_id', sa.UUID(), nullable=False),
    sa.Column('value_type', sa.String(20), nullable=False),
    sa.Column('text_value', sa.Text(), nullable=True),
    sa.Column('numeric_value', sa.Numeric(20, 8), nullable=True),
    sa.Column('integer_value', sa.Integer(), nullable=True),
    sa.Column('boolean_value', sa.Boolean(), nullable=True),
    sa.Column('date_value', sa.Date(), nullable=True),
    sa.Column('datetime_value', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("value_type IN ('TEXT', 'NUMBER', 'INTEGER', 'BOOLEAN', 'DATE', 'DATETIME')", name='ck_parameter_results_value_type'),
    sa.CheckConstraint('version > 0', name='ck_parameter_results_version_positive'),
    sa.ForeignKeyConstraint(['method_parameter_id'], ['method_parameters.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['sample_test_result_id'], ['sample_test_results.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sample_test_result_id', 'method_parameter_id', name='uq_parameter_results_result_parameter'),
    )
    op.create_index('ix_parameter_results_result', 'qc_parameter_results', ['sample_test_result_id'])
    op.create_index('ix_parameter_results_parameter', 'qc_parameter_results', ['method_parameter_id'])

    # ResultInstrumentUsage: historical instrument usage
    op.create_table('qc_result_instrument_usages',
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('sample_test_result_id', sa.UUID(), nullable=False),
    sa.Column('instrument_id', sa.UUID(), nullable=False),
    sa.Column('usage_notes', sa.Text(), nullable=True),
    sa.CheckConstraint('version > 0', name='ck_result_instrument_usages_version_positive'),
    sa.ForeignKeyConstraint(['instrument_id'], ['instruments.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['sample_test_result_id'], ['sample_test_results.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sample_test_result_id', 'instrument_id', name='uq_result_instrument_usages_result_instrument'),
    )
    op.create_index('ix_result_instrument_usages_result', 'qc_result_instrument_usages', ['sample_test_result_id'])
    op.create_index('ix_result_instrument_usages_instrument', 'qc_result_instrument_usages', ['instrument_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_result_instrument_usages_instrument', table_name='qc_result_instrument_usages')
    op.drop_index('ix_result_instrument_usages_result', table_name='qc_result_instrument_usages')
    op.drop_table('qc_result_instrument_usages')

    op.drop_index('ix_parameter_results_parameter', table_name='qc_parameter_results')
    op.drop_index('ix_parameter_results_result', table_name='qc_parameter_results')
    op.drop_table('qc_parameter_results')

    op.drop_index('ix_sample_test_results_finalized_by_user_id', table_name='sample_test_results')
    op.drop_index('ix_sample_test_results_reviewed_by_user_id', table_name='sample_test_results')
    op.drop_index('ix_sample_test_results_entered_by_user_id', table_name='sample_test_results')
    op.drop_index('ix_sample_test_results_effective', table_name='sample_test_results')
    op.drop_index('ix_sample_test_results_sample_test_status', table_name='sample_test_results')
    op.drop_table('sample_test_results')
