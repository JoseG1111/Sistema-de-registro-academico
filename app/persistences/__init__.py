"""Capa de persistencia del sistema academico."""

from .errors import PersistenciaError
from .estudiante_repository import EstudianteRepository
from .file_manager import FileManager, ReporteError
from .legacy_snapshot import LegacySnapshotLoader

__all__ = [
    "EstudianteRepository",
    "FileManager",
    "LegacySnapshotLoader",
    "PersistenciaError",
    "ReporteError",
]
