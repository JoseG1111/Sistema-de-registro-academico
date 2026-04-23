SISTEMA DE REGISTRO ACADEMICO

Descripcion general
Este proyecto ahora ejecuta una aplicacion web Flask con arquitectura MVC,
persistencia en PostgreSQL y despliegue recomendado con Gunicorn + Nginx en
Ubuntu. La interfaz permite registrar estudiantes, cargar notas, editar
registros, eliminarlos y generar reportes individuales en texto plano.

Cambios principales
- Ya no se usa CSV como fuente de datos de la aplicacion.
- Ya no se escribe el autosave en app/registros.json.
- Todos los cambios se guardan directamente en PostgreSQL.
- Si la base esta vacia y BOOTSTRAP_LEGACY_DATA=true, la app puede migrar una
  sola vez el contenido heredado de app/registros.json.
- Se agregaron archivos listos para despliegue:
  - wsgi.py
  - requirements.txt
  - .env.example
  - deploy/gunicorn.conf.py
  - deploy/registro-academico.service
  - deploy/nginx-registro-academico.conf

Variables de entorno
- DATABASE_URL: obligatoria. Ejemplo:
  postgresql://registro_user:clave@127.0.0.1:5432/registro_academico
- APP_HOST: host para desarrollo local. Valor por defecto: 127.0.0.1
- APP_PORT: puerto para desarrollo local. Valor por defecto: 8000
- APP_DEBUG: modo debug local. Valor por defecto: false
- REPORTS_DIR: carpeta donde se guardan los reportes. Valor por defecto:
  storage/reportes
- BOOTSTRAP_LEGACY_DATA: migra app/registros.json si la base esta vacia.
  Valor por defecto: true
- LEGACY_SNAPSHOT_PATH: ruta del snapshot heredado. Valor por defecto:
  app/registros.json
- GUNICORN_BIND, WEB_CONCURRENCY, GUNICORN_THREADS, GUNICORN_TIMEOUT:
  parametros del servidor Gunicorn

Preparacion local
1. Crear entorno virtual:
   python3 -m venv .venv

2. Instalar dependencias:
   .venv/bin/pip install -r requirements.txt

3. Copiar el archivo de entorno:
   cp .env.example .env

4. Crear la base de datos en PostgreSQL:
   psql -U postgres -c "CREATE USER registro_user WITH PASSWORD 'cambia-esta-clave';"
   psql -U postgres -c "CREATE DATABASE registro_academico OWNER registro_user;"

5. Ajustar DATABASE_URL dentro de .env si hace falta.

6. Ejecutar la aplicacion:
   .venv/bin/python main.py

La app quedara disponible en http://127.0.0.1:8000 por defecto.

Despliegue en Ubuntu
1. Instalar dependencias del sistema:
   sudo apt update
   sudo apt install -y python3 python3-venv postgresql postgresql-contrib nginx

2. Subir el proyecto a /opt/registro-academico o una ruta similar.

3. Crear entorno virtual e instalar dependencias:
   cd /opt/registro-academico
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt

4. Crear base de datos y usuario en PostgreSQL:
   sudo -u postgres psql -c "CREATE USER registro_user WITH PASSWORD 'cambia-esta-clave';"
   sudo -u postgres psql -c "CREATE DATABASE registro_academico OWNER registro_user;"

5. Crear .env a partir de .env.example y ajustar DATABASE_URL.

6. Copiar el servicio systemd:
   sudo cp deploy/registro-academico.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now registro-academico

7. Copiar la configuracion de Nginx:
   sudo cp deploy/nginx-registro-academico.conf /etc/nginx/sites-available/registro-academico
   sudo ln -s /etc/nginx/sites-available/registro-academico /etc/nginx/sites-enabled/registro-academico
   sudo nginx -t
   sudo systemctl reload nginx

Entrypoints
- Desarrollo: python3 main.py
- Produccion: gunicorn --config deploy/gunicorn.conf.py wsgi:app
- Salud: GET /health

Estructura actual
app/
|-- config.py
|-- main.py
|-- controllers/
|-- models/
|-- persistences/
|   |-- errors.py
|   |-- estudiante_repository.py
|   |-- file_manager.py
|   |-- legacy_snapshot.py
|-- views/
|   |-- estudiante/
|       |-- estudiante_view.py
|       |-- formulario.py
|       |-- static/
|           |-- app.js
|           |-- styles.css
deploy/
|-- gunicorn.conf.py
|-- nginx-registro-academico.conf
|-- registro-academico.service
wsgi.py

Notas finales
- Los reportes se generan en el directorio definido por REPORTS_DIR.
- PostgreSQL crea las tablas necesarias automaticamente al iniciar.
- Si no deseas migrar el snapshot heredado, define BOOTSTRAP_LEGACY_DATA=false.
