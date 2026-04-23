"""Errores de la capa de persistencia."""

from __future__ import annotations


class PersistenciaError(RuntimeError):
    """Se lanza cuando ocurre un problema leyendo o escribiendo datos persistentes."""
