from app.infrastructure.database.models import (
    TicketModel,
    LLMDatasetModel,
    UserAuditLogModel,
    DatasetAuditLogModel,
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
