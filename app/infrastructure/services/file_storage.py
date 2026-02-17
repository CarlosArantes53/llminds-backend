"""Serviço de armazenamento de arquivos no filesystem local."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.infrastructure.config import get_settings

settings = get_settings()


class FileStorageError(Exception):
    pass


class FileStorageService:
    """Armazena arquivos em disco local. Organiza por ticket_id."""

    def __init__(self) -> None:
        self.base_dir = Path(settings.UPLOAD_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _ticket_dir(self, ticket_id: int) -> Path:
        d = self.base_dir / f"tickets/{ticket_id}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def save(self, ticket_id: int, file: UploadFile) -> dict:
        """Salva arquivo e retorna metadados."""
        # Validar tipo
        if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
            raise FileStorageError(
                f"Tipo não permitido: {file.content_type}. "
                f"Permitidos: {', '.join(settings.ALLOWED_CONTENT_TYPES)}"
            )

        # Ler conteúdo e validar tamanho
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            raise FileStorageError(
                f"Arquivo excede o limite de {settings.MAX_FILE_SIZE_MB}MB"
            )

        # Gerar nome único
        ext = Path(file.filename or "file").suffix.lower()
        stored_name = f"{uuid.uuid4().hex}{ext}"

        # Salvar
        dest = self._ticket_dir(ticket_id) / stored_name
        dest.write_bytes(content)

        return {
            "original_filename": file.filename or "unnamed",
            "stored_filename": stored_name,
            "content_type": file.content_type,
            "file_size": len(content),
        }

    def get_path(self, ticket_id: int, stored_filename: str) -> Path:
        """Retorna o path completo de um arquivo."""
        return self._ticket_dir(ticket_id) / stored_filename

    def delete(self, ticket_id: int, stored_filename: str) -> None:
        path = self.get_path(ticket_id, stored_filename)
        if path.exists():
            path.unlink()