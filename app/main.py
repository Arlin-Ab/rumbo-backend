from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    auth,
    badges,
    checkin,
    cv,
    dashboard,
    institucion,
    interview,
    mentoring,
    profile,
    vacantes,
    wellbeing,
)

app = FastAPI(title="Rumbo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(checkin.router)
app.include_router(wellbeing.router)
app.include_router(cv.router)
app.include_router(interview.router)
app.include_router(badges.router)
app.include_router(dashboard.router)
app.include_router(institucion.router)
app.include_router(mentoring.router)
app.include_router(vacantes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
