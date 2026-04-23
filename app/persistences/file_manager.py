"""Escritura y mantenimiento de reportes en disco."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.models import Estudiante


class ReporteError(OSError):
    """Se lanza cuando falla la escritura de un reporte."""


class FileManager:
    """Gestiona reportes y rutas auxiliares del sistema."""

    def __init__(
        self,
        directorio_base: Path | None = None,
        directorio_reportes: Path | None = None,
    ) -> None:
        """Configura la ruta base del proyecto y el directorio de reportes."""
        if directorio_base is None:
            directorio_base = Path(__file__).resolve().parents[2]
        self.__directorio_base = directorio_base
        if directorio_reportes is None:
            directorio_reportes = directorio_base / "storage" / "reportes"
        self.__directorio_reportes = directorio_reportes

    @property
    def directorio_base(self) -> Path:
        """Devuelve la ruta base del proyecto."""
        return self.__directorio_base

    @property
    def directorio_reportes(self) -> Path:
        """Devuelve el directorio donde se almacenan los reportes."""
        return self.__directorio_reportes

    def escribir_reporte(self, estudiante: Estudiante) -> Path:
        """Genera y guarda el reporte individual de un estudiante."""
        ruta_reporte = self.__directorio_reportes / f"{estudiante.codigo}.txt"
        contenido = self._construir_reporte(estudiante)

        try:
            self.__directorio_reportes.mkdir(parents=True, exist_ok=True)
            ruta_reporte.write_text(contenido, encoding="utf-8")
        except OSError as exc:
            raise ReporteError(
                f"No se pudo generar el reporte para el estudiante {estudiante.codigo}."
            ) from exc

        return ruta_reporte

    def eliminar_reporte(self, codigo: str) -> None:
        """Elimina el reporte existente para un estudiante si esta presente."""
        ruta_reporte = self.__directorio_reportes / f"{codigo}.txt"
        if ruta_reporte.exists():
            try:
                ruta_reporte.unlink()
            except OSError as exc:
                raise ReporteError(
                    f"No se pudo eliminar el reporte asociado al estudiante {codigo}."
                ) from exc

    @staticmethod
    def _construir_reporte(estudiante: Estudiante) -> str:
        """Arma el contenido textual del reporte individual."""
        resumen = estudiante.obtener_resumen()
        lineas = [
            "REPORTE ACADEMICO INDIVIDUAL",
            "=" * 60,
            f"Codigo: {resumen['codigo']}",
            f"Nombre: {resumen['nombre']}",
            f"Fecha de generacion: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "Materias registradas:",
        ]

        notas = resumen["notas"]
        if notas:
            for materia, nota in sorted(notas.items()):
                lineas.append(f"- {materia}: {nota:.2f}")
        else:
            lineas.append("- Sin notas registradas")

        lineas.extend(
            [
                "",
                f"Promedio general: {resumen['promedio']:.2f}",
                f"Estado academico: {resumen['estado']}",
            ]
        )
        return "\n".join(lineas) + "\n"
