"""Repositorio PostgreSQL para estudiantes y notas."""

from __future__ import annotations

from decimal import Decimal

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from app.models import Estudiante

from .errors import PersistenciaError


class EstudianteRepository:
    """Almacena estudiantes y notas en PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        """Configura el repositorio usando una URL de conexion PostgreSQL."""
        self.__database_url = database_url
        self.ensure_schema()

    def existe(self, codigo: str) -> bool:
        """Indica si ya existe un estudiante con el codigo dado."""
        consulta = "SELECT 1 FROM estudiantes WHERE codigo = %s LIMIT 1"
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, (codigo,))
                return cursor.fetchone() is not None

    def guardar(self, estudiante: Estudiante) -> None:
        """Guarda o actualiza un estudiante con todas sus notas."""
        insercion_estudiante = """
            INSERT INTO estudiantes (codigo, nombre)
            VALUES (%s, %s)
            ON CONFLICT (codigo) DO UPDATE
            SET nombre = EXCLUDED.nombre, actualizado_en = NOW()
        """
        borrado_notas = "DELETE FROM notas WHERE estudiante_codigo = %s"
        insercion_nota = """
            INSERT INTO notas (estudiante_codigo, materia, nota)
            VALUES (%s, %s, %s)
        """

        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    insercion_estudiante,
                    (estudiante.codigo, estudiante.nombre),
                )
                cursor.execute(borrado_notas, (estudiante.codigo,))
                if estudiante.notas:
                    cursor.executemany(
                        insercion_nota,
                        [
                            (estudiante.codigo, materia, nota)
                            for materia, nota in sorted(
                                estudiante.notas.items(),
                                key=lambda item: item[0].casefold(),
                            )
                        ],
                    )

    def obtener(self, codigo: str) -> Estudiante | None:
        """Recupera un estudiante por codigo si existe."""
        consulta = """
            SELECT e.codigo, e.nombre, n.materia, n.nota
            FROM estudiantes AS e
            LEFT JOIN notas AS n
              ON n.estudiante_codigo = e.codigo
            WHERE e.codigo = %s
            ORDER BY LOWER(COALESCE(n.materia, '')), n.materia
        """
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, (codigo,))
                filas = cursor.fetchall()
        if not filas:
            return None
        return self._construir_estudiante(filas)

    def eliminar(self, codigo: str) -> None:
        """Elimina un estudiante por codigo si existe."""
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("DELETE FROM estudiantes WHERE codigo = %s", (codigo,))

    def esta_vacio(self) -> bool:
        """Indica si la base de datos no tiene estudiantes."""
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM estudiantes")
                resultado = cursor.fetchone()
        return int(resultado["total"]) == 0

    def vaciar(self) -> None:
        """Elimina todos los estudiantes registrados."""
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("DELETE FROM estudiantes")

    def listar(self) -> list[Estudiante]:
        """Devuelve todos los estudiantes ordenados por codigo."""
        consulta = """
            SELECT e.codigo, e.nombre, n.materia, n.nota
            FROM estudiantes AS e
            LEFT JOIN notas AS n
              ON n.estudiante_codigo = e.codigo
            ORDER BY e.codigo, LOWER(COALESCE(n.materia, '')), n.materia
        """
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(consulta)
                filas = cursor.fetchall()
        return self._construir_estudiantes(filas)

    def ping(self) -> None:
        """Verifica que la conexion actual responda correctamente."""
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1")

    def obtener_etiqueta_conexion(self) -> str:
        """Devuelve una referencia segura del destino PostgreSQL actual."""
        try:
            parametros = conninfo_to_dict(self.__database_url)
        except (psycopg.Error, TypeError, ValueError):
            return "PostgreSQL"

        host = parametros.get("host") or "localhost"
        port = parametros.get("port")
        database = parametros.get("dbname") or "postgres"
        if port:
            return f"{database} @ {host}:{port}"
        return f"{database} @ {host}"

    def ensure_schema(self) -> None:
        """Crea las tablas base si todavia no existen."""
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS estudiantes (
                        codigo VARCHAR(8) PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notas (
                        id BIGSERIAL PRIMARY KEY,
                        estudiante_codigo VARCHAR(8) NOT NULL REFERENCES estudiantes(codigo)
                            ON DELETE CASCADE,
                        materia TEXT NOT NULL,
                        nota NUMERIC(4, 2) NOT NULL CHECK (nota >= 0 AND nota <= 10),
                        creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_notas_estudiante_materia_ci
                    ON notas (estudiante_codigo, LOWER(materia))
                    """
                )

    def _conectar(self) -> psycopg.Connection[dict[str, object]]:
        """Abre una conexion corta hacia PostgreSQL."""
        try:
            return psycopg.connect(
                self.__database_url,
                row_factory=dict_row,
                connect_timeout=5,
            )
        except psycopg.Error as exc:
            raise PersistenciaError(
                "No se pudo conectar a PostgreSQL con la configuracion actual."
            ) from exc

    def _construir_estudiantes(
        self,
        filas: list[dict[str, object]],
    ) -> list[Estudiante]:
        """Agrupa filas relacionales y reconstruye objetos de dominio."""
        agrupados: dict[str, list[dict[str, object]]] = {}
        for fila in filas:
            codigo = str(fila["codigo"])
            agrupados.setdefault(codigo, []).append(fila)
        return [self._construir_estudiante(agrupados[codigo]) for codigo in agrupados]

    def _construir_estudiante(
        self,
        filas: list[dict[str, object]],
    ) -> Estudiante:
        """Convierte filas de consulta en un estudiante de dominio."""
        primera_fila = filas[0]
        try:
            estudiante = Estudiante(
                nombre=str(primera_fila["nombre"]),
                codigo=str(primera_fila["codigo"]),
            )
            for fila in filas:
                materia = fila["materia"]
                nota = fila["nota"]
                if materia is None or nota is None:
                    continue
                if isinstance(nota, Decimal):
                    nota = float(nota)
                estudiante.registrar_nota(str(materia), float(nota))
        except Exception as exc:  # pragma: no cover - ruta defensiva ante corrupcion manual
            raise PersistenciaError(
                "La base de datos contiene registros invalidos para estudiantes o notas."
            ) from exc
        return estudiante
