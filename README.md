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

## Estructura

```
app/
  main.py           # app FastAPI, CORS, startup, routers
  config.py         # settings desde variables de entorno
  database.py       # engine/session SQLAlchemy
  models.py         # tablas: users, profiles, checkins, cv_reviews, interview_sessions, badges, device_tokens
  schemas.py        # esquemas Pydantic
  security.py       # hash de password (bcrypt) + JWT
  deps.py           # get_current_user, require_role
  routers/          # un router por caso de uso (auth, profile, checkin, wellbeing, cv, interview, badges, dashboard, institucion)
  services/
    ai_service.py       # unico punto que llama a internet (Groq), con fallback offline
    badges_service.py   # logica de insignias (UC-11)
  fixtures/          # respuestas pre-generadas (modo demo offline) y KPIs mock (UC-13)
```

## Notas de conexion (Flutter / React)

- Emulador Android: usar `http://10.0.2.2:8000`, no `localhost`.
- Celular fisico por USB: `adb reverse tcp:8000 tcp:8000`.
- Celular fisico por Wi-Fi: usar la IP local de la laptop (`192.168.x.x:8000`).
- React (Vite): configurar `VITE_API_URL` en `.env` del proyecto web.

## Roles

`users.role` puede ser `joven` (app movil), `institucion` o `empresa` (panel web). El endpoint `/institucion/kpis` exige rol `institucion` o `empresa`.
