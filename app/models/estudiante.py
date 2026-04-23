"""Modelo de dominio para estudiantes y notas."""

from __future__ import annotations

import math
from typing import Any


class EstudianteError(ValueError):
    """Excepcion base para errores de validacion del modelo."""


class NombreInvalidoError(EstudianteError):
    """Se lanza cuando el nombre del estudiante no es valido."""


class CodigoInvalidoError(EstudianteError):
    """Se lanza cuando el codigo del estudiante no cumple la regla."""


class MateriaInvalidaError(EstudianteError):
    """Se lanza cuando el nombre de la materia no es valido."""


class NotaInvalidaError(EstudianteError):
    """Se lanza cuando la nota no esta en el rango permitido."""


class MateriaDuplicadaError(EstudianteError):
    """Se lanza cuando se intenta registrar una materia repetida."""


class MateriaNoEncontradaError(EstudianteError):
    """Se lanza cuando no existe la materia solicitada."""


class EstudianteDuplicadoError(EstudianteError):
    """Se lanza cuando ya existe un estudiante con el mismo codigo."""


class EstudianteNoEncontradoError(LookupError):
    """Se lanza cuando no existe un estudiante con el codigo indicado."""


class Estudiante:
    """Representa a un estudiante con codigo unico y notas por materia."""

    def __init__(self, nombre: str, codigo: str) -> None:
        """Inicializa un estudiante con nombre y codigo validados."""
        self.__nombre = ""
        self.__codigo = ""
        self.__notas: dict[str, float] = {}
        self.nombre = nombre
        self.codigo = codigo

    @property
    def nombre(self) -> str:
        """Devuelve el nombre del estudiante."""
        return self.__nombre

    @nombre.setter
    def nombre(self, valor: str) -> None:
        """Actualiza el nombre del estudiante despues de validarlo."""
        self.__nombre = self._validar_nombre(valor)

    @property
    def codigo(self) -> str:
        """Devuelve el codigo del estudiante."""
        return self.__codigo

    @codigo.setter
    def codigo(self, valor: str) -> None:
        """Actualiza el codigo del estudiante despues de validarlo."""
        self.__codigo = self._validar_codigo(valor)

    @property
    def notas(self) -> dict[str, float]:
        """Devuelve una copia de las notas registradas."""
        return dict(self.__notas)

    def actualizar_nombre(self, nombre: str) -> None:
        """Modifica el nombre del estudiante."""
        self.nombre = nombre

    def registrar_nota(self, materia: str, nota: float) -> None:
        """Registra la nota de una materia si no estaba cargada."""
        materia_validada = self._validar_materia(materia)
        materia_existente = self._buscar_materia_existente(materia_validada)
        if materia_existente is not None:
            raise MateriaDuplicadaError(
                f"La materia '{materia_existente}' ya tiene una nota registrada."
            )
        self.__notas[materia_validada] = self._normalizar_nota(nota)

    def editar_nota(self, materia_actual: str, nueva_materia: str, nueva_nota: float) -> None:
        """Actualiza una nota existente, permitiendo renombrar la materia."""
        materia_registrada = self._obtener_materia_registrada(materia_actual)
        materia_nueva = self._validar_materia(nueva_materia)
        nota_normalizada = self._normalizar_nota(nueva_nota)

        if materia_registrada.casefold() != materia_nueva.casefold():
            materia_existente = self._buscar_materia_existente(materia_nueva)
            if materia_existente is not None:
                raise MateriaDuplicadaError(
                    f"La materia '{materia_existente}' ya tiene una nota registrada."
                )

        del self.__notas[materia_registrada]
        self.__notas[materia_nueva] = nota_normalizada

    def eliminar_nota(self, materia: str) -> None:
        """Elimina una materia registrada del estudiante."""
        materia_registrada = self._obtener_materia_registrada(materia)
        del self.__notas[materia_registrada]

    def obtener_nota(self, materia: str) -> float | None:
        """Devuelve la nota de una materia si existe."""
        materia_registrada = self._buscar_materia_existente(self._validar_materia(materia))
        if materia_registrada is None:
            return None
        return self.__notas[materia_registrada]

    def calcular_promedio(self) -> float:
        """Calcula el promedio general del estudiante."""
        if not self.__notas:
            return 0.0
        promedio = sum(self.__notas.values()) / len(self.__notas)
        return round(promedio, 2)

    def determinar_estado(self) -> str:
        """Determina el estado academico con base en el promedio."""
        if not self.__notas:
            return "Pendiente"
        if self.calcular_promedio() >= 6.0:
            return "Aprobado"
        return "Reprobado"

    def tiene_notas(self) -> bool:
        """Indica si el estudiante tiene al menos una nota registrada."""
        return bool(self.__notas)

    def serializar(self) -> dict[str, Any]:
        """Devuelve los datos persistibles del estudiante."""
        return {
            "codigo": self.codigo,
            "nombre": self.nombre,
            "notas": self.notas,
        }

    def obtener_resumen(self) -> dict[str, Any]:
        """Construye un resumen serializable del estado academico."""
        return {
            "codigo": self.codigo,
            "nombre": self.nombre,
            "notas": self.notas,
            "materias_totales": len(self.__notas),
            "promedio": self.calcular_promedio(),
            "estado": self.determinar_estado(),
        }

    def _buscar_materia_existente(self, materia: str) -> str | None:
        """Busca una materia repetida sin diferenciar mayusculas."""
        materia_normalizada = materia.casefold()
        for materia_registrada in self.__notas:
            if materia_registrada.casefold() == materia_normalizada:
                return materia_registrada
        return None

    def _obtener_materia_registrada(self, materia: str) -> str:
        """Recupera el nombre exacto de una materia registrada."""
        materia_validada = self._validar_materia(materia)
        materia_registrada = self._buscar_materia_existente(materia_validada)
        if materia_registrada is None:
            raise MateriaNoEncontradaError(
                f"La materia '{materia_validada}' no esta registrada para este estudiante."
            )
        return materia_registrada

    @staticmethod
    def _validar_nombre(valor: str) -> str:
        """Valida y normaliza el nombre del estudiante."""
        nombre = valor.strip()
        if not nombre:
            raise NombreInvalidoError("El nombre del estudiante no puede estar vacio.")
        return nombre

    @staticmethod
    def _validar_codigo(valor: str) -> str:
        """Valida y normaliza el codigo del estudiante."""
        codigo = valor.strip()
        if len(codigo) != 8:
            raise CodigoInvalidoError(
                "El codigo del estudiante debe tener exactamente 8 caracteres."
            )
        return codigo

    @staticmethod
    def _validar_materia(valor: str) -> str:
        """Valida y normaliza el nombre de la materia."""
        materia = valor.strip()
        if not materia:
            raise MateriaInvalidaError("La materia no puede estar vacia.")
        return materia

    @staticmethod
    def _normalizar_nota(valor: float) -> float:
        """Valida la nota y la devuelve en formato numerico."""
        try:
            nota = float(valor)
        except (TypeError, ValueError) as exc:
            raise NotaInvalidaError("La nota debe ser un numero valido.") from exc

        if not math.isfinite(nota) or nota < 0.0 or nota > 10.0:
            raise NotaInvalidaError("La nota debe estar entre 0.0 y 10.0.")
        return round(nota, 2)

