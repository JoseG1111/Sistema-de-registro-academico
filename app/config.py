"""Configuracion de entorno para la aplicacion web."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


class ConfiguracionError(ValueError):
    """Se lanza cuando falta una variable obligatoria o es invalida."""


@dataclass(frozen=True)
class AppConfig:
    """Parametros de ejecucion y despliegue de la aplicacion."""

    base_dir: Path
    database_url: str
    host: str
    port: int
    debug: bool
    reports_dir: Path
    legacy_snapshot_path: Path | None
    bootstrap_legacy_data: bool

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        base_dir: Path | None = None,
    ) -> AppConfig:
        """Construye la configuracion a partir del entorno y un archivo .env local."""
        raiz = base_dir or Path(__file__).resolve().parents[1]
        variables = _load_environment(raiz / ".env")
        variables.update(os.environ)
        if environ is not None:
            variables.update(environ)

        database_url = (variables.get("DATABASE_URL") or "").strip()
        if not database_url:
            raise ConfiguracionError(
                "Debes definir DATABASE_URL para conectar la aplicacion con PostgreSQL."
            )

        reports_dir = _resolve_path(
            variables.get("REPORTS_DIR", "storage/reportes"),
            raiz,
        )
        legacy_path = (variables.get("LEGACY_SNAPSHOT_PATH") or "app/registros.json").strip()

        return cls(
            base_dir=raiz,
            database_url=database_url,
            host=(variables.get("APP_HOST") or "127.0.0.1").strip() or "127.0.0.1",
            port=_parse_port(variables.get("APP_PORT", "8000")),
            debug=_parse_bool(variables.get("APP_DEBUG"), default=False),
            reports_dir=reports_dir,
            legacy_snapshot_path=_resolve_optional_path(legacy_path, raiz),
            bootstrap_legacy_data=_parse_bool(
                variables.get("BOOTSTRAP_LEGACY_DATA"),
                default=True,
            ),
        )

    @property
    def database_label(self) -> str:
        """Devuelve una referencia segura para mostrar la conexion configurada."""
        partes = urlsplit(self.database_url)
        host = partes.hostname or "localhost"
        port = f":{partes.port}" if partes.port else ""
        database = partes.path.removeprefix("/") or "postgres"
        return f"{database} @ {host}{port}"


def _load_environment(env_path: Path) -> dict[str, str]:
    """Carga pares KEY=VALUE desde un archivo .env si existe."""
    if not env_path.exists():
        return {}

    variables: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        contenido = line.strip()
        if not contenido or contenido.startswith("#") or "=" not in contenido:
            continue
        clave, valor = contenido.split("=", 1)
        variables[clave.strip()] = _strip_quotes(valor.strip())
    return variables


def _strip_quotes(value: str) -> str:
    """Elimina comillas envolventes comunes en archivos .env."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _resolve_path(raw_path: str, base_dir: Path) -> Path:
    """Convierte una ruta relativa en absoluta usando la raiz del proyecto."""
    ruta = Path(raw_path).expanduser()
    if not ruta.is_absolute():
        ruta = base_dir / ruta
    return ruta.resolve()


def _resolve_optional_path(raw_path: str, base_dir: Path) -> Path | None:
    """Resuelve una ruta opcional; una cadena vacia deshabilita el valor."""
    if not raw_path:
        return None
    return _resolve_path(raw_path, base_dir)


def _parse_bool(value: str | None, default: bool) -> bool:
    """Interpreta valores booleanos comunes."""
    if value is None:
        return default
    normalizado = value.strip().casefold()
    if normalizado in {"1", "true", "yes", "on", "si", "sí"}:
        return True
    if normalizado in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_port(value: str) -> int:
    """Valida y devuelve el puerto HTTP configurado."""
    try:
        port = int(value)
    except ValueError as exc:
        raise ConfiguracionError("APP_PORT debe ser un numero entero valido.") from exc

    if port <= 0 or port > 65535:
        raise ConfiguracionError("APP_PORT debe estar entre 1 y 65535.")
    return port
