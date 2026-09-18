import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import Mentoria, MentoriaGrupal, MentoriaGrupalInscripcion, MentoriaMensaje, MentorProfile, User
from app.schemas import (
    InscritoGrupalOut,
    MensajeIn,
    MensajeOut,
    MentoriaGrupalIn,
    MentoriaGrupalOut,
    MentoriaOut,
    MentoriaRespuestaIn,
    MentoriaSolicitudIn,
    MentorProfileIn,
    MentorProfileOut,
)

router = APIRouter(prefix="/mentoring", tags=["mentoring"])


def _mentor_profile_out(perfil: MentorProfile, nombre: str) -> MentorProfileOut:
    return MentorProfileOut(
        user_id=perfil.user_id,
        nombre=nombre,
        area_expertise=perfil.area_expertise,
        bio=perfil.bio,
        disponibilidad=perfil.disponibilidad,
    )


def _mentoria_out(db: Session, mentoria: Mentoria) -> MentoriaOut:
    mentor = db.get(User, mentoria.mentor_id)
    joven = db.get(User, mentoria.joven_id)
    return MentoriaOut(
        id=mentoria.id,
        mentor_id=mentoria.mentor_id,
        mentor_nombre=mentor.nombre if mentor else "",
        joven_id=mentoria.joven_id,
        joven_nombre=joven.nombre if joven else "",
        estado=mentoria.estado,
        fecha_solicitud=mentoria.fecha_solicitud,
    )


def _verificar_participante(mentoria: Mentoria, user: User) -> None:
    if user.id not in (mentoria.mentor_id, mentoria.joven_id):
        raise HTTPException(status_code=403, detail="No formas parte de esta mentoria")


@router.post("/perfil", response_model=MentorProfileOut)
def upsert_perfil_mentor(
    payload: MentorProfileIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("mentor")),
):
    perfil = db.get(MentorProfile, current_user.id)
    if perfil is None:
        perfil = MentorProfile(user_id=current_user.id)
        db.add(perfil)

    perfil.area_expertise = payload.area_expertise
    perfil.bio = payload.bio
    perfil.disponibilidad = payload.disponibilidad

    db.commit()
    db.refresh(perfil)
    return _mentor_profile_out(perfil, current_user.nombre)


@router.get("/mentores", response_model=list[MentorProfileOut])
def listar_mentores(
    area: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(MentorProfile)
    if area:
        query = query.filter(MentorProfile.area_expertise == area)

    perfiles = query.all()
    return [_mentor_profile_out(p, p.user.nombre) for p in perfiles]


@router.post("/solicitar", response_model=MentoriaOut, status_code=201)
def solicitar_mentoria(
    payload: MentoriaSolicitudIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("joven")),
):
    mentor = db.get(User, payload.mentor_id)
    if mentor is None or mentor.role != "mentor":
        raise HTTPException(status_code=404, detail="Mentor no encontrado")

    existente = (
        db.query(Mentoria)
        .filter(
            Mentoria.mentor_id == payload.mentor_id,
            Mentoria.joven_id == current_user.id,
            Mentoria.estado == "pendiente",
        )
        .first()
    )
    if existente:
        raise HTTPException(status_code=400, detail="Ya tenes una solicitud pendiente con este mentor")

    mentoria = Mentoria(mentor_id=payload.mentor_id, joven_id=current_user.id, estado="pendiente")
    db.add(mentoria)
    db.commit()
    db.refresh(mentoria)

    if payload.mensaje_inicial:
        db.add(MentoriaMensaje(mentoria_id=mentoria.id, remitente_id=current_user.id, texto=payload.mensaje_inicial))
        db.commit()

    return _mentoria_out(db, mentoria)


@router.get("/mias", response_model=list[MentoriaOut])
def mis_mentorias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mentorias = (
        db.query(Mentoria)
        .filter(or_(Mentoria.mentor_id == current_user.id, Mentoria.joven_id == current_user.id))
        .order_by(desc(Mentoria.fecha_solicitud))
        .all()
    )
    return [_mentoria_out(db, m) for m in mentorias]


@router.post("/{mentoria_id}/responder", response_model=MentoriaOut)
def responder_mentoria(
    mentoria_id: uuid.UUID,
    payload: MentoriaRespuestaIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("mentor")),
):
    mentoria = db.get(Mentoria, mentoria_id)
    if mentoria is None or mentoria.mentor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    mentoria.estado = payload.estado
    db.commit()
    db.refresh(mentoria)
    return _mentoria_out(db, mentoria)


