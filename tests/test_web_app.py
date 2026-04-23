"""Pruebas de integracion para la app Flask con PostgreSQL temporal."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TemporaryPostgres:
    """Levanta una instancia local y temporal de PostgreSQL para pruebas."""

    def __init__(self) -> None:
        self.root_dir: Path | None = None
        self.data_dir: Path | None = None
        self.socket_dir: Path | None = None
        self.log_path: Path | None = None
        self.port: int | None = None
        self.database_url = ""

    def __enter__(self) -> TemporaryPostgres:
        self.root_dir = Path(tempfile.mkdtemp(prefix="registro-pg-"))
        self.data_dir = self.root_dir / "data"
        self.socket_dir = self.root_dir / "socket"
        self.log_path = self.root_dir / "postgres.log"
        self.socket_dir.mkdir(parents=True, exist_ok=True)
        self.port = _find_free_port()

        self._run(
            [
                "initdb",
                "-A",
                "trust",
                "-U",
                "postgres",
                "-D",
                str(self.data_dir),
            ]
        )
        self._run(
            [
                "pg_ctl",
                "-D",
                str(self.data_dir),
                "-l",
                str(self.log_path),
                "-o",
                f"-F -p {self.port} -h 127.0.0.1 -k {self.socket_dir}",
                "-w",
                "start",
            ]
        )
        self._run(
            [
                "psql",
                "-h",
                "127.0.0.1",
                "-p",
                str(self.port),
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-c",
                "CREATE DATABASE registro_test",
            ]
        )
        self.database_url = f"postgresql://postgres@127.0.0.1:{self.port}/registro_test"
        return self

    def __exit__(self, *_: object) -> None:
        if self.data_dir is not None:
            subprocess.run(
                ["pg_ctl", "-D", str(self.data_dir), "-m", "immediate", "stop"],
                check=False,
                capture_output=True,
                text=True,
            )
        if self.root_dir is not None:
            shutil.rmtree(self.root_dir, ignore_errors=True)

    @staticmethod
    def _run(command: list[str]) -> None:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Fallo ejecutando {' '.join(command)}\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class WebAppIntegrationTests(unittest.TestCase):
    """Valida el flujo HTTP principal usando una base PostgreSQL real."""

    def test_crud_flow_and_report_generation(self) -> None:
        with TemporaryPostgres() as postgres:
            report_dir = Path(tempfile.mkdtemp(prefix="registro-reportes-"))
            self.addCleanup(shutil.rmtree, report_dir, True)

            app = create_app(
                AppConfig(
                    base_dir=PROJECT_ROOT,
                    database_url=postgres.database_url,
                    host="127.0.0.1",
                    port=8000,
                    debug=False,
                    reports_dir=report_dir,
                    legacy_snapshot_path=None,
                    bootstrap_legacy_data=False,
                )
            )
            client = app.test_client()

            health = client.get("/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.get_json()["status"], "ok")

            created = client.post(
                "/api/students",
                json={"codigo": "20240001", "nombre": "Ana Torres"},
            )
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.get_json()["codigo"], "20240001")

            grade = client.post(
                "/api/grades",
                json={"codigo": "20240001", "materia": "Programacion", "nota": 8.5},
            )
            self.assertEqual(grade.status_code, 200)
            self.assertEqual(grade.get_json()["materias_totales"], 1)

            updated_student = client.put(
                "/api/students/20240001",
                json={"nombre": "Ana Maria Torres"},
            )
            self.assertEqual(updated_student.status_code, 200)
            self.assertEqual(updated_student.get_json()["nombre"], "Ana Maria Torres")

            updated_grade = client.put(
                "/api/grades/20240001/Programacion",
                json={"materia": "Base de Datos", "nota": 9.1},
            )
            self.assertEqual(updated_grade.status_code, 200)
            self.assertEqual(updated_grade.get_json()["notas"]["Base de Datos"], 9.1)

            summary = client.get("/api/summary")
            self.assertEqual(summary.status_code, 200)
            self.assertEqual(summary.get_json()["estudiantes_totales"], 1)
            self.assertEqual(summary.get_json()["materias_totales"], 1)

            meta = client.get("/api/meta")
            self.assertEqual(meta.status_code, 200)
            self.assertIn("registro_test", meta.get_json()["database"])

            report = client.post("/api/reports/20240001", json={})
            self.assertEqual(report.status_code, 200)
            report_path = report_dir / "20240001.txt"
            self.assertTrue(report_path.exists())
            self.assertIn("Ana Maria Torres", report_path.read_text(encoding="utf-8"))

            deleted_grade = client.delete("/api/grades/20240001/Base%20de%20Datos")
            self.assertEqual(deleted_grade.status_code, 200)
            self.assertEqual(deleted_grade.get_json()["resumen"]["materias_totales"], 0)

            deleted_student = client.delete("/api/students/20240001")
            self.assertEqual(deleted_student.status_code, 200)

            students = client.get("/api/students")
            self.assertEqual(students.status_code, 200)
            self.assertEqual(students.get_json(), [])

    def test_bootstrap_legacy_snapshot_when_database_is_empty(self) -> None:
        with TemporaryPostgres() as postgres:
            report_dir = Path(tempfile.mkdtemp(prefix="registro-reportes-"))
            snapshot_dir = Path(tempfile.mkdtemp(prefix="registro-snapshot-"))
            snapshot_path = snapshot_dir / "legacy.json"
            self.addCleanup(shutil.rmtree, report_dir, True)
            self.addCleanup(shutil.rmtree, snapshot_dir, True)

            snapshot_path.write_text(
                json.dumps(
                    {
                        "estudiantes": [
                            {
                                "codigo": "20249999",
                                "nombre": "Miguel Rojas",
                                "notas": {"Historia": 7.5},
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            app = create_app(
                AppConfig(
                    base_dir=PROJECT_ROOT,
                    database_url=postgres.database_url,
                    host="127.0.0.1",
                    port=8000,
                    debug=False,
                    reports_dir=report_dir,
                    legacy_snapshot_path=snapshot_path,
                    bootstrap_legacy_data=True,
                )
            )
            client = app.test_client()

            students = client.get("/api/students")
            self.assertEqual(students.status_code, 200)
            payload = students.get_json()
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["codigo"], "20249999")
            self.assertEqual(payload[0]["notas"]["Historia"], 7.5)


if __name__ == "__main__":
    unittest.main()
