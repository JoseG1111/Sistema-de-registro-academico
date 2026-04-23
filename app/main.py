"""Arranque principal de la aplicacion web desplegable."""

from __future__ import annotations

from flask import Flask

from app.config import AppConfig, ConfiguracionError
from app.controllers import EstudianteController, PersistenciaError
from app.views.estudiante import EstudianteView


def create_app(config: AppConfig | None = None) -> Flask:
    """Construye la aplicacion Flask con sus rutas y servicios."""
    configuracion = config or AppConfig.from_env()
    controlador = EstudianteController(configuracion)
    vista = EstudianteView(controlador)

    app = Flask(
        __name__,
        static_folder=str(vista.directorio_static),
        static_url_path="/static",
    )
    app.json.ensure_ascii = False
    vista.registrar_rutas(app)
    return app


def main() -> None:
    """Inicia el servidor de desarrollo local con configuracion de entorno."""
    try:
        configuracion = AppConfig.from_env()
        app = create_app(configuracion)
    except (ConfiguracionError, PersistenciaError) as exc:
        raise SystemExit(f"No se pudo iniciar el sistema: {exc}") from exc

    print(
        "Aplicacion disponible en "
        f"http://{configuracion.host}:{configuracion.port}"
    )
    app.run(
        host=configuracion.host,
        port=configuracion.port,
        debug=configuracion.debug,
    )


if __name__ == "__main__":
    main()