@router.get("/{mentoria_id}/mensajes", response_model=list[MensajeOut])
def listar_mensajes(
    mentoria_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mentoria = db.get(Mentoria, mentoria_id)
    if mentoria is None:
        raise HTTPException(status_code=404, detail="Mentoria no encontrada")
    _verificar_participante(mentoria, current_user)

    return (
        db.query(MentoriaMensaje)
        .filter(MentoriaMensaje.mentoria_id == mentoria_id)
        .order_by(MentoriaMensaje.fecha)
        .all()
    )


@router.post("/{mentoria_id}/mensajes", response_model=MensajeOut, status_code=201)
def enviar_mensaje(
    mentoria_id: uuid.UUID,
    payload: MensajeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    mentoria = db.get(Mentoria, mentoria_id)
    if mentoria is None:
        raise HTTPException(status_code=404, detail="Mentoria no encontrada")
    _verificar_participante(mentoria, current_user)
    if mentoria.estado != "aceptada":
        raise HTTPException(status_code=400, detail="La mentoria todavia no fue aceptada")

    mensaje = MentoriaMensaje(mentoria_id=mentoria_id, remitente_id=current_user.id, texto=payload.texto)
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)
    return mensaje


# ---------- Mentoria grupal ----------
def _grupal_out(db: Session, grupal: MentoriaGrupal, current_user: User) -> MentoriaGrupalOut:
    mentor = db.get(User, grupal.mentor_id)
    inscritos = (
        db.query(func.count(MentoriaGrupalInscripcion.id))
        .filter(MentoriaGrupalInscripcion.mentoria_grupal_id == grupal.id)
        .scalar()
        or 0
    )
    ya_inscrito = (
        db.query(MentoriaGrupalInscripcion)
        .filter(
            MentoriaGrupalInscripcion.mentoria_grupal_id == grupal.id,
            MentoriaGrupalInscripcion.joven_id == current_user.id,
        )
        .first()
        is not None
    )
    return MentoriaGrupalOut(
        id=grupal.id,
        mentor_id=grupal.mentor_id,
        mentor_nombre=mentor.nombre if mentor else "",
        titulo=grupal.titulo,
        descripcion=grupal.descripcion,
        cupo_maximo=grupal.cupo_maximo,
        inscritos=inscritos,
        meet_link=grupal.meet_link,
        fecha_hora=grupal.fecha_hora,
        ya_inscrito=ya_inscrito,
    )


@router.post("/grupales", response_model=MentoriaGrupalOut, status_code=201)
def crear_mentoria_grupal(
    payload: MentoriaGrupalIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("mentor")),
):
    grupal = MentoriaGrupal(mentor_id=current_user.id, **payload.model_dump())
    db.add(grupal)
    db.commit()
    db.refresh(grupal)
    return _grupal_out(db, grupal, current_user)


@router.get("/grupales", response_model=list[MentoriaGrupalOut])
def listar_mentorias_grupales(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las proximas mentorias grupales (futuras), para que los jovenes se unan."""
    grupales = (
        db.query(MentoriaGrupal)
        .filter(MentoriaGrupal.fecha_hora >= datetime.utcnow())
        .order_by(MentoriaGrupal.fecha_hora)
        .all()
    )
    return [_grupal_out(db, g, current_user) for g in grupales]


@router.get("/grupales/mias", response_model=list[MentoriaGrupalOut])
def mis_mentorias_grupales(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("mentor")),
):
    grupales = (
        db.query(MentoriaGrupal)
        .filter(MentoriaGrupal.mentor_id == current_user.id)
        .order_by(desc(MentoriaGrupal.fecha_hora))
        .all()
    )
    return [_grupal_out(db, g, current_user) for g in grupales]


@router.post("/grupales/{grupal_id}/unirse", response_model=MentoriaGrupalOut)
def unirse_mentoria_grupal(
    grupal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("joven")),
):
    grupal = db.get(MentoriaGrupal, grupal_id)
    if grupal is None:
        raise HTTPException(status_code=404, detail="Mentoria grupal no encontrada")

    ya_inscrito = (
        db.query(MentoriaGrupalInscripcion)
        .filter(
            MentoriaGrupalInscripcion.mentoria_grupal_id == grupal_id,
            MentoriaGrupalInscripcion.joven_id == current_user.id,
        )
        .first()
    )
    if ya_inscrito:
        raise HTTPException(status_code=400, detail="Ya te uniste a esta mentoria grupal")

    inscritos = (
        db.query(func.count(MentoriaGrupalInscripcion.id))
        .filter(MentoriaGrupalInscripcion.mentoria_grupal_id == grupal_id)
        .scalar()
        or 0
    )
    if inscritos >= grupal.cupo_maximo:
        raise HTTPException(status_code=400, detail="Ya no hay cupos disponibles")

    db.add(MentoriaGrupalInscripcion(mentoria_grupal_id=grupal_id, joven_id=current_user.id))
    db.commit()
    return _grupal_out(db, grupal, current_user)


@router.get("/grupales/{grupal_id}/inscritos", response_model=list[InscritoGrupalOut])
def listar_inscritos_grupal(
    grupal_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("mentor")),
):
    grupal = db.get(MentoriaGrupal, grupal_id)
    if grupal is None or grupal.mentor_id != current_user.id:
        raise HTTPException(status_code=404, detail="Mentoria grupal no encontrada")

    filas = (
        db.query(MentoriaGrupalInscripcion, User)
        .join(User, User.id == MentoriaGrupalInscripcion.joven_id)
        .filter(MentoriaGrupalInscripcion.mentoria_grupal_id == grupal_id)
        .order_by(MentoriaGrupalInscripcion.fecha_inscripcion)
        .all()
    )
    return [
        InscritoGrupalOut(
            joven_id=alumno.id,
            nombre=alumno.nombre,
            email=alumno.email,
            fecha_inscripcion=inscripcion.fecha_inscripcion,
        )
        for inscripcion, alumno in filas
    ]
