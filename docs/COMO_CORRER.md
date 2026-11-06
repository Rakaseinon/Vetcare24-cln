# Cómo correr VetCare 24 (paso a paso)

Todo se hace desde una terminal **dentro de la carpeta del proyecto** (donde está `README.md`).

## 0. Qué necesitas
| Para… | Instala |
|---|---|
| Correrlo sin Docker | Python 3.12 o más nuevo (`python --version`) |
| Correrlo con PostgreSQL como en producción | Docker Desktop |
| Subirlo a GitHub | Git y una cuenta de GitHub |
| Desplegarlo | Cuenta gratuita en Render (render.com) |

## 1. Correr la API (sin Docker, lo más rápido)
**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
$env:SEED_ON_START = "true"
uvicorn src.api.main:create_app --factory --reload
```
**Mac / Linux**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export SEED_ON_START=true
uvicorn src.api.main:create_app --factory --reload
```
Abre **http://localhost:8000/docs**. Para detenerla: `Ctrl + C`.

- `SEED_ON_START=true` carga los datos del profesor (tutor `VET-C012`, servicios `VET-P001…`, órdenes `VET-O001…`) y las 20 jaulas. Sin esa variable la base arranca vacía y `GET /ordenes/VET-O001` responde 404.
- Sin `DATABASE_URL` usa un archivo SQLite local; no hay que instalar ninguna base de datos.
- Si PowerShell no deja activar el entorno: `Set-ExecutionPolicy -Scope Process Bypass` y vuelve a intentar.

## 2. Correr todo con Docker (API + PostgreSQL)
```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
docker compose up --build
```
API en **http://localhost:8000/docs**. Para borrar la base y empezar limpio: `docker compose down -v`.

> Importante: el build de la imagen de Docker **no se pudo probar en el entorno donde se desarrolló** (solo se validó el `docker-compose.yml`). Córranlo una vez antes de entregar; si falla, mándame el error.

## 3. Correr las pruebas
```bash
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```
Deben pasar **343 pruebas** con **99 %** de cobertura. Con Docker: `docker compose run --rm tests`.
Contra PostgreSQL real: `TEST_DATABASE_URL=postgresql://usuario:clave@localhost:5432/pruebas pytest`.

## 4. Probar en Swagger (http://localhost:8000/docs)
1. La página entra sola como `DIRECTOR`. Para cambiar de rol: **Authorize** → `X-Rol`.
2. Abre un recurso → **Try it out** → **Execute**. El cuerpo ya trae un ejemplo válido.
3. La respuesta está en **Server response** (debajo del `curl`).
4. Recorrido completo de la demo: está en la descripción de la propia página y en `docs/GUIA_DEFENSA.md` §5.

## 5. Subirlo a GitHub con commits de los tres
La rúbrica pide historial de commits del equipo. Cada integrante hace sus propios commits desde su computadora:
```bash
git init -b main
git add .
git commit -m "chore: estructura inicial del proyecto"
git remote add origin https://github.com/<USUARIO>/<REPO>.git
git push -u origin main
```
Después cada quien trabaja en su rama y abre *pull request* (reparto sugerido y mensajes de ejemplo en `docs/GUIA_DEFENSA.md` §6). Agrega a los otros dos como colaboradores y al profesor para que tenga acceso al repositorio. Cada integrante debe configurar **su** correo antes de commitear (`git config user.name` / `git config user.email`).

## 6. Desplegar en Render (Swagger en línea)
1. Con el repo ya en GitHub: Render → **New → Blueprint** → elige el repositorio (usa `render.yaml`).
2. Espera el build y abre `https://<servicio>.onrender.com/docs`.
3. Reemplaza los marcadores `<USUARIO>/<REPO>` y `<TU-SERVICIO>` (con el buscador de tu editor) en `README.md`, en `docs/Reporte_Final_VetCare24.html` y en las diapositivas. Para volver a sacar el PDF: abre el `.html` en Chrome → `Ctrl + P` → *Guardar como PDF*.
4. En el plan gratuito el servicio se duerme: abre la URL unos minutos antes de la defensa.

## 7. Si algo falla
| Síntoma | Causa y arreglo |
|---|---|
| `GET /ordenes/VET-O001` da 404 | Faltó `SEED_ON_START=true`; reinicia con la variable |
| 401 en cualquier recurso | Falta el rol; en `/docs` usa Authorize |
| 403 | El rol no tiene acceso a ese recurso (es RNF-03, a propósito) |
| 409 | Una regla de negocio funcionó: lee el `mensaje` |
| `pip` no instala | Revisa que el entorno virtual esté activo (`(.venv)` en la terminal) |
