"""Modelos del sistema de registro academico."""

from .estudiante import (
    CodigoInvalidoError,
    Estudiante,
    EstudianteDuplicadoError,
    EstudianteError,
    EstudianteNoEncontradoError,
    MateriaDuplicadaError,
    MateriaNoEncontradaError,
    MateriaInvalidaError,
    NombreInvalidoError,
    NotaInvalidaError,
)

__all__ = [
    "CodigoInvalidoError",
    "Estudiante",
    "EstudianteDuplicadoError",
    "EstudianteError",
    "EstudianteNoEncontradoError",
    "MateriaDuplicadaError",
    "MateriaNoEncontradaError",
    "MateriaInvalidaError",
    "NombreInvalidoError",
    "NotaInvalidaError",
]
