"""Lectura de snapshots JSON heredados para migraciones iniciales."""

from __future__ import annotations

import json
from pathlib import Path

from app.models import Estudiante, EstudianteError

from .errors import PersistenciaError


class LegacySnapshotLoader:
    """Recupera estudiantes desde el antiguo archivo JSON si existe."""

    def __init__(self, ruta_snapshot: Path | None) -> None:
        """Configura la ruta del snapshot heredado."""
        self.__ruta_snapshot = ruta_snapshot

    @property
    def ruta_snapshot(self) -> Path | None:
        """Devuelve la ruta configurada para la carga heredada."""
        return self.__ruta_snapshot

    def cargar(self) -> list[Estudiante]:
        """Reconstruye estudiantes desde el snapshot JSON heredado."""
        if self.__ruta_snapshot is None or not self.__ruta_snapshot.exists():
            return []

        try:
            contenido = self.__ruta_snapshot.read_text(encoding="utf-8").strip()
            if not contenido:
                return []
            payload = json.loads(contenido)
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenciaError(
                f"No se pudo leer el snapshot heredado: {self.__ruta_snapshot}."
            ) from exc

        if not isinstance(payload, dict):
            raise PersistenciaError(
                f"El snapshot heredado tiene un formato invalido: {self.__ruta_snapshot}."
            )

        estudiantes_serializados = payload.get("estudiantes", [])
        if not isinstance(estudiantes_serializados, list):
            raise PersistenciaError(
                f"El snapshot heredado tiene un formato invalido: {self.__ruta_snapshot}."
            )

        estudiantes: list[Estudiante] = []
        for registro in estudiantes_serializados:
            try:
                estudiante = Estudiante(
                    nombre=str(registro["nombre"]),
                    codigo=str(registro["codigo"]),
                )
                notas = registro.get("notas", {})
                if not isinstance(notas, dict):
                    raise PersistenciaError(
                        f"El snapshot heredado contiene notas invalidas: {self.__ruta_snapshot}."
                    )
                for materia, nota in notas.items():
                    estudiante.registrar_nota(str(materia), float(nota))
            except (KeyError, TypeError, ValueError, EstudianteError) as exc:
                raise PersistenciaError(
                    f"No se pudo migrar el snapshot heredado: {self.__ruta_snapshot}."
                ) from exc
            estudiantes.append(estudiante)

        return estudiantes
