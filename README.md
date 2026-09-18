# Rumbo — Backend (FastAPI + PostgreSQL)

Backend unico para las tres superficies de Rumbo (app movil Flutter, landing web y panel web), segun `RUMBO_Casos_de_Uso_Implementacion.md`.

## Requisitos previos

- Python 3.11+
- PostgreSQL corriendo localmente, con la base `rumbo` ya creada:
  ```sql
  CREATE DATABASE rumbo;
  ```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env         # Windows (o cp en bash)
```

Editar `.env` con la cadena de conexion real y (opcional) la API key de Groq.

## Correr el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Las tablas se crean automaticamente al iniciar (`Base.metadata.create_all`), sin Alembic.

Docs interactivas: http://localhost:8000/docs

### Alternativa con Docker

```bash
docker compose up
```

Levanta Postgres + la API juntos (`Dockerfile` + `docker-compose.yml`), sin instalar nada en el sistema.

### Datos de ejemplo

```bash
python -m app.seed
```

Llena todas las tablas con datos falsos (jovenes, mentores, instituciones/empresas, vacantes y postulaciones con 12 meses de historial) para poder ver el panel y el dashboard con contenido real. Ver el docstring de `app/seed.py` para el detalle (borra los datos existentes antes de sembrar).

## Estructura

```
app/
  main.py           # app FastAPI, CORS, startup, routers
  config.py         # settings desde variables de entorno
  database.py       # engine/session SQLAlchemy
  models.py         # users, profiles, experiencias_laborales, checkins, cv_reviews,
                     # interview_sessions, badges, device_tokens, mentor_profiles,
                     # mentorias(+mensajes), mentorias_grupales(+inscripciones),
                     # vacantes, postulaciones
  schemas.py        # esquemas Pydantic
  security.py       # hash de password (bcrypt) + JWT
  deps.py           # get_current_user, require_role
  routers/
    auth.py, profile.py, checkin.py, wellbeing.py, cv.py, interview.py,
    badges.py, dashboard.py, institucion.py, mentoring.py, vacantes.py
  services/
    ai_service.py       # unico punto que llama a internet (Groq), con fallback offline
    badges_service.py   # logica de insignias (UC-11)
    kpi_service.py      # KPIs institucionales calculados sobre datos reales (UC-13)
    ml_service.py       # prediccion de demanda de vacantes con regresion lineal (scikit-learn)
  fixtures/          # respuestas pre-generadas para el modo demo offline
  seed.py            # datos de ejemplo para desarrollo/demo
```

## Notas de conexion (Flutter / React)

- Emulador Android: usar `http://10.0.2.2:8000`, no `localhost`.
- Celular fisico por USB: `adb reverse tcp:8000 tcp:8000`.
- Celular fisico por Wi-Fi: usar la IP local de la laptop (`192.168.x.x:8000`) — configurable en `lib/config.dart` del lado de Flutter.
- React (Vite): configurar `VITE_API_URL` en `.env` del proyecto web.

## Roles

`users.role` puede ser `joven` (app movil), `mentor` (app movil), o `institucion`/`empresa` (panel web). El endpoint `/institucion/kpis` y el resto de `/institucion/*` y `/vacantes/*` de gestion exigen rol `institucion` o `empresa`; los endpoints de `/mentoring/*` que crean/gestionan mentorias exigen rol `mentor`.
