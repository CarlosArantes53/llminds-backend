from app.infrastructure.database.models import (
    TicketModel,
    LLMDatasetModel,
    UserAuditLogModel,
    DatasetAuditLogModel,
    DatasetRowModel,
)

def test_ticket_model_indexes():
    """Verify that TicketModel has an index on created_at."""
    # Check if the column has index=True
    assert TicketModel.created_at.index is True, "TicketModel.created_at should have index=True"

def test_llm_dataset_model_indexes():
    """Verify that LLMDatasetModel has an index on inserted_at."""
    assert LLMDatasetModel.inserted_at.index is True, "LLMDatasetModel.inserted_at should have index=True"

def test_user_audit_log_model_indexes():
    """Verify that UserAuditLogModel has an index on performed_at."""
    assert UserAuditLogModel.performed_at.index is True, "UserAuditLogModel.performed_at should have index=True"

def test_dataset_audit_log_model_indexes():
    """Verify that DatasetAuditLogModel has an index on performed_at."""
    assert DatasetAuditLogModel.performed_at.index is True, "DatasetAuditLogModel.performed_at should have index=True"

def test_dataset_row_model_indexes():
    """Verify that DatasetRowModel has a composite index on (dataset_id, order)."""
    # Check if the composite index exists in __table__.indexes
    indexes = {i.name: i for i in DatasetRowModel.__table__.indexes}
    assert "ix_llm_dataset_rows_dataset_id_order" in indexes, "Composite index 'ix_llm_dataset_rows_dataset_id_order' should exist"

    idx = indexes["ix_llm_dataset_rows_dataset_id_order"]
    # Check columns
    col_names = [c.name for c in idx.columns]
    assert col_names == ["dataset_id", "order"], f"Index columns should be ['dataset_id', 'order'], but got {col_names}"
