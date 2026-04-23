"""Vista web para gestionar estudiantes con Flask."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from pathlib import Path

from flask import Flask, Response, jsonify, request

from app.controllers import EstudianteController, ReporteError
from app.models import EstudianteError, EstudianteNoEncontradoError
from app.persistences import PersistenciaError

from .formulario import ESTUDIANTE_FIELDS, NOTA_FIELDS, render_modal_form


class EstudianteView:
    """Construye la vista HTML y expone endpoints HTTP para la interfaz."""

    def __init__(self, controlador: EstudianteController) -> None:
        """Inicializa la vista con su controlador y rutas estaticas."""
        self._controlador = controlador
        self.__directorio_vista = Path(__file__).resolve().parent
        self.__directorio_static = self.__directorio_vista / "static"

    @property
    def directorio_static(self) -> Path:
        """Devuelve el directorio de archivos estaticos."""
        return self.__directorio_static

    def registrar_rutas(self, app: Flask) -> None:
        """Registra las rutas HTML, API y salud sobre una app Flask."""

        @app.after_request
        def deshabilitar_cache(respuesta: Response) -> Response:
            if request.path == "/" or request.path.startswith("/api/") or request.path == "/health":
                respuesta.headers["Cache-Control"] = "no-store"
            return respuesta

        @app.get("/")
        def index() -> Response:
            return Response(self._renderizar_html(), mimetype="text/html")

        @app.get("/health")
        def health() -> tuple[Response, HTTPStatus]:
            try:
                estado = self._controlador.verificar_salud()
            except PersistenciaError as exc:
                return (
                    jsonify({"status": "error", "error": str(exc)}),
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
            return jsonify(estado), HTTPStatus.OK

        @app.get("/api/meta")
        def obtener_meta() -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    {
                        "database": self._controlador.obtener_info_persistencia()["database"],
                        "reports_dir": self._formatear_ruta(
                            self._controlador.obtener_directorio_reportes()
                        ),
                    },
                    HTTPStatus.OK,
                )
            )

        @app.get("/api/summary")
        def obtener_resumen() -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    self._controlador.obtener_resumen_general(),
                    HTTPStatus.OK,
                )
            )

        @app.get("/api/students")
        def listar_estudiantes() -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    self._controlador.listar_resumenes_estudiantes(),
                    HTTPStatus.OK,
                )
            )

        @app.get("/api/students/<codigo>")
        def obtener_estudiante(codigo: str) -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    self._controlador.obtener_resumen_estudiante(codigo),
                    HTTPStatus.OK,
                )
            )

        @app.post("/api/students")
        def crear_estudiante() -> tuple[Response, HTTPStatus]:
            payload = request.get_json(silent=True) or {}
            return self._respuesta_api(
                lambda: (
                    self._controlador.crear_estudiante(
                        nombre=str(payload.get("nombre", "")),
                        codigo=str(payload.get("codigo", "")),
                    ),
                    HTTPStatus.CREATED,
                )
            )

        @app.put("/api/students/<codigo>")
        def actualizar_estudiante(codigo: str) -> tuple[Response, HTTPStatus]:
            payload = request.get_json(silent=True) or {}
            return self._respuesta_api(
                lambda: (
                    self._controlador.actualizar_estudiante(
                        codigo,
                        str(payload.get("nombre", "")),
                    ),
                    HTTPStatus.OK,
                )
            )

        @app.delete("/api/students/<codigo>")
        def eliminar_estudiante(codigo: str) -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    {
                        "message": "Estudiante eliminado correctamente.",
                        **self._controlador.eliminar_estudiante(codigo),
                    },
                    HTTPStatus.OK,
                )
            )

        @app.post("/api/grades")
        def crear_nota() -> tuple[Response, HTTPStatus]:
            payload = request.get_json(silent=True) or {}
            return self._respuesta_api(
                lambda: (
                    self._controlador.registrar_nota(
                        codigo=str(payload.get("codigo", "")),
                        materia=str(payload.get("materia", "")),
                        nota=float(payload.get("nota", "")),
                    ),
                    HTTPStatus.OK,
                )
            )

        @app.put("/api/grades/<codigo>/<path:materia_actual>")
        def editar_nota(codigo: str, materia_actual: str) -> tuple[Response, HTTPStatus]:
            payload = request.get_json(silent=True) or {}
            return self._respuesta_api(
                lambda: (
                    self._controlador.editar_nota(
                        codigo=codigo,
                        materia_actual=materia_actual,
                        materia_nueva=str(payload.get("materia", "")),
                        nota_nueva=float(payload.get("nota", "")),
                    ),
                    HTTPStatus.OK,
                )
            )

        @app.delete("/api/grades/<codigo>/<path:materia>")
        def eliminar_nota(codigo: str, materia: str) -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    {
                        "message": "Materia eliminada correctamente.",
                        "resumen": self._controlador.eliminar_nota(codigo, materia),
                    },
                    HTTPStatus.OK,
                )
            )

        @app.post("/api/reports")
        def generar_reportes() -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    {
                        "message": "Reportes generados correctamente.",
                        "rutas": [
                            self._formatear_ruta(ruta_generada)
                            for ruta_generada in self._controlador.generar_reportes_todos()
                        ],
                    },
                    HTTPStatus.OK,
                )
            )

        @app.post("/api/reports/<codigo>")
        def generar_reporte_individual(codigo: str) -> tuple[Response, HTTPStatus]:
            return self._respuesta_api(
                lambda: (
                    {
                        "message": "Reporte individual generado correctamente.",
                        "ruta": self._formatear_ruta(
                            self._controlador.generar_reporte_individual(codigo)
                        ),
                    },
                    HTTPStatus.OK,
                )
            )

        @app.errorhandler(404)
        def ruta_no_encontrada(_: Exception) -> tuple[Response, HTTPStatus] | Response:
            if request.path.startswith("/api/") or request.path == "/health":
                return (
                    jsonify({"error": "La ruta solicitada no existe."}),
                    HTTPStatus.NOT_FOUND,
                )
            return Response(
                "La ruta solicitada no existe.",
                status=HTTPStatus.NOT_FOUND,
                mimetype="text/plain",
            )

    def _respuesta_api(
        self,
        operacion: Callable[[], tuple[object, HTTPStatus]],
    ) -> tuple[Response, HTTPStatus]:
        """Ejecuta una operacion de API y transforma excepciones en JSON."""
        try:
            payload, estado = operacion()
            return jsonify(payload), estado
        except EstudianteNoEncontradoError as exc:
            return jsonify({"error": str(exc)}), HTTPStatus.NOT_FOUND
        except (EstudianteError, PersistenciaError, ReporteError, ValueError) as exc:
            return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    def _renderizar_html(self) -> str:
        """Compone el documento HTML base de la aplicacion."""
        modal_estudiante = render_modal_form(
            "student-modal",
            "student-form",
            "Nuevo estudiante",
            "Crea un registro individual con nombre y codigo unico de 8 caracteres.",
            ESTUDIANTE_FIELDS,
            "Guardar estudiante",
        )
        modal_nota = render_modal_form(
            "grade-modal",
            "grade-form",
            "Registrar nota",
            "Asigna o edita una calificacion individual por materia.",
            NOTA_FIELDS,
            "Guardar nota",
        )

        return f"""<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registro Academico</title>
    <link rel="stylesheet" href="/static/styles.css">
  </head>
  <body>
    <div class="ambient-glow ambient-one"></div>
    <div class="ambient-glow ambient-two"></div>
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand-card">
          <p class="eyebrow">Arquitectura MVC</p>
          <h1>Registro academico</h1>
          <p class="sidebar-copy">
            Gestiona estudiantes, notas y reportes desde una aplicacion web lista para PostgreSQL y despliegue en Ubuntu.
          </p>
        </div>

        <div class="sidebar-actions">
          <button id="new-student-button" class="primary-button">Nuevo estudiante</button>
          <button id="new-grade-button" class="secondary-button">Registrar nota</button>
          <button id="student-report-button" class="ghost-button">Reporte individual</button>
          <button id="all-reports-button" class="ghost-button">Reportes de todos</button>
        </div>

        <div class="sidebar-card">
          <p class="notes-title">Base de datos</p>
          <p class="sidebar-card-copy">
            Todos los cambios se guardan en tiempo real en
            <strong id="database-label">PostgreSQL</strong>.
          </p>
        </div>

        <div class="sidebar-card">
          <p class="notes-title">Reportes</p>
          <p class="sidebar-card-copy">
            Los reportes individuales se escriben en
            <strong id="reports-dir">storage/reportes</strong>.
          </p>
        </div>

        <div class="sidebar-card notes-card">
          <p class="notes-title">Despliegue</p>
          <p>1. Configura PostgreSQL mediante DATABASE_URL.</p>
          <p>2. Publica la app con Gunicorn y Nginx en Ubuntu.</p>
          <p>3. Supervisa disponibilidad con el endpoint /health.</p>
        </div>
      </aside>

      <main class="content">
        <header class="hero">
          <div>
            <p class="eyebrow">Web + PostgreSQL</p>
            <h2>Panel de control academico</h2>
            <p class="hero-copy">
              Visualiza promedios, estados, materias, filtros y acciones CRUD desde una sola pantalla, ahora con persistencia en PostgreSQL.
            </p>
          </div>
          <div class="hero-badge">
            <span>PostgreSQL</span>
            <span>Gunicorn</span>
            <span>Nginx</span>
            <span>MVC</span>
          </div>
        </header>

        <section class="summary-grid">
          <article class="summary-card accent-light">
            <p>Total de estudiantes</p>
            <h3 id="summary-total">0</h3>
          </article>
          <article class="summary-card accent-dark">
            <p>Promedio general</p>
            <h3 id="summary-average">0.00</h3>
          </article>
          <article class="summary-card accent-success">
            <p>Aprobados</p>
            <h3 id="summary-approved">0</h3>
          </article>
          <article class="summary-card accent-alert">
            <p>Reprobados</p>
            <h3 id="summary-failed">0</h3>
          </article>
          <article class="summary-card accent-warning">
            <p>Materias cargadas</p>
            <h3 id="summary-subjects">0</h3>
          </article>
        </section>

        <section class="dashboard-grid">
          <article class="panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Tabla principal</p>
                <h3>Estudiantes registrados</h3>
              </div>
              <button id="refresh-button" class="mini-button">Actualizar</button>
            </div>

            <div class="toolbar">
              <label class="toolbar-field">
                <span>Buscar</span>
                <input id="student-search" type="search" placeholder="Nombre o codigo">
              </label>
              <label class="toolbar-field">
                <span>Estado</span>
                <select id="status-filter">
                  <option value="todos">Todos</option>
                  <option value="Aprobado">Aprobado</option>
                  <option value="Reprobado">Reprobado</option>
                  <option value="Pendiente">Pendiente</option>
                </select>
              </label>
            </div>

            <div class="panel-subline">
              <span id="results-counter">0 resultados</span>
              <span id="students-meta">Sincronizado</span>
            </div>

            <div class="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>Codigo</th>
                    <th>Nombre</th>
                    <th>Materias</th>
                    <th>Promedio</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody id="students-body">
                  <tr>
                    <td colspan="5" class="empty-state">Todavia no hay estudiantes cargados.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article class="panel detail-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Detalle</p>
                <h3 id="detail-name">Sin seleccion</h3>
              </div>
              <span id="detail-status" class="status-pill neutral">Pendiente</span>
            </div>

            <div class="detail-toolbar">
              <button id="edit-student-button" class="mini-button" disabled>Editar estudiante</button>
              <button id="delete-student-button" class="danger-button" disabled>Eliminar estudiante</button>
            </div>

            <div class="detail-grid">
              <div class="detail-card">
                <span>Codigo</span>
                <strong id="detail-code">Sin seleccion</strong>
              </div>
              <div class="detail-card">
                <span>Promedio</span>
                <strong id="detail-average">0.00</strong>
              </div>
            </div>

            <div class="notes-wrapper">
              <div class="notes-head">
                <div>
                  <p class="panel-kicker">Notas registradas</p>
                  <p class="notes-helper">Selecciona una materia para editarla o eliminarla.</p>
                </div>
                <div class="inline-actions">
                  <button id="edit-note-button" class="mini-button" disabled>Editar nota</button>
                  <button id="delete-note-button" class="danger-button" disabled>Eliminar nota</button>
                </div>
              </div>
              <div class="table-shell compact">
                <table>
                  <thead>
                    <tr>
                      <th>Materia</th>
                      <th>Nota</th>
                    </tr>
                  </thead>
                  <tbody id="notes-body">
                    <tr>
                      <td colspan="2" class="empty-state">Selecciona un estudiante para ver sus notas.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </article>
        </section>

        <footer class="status-bar">
          <span id="status-indicator" class="indicator info"></span>
          <p id="status-text">
            Listo para iniciar. Registra estudiantes y notas; todos los cambios se guardan en PostgreSQL.
          </p>
        </footer>
      </main>
    </div>

    {modal_estudiante}
    {modal_nota}

    <script src="/static/app.js"></script>
  </body>
</html>"""

    def _formatear_ruta(self, ruta: Path) -> str:
        """Muestra rutas relativas al directorio base cuando sea posible."""
        try:
            return str(ruta.relative_to(self._controlador.obtener_directorio_base()))
        except ValueError:
            return str(ruta)
