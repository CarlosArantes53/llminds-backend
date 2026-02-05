"""Value Objects do domínio — imutáveis, comparados por valor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class Milestone:
    """
    Milestone de um Ticket — value object imutável.
    Representa uma etapa com título, prazo e estado de conclusão.
    """
    title: str
    due_date: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None
    order: int = 0

    def mark_completed(self) -> "Milestone":
        """Retorna nova instância marcada como concluída (imutável)."""
        return Milestone(
            title=self.title,
            due_date=self.due_date,
            completed=True,
            completed_at=datetime.utcnow(),
            order=self.order,
        )

    def is_overdue(self) -> bool:
        if self.due_date is None or self.completed:
            return False
        return datetime.utcnow() > self.due_date

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Milestone":
        return cls(
            title=data.get("title", ""),
            due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
            completed=data.get("completed", False),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            order=data.get("order", 0),
        )


@dataclass(frozen=True)
class Email:
    """Value object para email validado."""
    address: str

    def __post_init__(self):
        if not self.address or "@" not in self.address:
            raise ValueError(f"Email inválido: {self.address}")
