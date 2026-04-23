"""Controlador para coordinar estudiantes, PostgreSQL y reportes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import AppConfig
from app.models import (
    Estudiante,
    EstudianteDuplicadoError,
    EstudianteNoEncontradoError,
)
from app.persistences import (
    EstudianteRepository,
    FileManager,
    LegacySnapshotLoader,
)


class EstudianteController:
    """Orquesta las operaciones del sistema sin mezclar presentacion."""

    def __init__(self, configuracion: AppConfig) -> None:
        """Inicializa PostgreSQL, reportes y la migracion heredada opcional."""
        self.__configuracion = configuracion
        self.__repositorio = EstudianteRepository(configuracion.database_url)
        self.__file_manager = FileManager(
            directorio_base=configuracion.base_dir,
            directorio_reportes=configuracion.reports_dir,
        )
        self.__legacy_loader = LegacySnapshotLoader(configuracion.legacy_snapshot_path)
        self._bootstrap_legacy_data()

    def obtener_directorio_base(self) -> Path:
        """Devuelve el directorio base del proyecto."""
        return self.__file_manager.directorio_base

    def obtener_directorio_reportes(self) -> Path:
        """Devuelve el directorio donde se almacenan los reportes generados."""
        return self.__file_manager.directorio_reportes

    def obtener_info_persistencia(self) -> dict[str, str]:
        """Devuelve metadatos seguros de almacenamiento para la UI."""
        return {
            "database": self.__repositorio.obtener_etiqueta_conexion(),
            "reports_dir": str(self.__file_manager.directorio_reportes),
        }

    def verificar_salud(self) -> dict[str, str]:
        """Comprueba que la aplicacion puede acceder a PostgreSQL."""
        self.__repositorio.ping()
        return {"status": "ok", "database": "up"}

    def crear_estudiante(self, nombre: str, codigo: str) -> dict[str, Any]:
        """Crea un estudiante y devuelve su resumen serializable."""
        estudiante = Estudiante(nombre=nombre, codigo=codigo)
        if self.__repositorio.existe(estudiante.codigo):
            raise EstudianteDuplicadoError(
                f"Ya existe un estudiante registrado con el codigo {estudiante.codigo}."
            )
        self.__repositorio.guardar(estudiante)
        return estudiante.obtener_resumen()

    def actualizar_estudiante(self, codigo: str, nombre: str) -> dict[str, Any]:
        """Edita el nombre de un estudiante ya existente."""
        estudiante = self.obtener_estudiante(codigo)
        estudiante.actualizar_nombre(nombre)
        self.__repositorio.guardar(estudiante)
        return estudiante.obtener_resumen()

    def eliminar_estudiante(self, codigo: str) -> dict[str, str]:
        """Elimina un estudiante y su reporte asociado si existe."""
        estudiante = self.obtener_estudiante(codigo)
        self.__repositorio.eliminar(estudiante.codigo)
        self.__file_manager.eliminar_reporte(estudiante.codigo)
        return {
            "codigo": estudiante.codigo,
            "nombre": estudiante.nombre,
        }

    def obtener_estudiante(self, codigo: str) -> Estudiante:
        """Recupera un estudiante por su codigo."""
        codigo_normalizado = codigo.strip()
        estudiante = self.__repositorio.obtener(codigo_normalizado)
        if estudiante is None:
            raise EstudianteNoEncontradoError(
                f"No existe ningun estudiante con el codigo {codigo_normalizado}."
            )
        return estudiante

    def obtener_resumen_estudiante(self, codigo: str) -> dict[str, Any]:
        """Recupera el resumen serializable de un estudiante."""
        return self.obtener_estudiante(codigo).obtener_resumen()

    def registrar_nota(self, codigo: str, materia: str, nota: float) -> dict[str, Any]:
        """Registra una nota para el estudiante indicado."""
        estudiante = self.obtener_estudiante(codigo)
        estudiante.registrar_nota(materia, nota)
        self.__repositorio.guardar(estudiante)
        return estudiante.obtener_resumen()

    def editar_nota(
        self,
        codigo: str,
        materia_actual: str,
        materia_nueva: str,
        nota_nueva: float,
    ) -> dict[str, Any]:
        """Edita una nota existente de un estudiante."""
        estudiante = self.obtener_estudiante(codigo)
        estudiante.editar_nota(materia_actual, materia_nueva, nota_nueva)
        self.__repositorio.guardar(estudiante)
        return estudiante.obtener_resumen()

    def eliminar_nota(self, codigo: str, materia: str) -> dict[str, Any]:
        """Elimina una materia registrada para un estudiante."""
        estudiante = self.obtener_estudiante(codigo)
        estudiante.eliminar_nota(materia)
        self.__repositorio.guardar(estudiante)
        return estudiante.obtener_resumen()

    def listar_estudiantes(self) -> list[Estudiante]:
        """Devuelve todos los estudiantes ordenados por codigo."""
        return self.__repositorio.listar()

    def listar_resumenes_estudiantes(self) -> list[dict[str, Any]]:
        """Devuelve la informacion resumida de todos los estudiantes."""
        return [estudiante.obtener_resumen() for estudiante in self.listar_estudiantes()]

    def obtener_resumen_general(self) -> dict[str, int | float]:
        """Devuelve metricas generales para el panel principal."""
        estudiantes = self.listar_estudiantes()
        total = len(estudiantes)
        con_notas = sum(1 for estudiante in estudiantes if estudiante.tiene_notas())
        aprobados = sum(
            1 for estudiante in estudiantes if estudiante.determinar_estado() == "Aprobado"
        )
        reprobados = sum(
            1 for estudiante in estudiantes if estudiante.determinar_estado() == "Reprobado"
        )
        materias_totales = sum(len(estudiante.notas) for estudiante in estudiantes)
        promedio_general = (
            round(
                sum(estudiante.calcular_promedio() for estudiante in estudiantes) / total,
                2,
            )
            if total
            else 0.0
        )

        return {
            "estudiantes_totales": total,
            "con_notas": con_notas,
            "sin_notas": total - con_notas,
            "aprobados": aprobados,
            "reprobados": reprobados,
            "materias_totales": materias_totales,
            "promedio_general": promedio_general,
        }

    def generar_reporte_individual(self, codigo: str) -> Path:
        """Genera el reporte individual de un estudiante."""
        estudiante = self.obtener_estudiante(codigo)
        return self.__file_manager.escribir_reporte(estudiante)

    def generar_reportes_todos(self) -> list[Path]:
        """Genera reportes individuales para todos los estudiantes."""
        rutas: list[Path] = []
        for estudiante in self.listar_estudiantes():
            rutas.append(self.__file_manager.escribir_reporte(estudiante))
        return rutas

    def _bootstrap_legacy_data(self) -> None:
        """Migra el snapshot JSON heredado solo si la base esta vacia."""
        if not self.__configuracion.bootstrap_legacy_data:
            return
        if not self.__repositorio.esta_vacio():
            return

        for estudiante in self.__legacy_loader.cargar():
            self.__repositorio.guardar(estudiante)
