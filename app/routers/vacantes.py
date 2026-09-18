import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_role
from app.models import CVReview, ExperienciaLaboral, Postulacion, Profile, User, Vacante
from app.schemas import ExperienciaOut, PostulacionOut, PostulanteOut, VacanteIn, VacanteOut, VacanteUpdate
from app.services.cv_storage import ruta_cv

router = APIRouter(prefix="/vacantes", tags=["vacantes"])

# Empresas e instituciones/ONGs pueden publicar y gestionar vacantes.
PUBLICADORES = ("empresa", "institucion")


def _vacante_out(db: Session, vacante: Vacante) -> VacanteOut:
    total = db.query(func.count(Postulacion.id)).filter(Postulacion.vacante_id == vacante.id).scalar() or 0
    return VacanteOut(
        id=vacante.id,
        titulo=vacante.titulo,
        area=vacante.area,
        pais=vacante.pais,
        descripcion=vacante.descripcion,
        tipo_empleo=vacante.tipo_empleo,
        modalidad=vacante.modalidad,
        ciudad=vacante.ciudad,
        salario=vacante.salario,
        fecha_publicacion=vacante.fecha_publicacion,
        activa=vacante.activa,
        total_postulaciones=total,
    )


def _get_vacante_propia(db: Session, vacante_id: uuid.UUID, current_user: User) -> Vacante:
    vacante = db.get(Vacante, vacante_id)
    if vacante is None or vacante.empresa_id != current_user.id:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")
    return vacante


def _ultimo_cv_con_archivo(db: Session, user_id: uuid.UUID) -> CVReview | None:
    return (
        db.query(CVReview)
        .filter(CVReview.user_id == user_id, CVReview.archivo_path.is_not(None))
        .order_by(desc(CVReview.fecha))
        .first()
    )


@router.post("", response_model=VacanteOut, status_code=201)
def crear_vacante(
    payload: VacanteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PUBLICADORES)),
):
    vacante = Vacante(
        empresa_id=current_user.id,
        titulo=payload.titulo,
        area=payload.area,
        pais=payload.pais,
        descripcion=payload.descripcion,
        tipo_empleo=payload.tipo_empleo,
        modalidad=payload.modalidad,
        ciudad=payload.ciudad,
        salario=payload.salario,
    )
    db.add(vacante)
    db.commit()
    db.refresh(vacante)
    return _vacante_out(db, vacante)


@router.get("", response_model=list[VacanteOut])
def listar_vacantes(
    area: str | None = None,
    pais: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Vacante).filter(Vacante.activa.is_(True))
    if area:
        query = query.filter(Vacante.area == area)
    if pais:
        query = query.filter(Vacante.pais == pais)

    vacantes = query.order_by(desc(Vacante.fecha_publicacion)).all()
    return [_vacante_out(db, v) for v in vacantes]


@router.get("/mias", response_model=list[VacanteOut])
def mis_vacantes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PUBLICADORES)),
):
    vacantes = (
        db.query(Vacante)
        .filter(Vacante.empresa_id == current_user.id)
        .order_by(desc(Vacante.fecha_publicacion))
        .all()
    )
    return [_vacante_out(db, v) for v in vacantes]


@router.put("/{vacante_id}", response_model=VacanteOut)
def editar_vacante(
    vacante_id: uuid.UUID,
    payload: VacanteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PUBLICADORES)),
):
    vacante = _get_vacante_propia(db, vacante_id, current_user)

    datos = payload.model_dump(exclude_unset=True)
    for campo, valor in datos.items():
        setattr(vacante, campo, valor)

    db.commit()
    db.refresh(vacante)
    return _vacante_out(db, vacante)


@router.delete("/{vacante_id}", status_code=204)
def eliminar_vacante(
    vacante_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PUBLICADORES)),
):
    vacante = _get_vacante_propia(db, vacante_id, current_user)

    db.query(Postulacion).filter(Postulacion.vacante_id == vacante_id).delete()
    db.delete(vacante)
    db.commit()


@router.get("/{vacante_id}/postulantes", response_model=list[PostulanteOut])
def ver_postulantes(
    vacante_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PUBLICADORES)),
):
    _get_vacante_propia(db, vacante_id, current_user)

    filas = (
        db.query(Postulacion, User, Profile)
        .join(User, User.id == Postulacion.joven_id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .filter(Postulacion.vacante_id == vacante_id)
        .order_by(desc(Postulacion.fecha))
        .all()
    )

    postulantes = []
    for postulacion, user, profile in filas:
        experiencia = (
            db.query(ExperienciaLaboral)
            .filter(ExperienciaLaboral.user_id == user.id)
            .order_by(desc(ExperienciaLaboral.fecha_inicio))
            .all()
        )
        postulantes.append(
            PostulanteOut(
                postulacion_id=postulacion.id,
                joven_id=user.id,
                nombre=user.nombre,
                email=user.email,
                fecha_postulacion=postulacion.fecha,
                sector_interes=profile.sector_interes if profile else None,
                nivel_experiencia=profile.nivel_experiencia if profile else None,
                ruta_preferida=profile.ruta_preferida if profile else None,
                ciudad=profile.ciudad if profile else None,
                experiencia=[ExperienciaOut.model_validate(e) for e in experiencia],
                tiene_cv=_ultimo_cv_con_archivo(db, user.id) is not None,
            )
        )
    return postulantes


@router.get("/{vacante_id}/postulantes/{joven_id}/cv")
def descargar_cv_postulante(
    vacante_id: uuid.UUID,
    joven_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*PUBLICADORES)),
):
    """Descarga el CV (PDF/.docx) que subio un postulante, solo para la
    empresa/institucion dueña de la vacante a la que se postulo."""
    _get_vacante_propia(db, vacante_id, current_user)

    ya_postulo = (
        db.query(Postulacion)
        .filter(Postulacion.vacante_id == vacante_id, Postulacion.joven_id == joven_id)
        .first()
    )
    if ya_postulo is None:
        raise HTTPException(status_code=404, detail="Ese usuario no se postulo a esta vacante")

    review = _ultimo_cv_con_archivo(db, joven_id)
    if review is None or review.archivo_path is None:
        raise HTTPException(status_code=404, detail="Este postulante no tiene un CV en archivo")

    ruta = ruta_cv(review.archivo_path)
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="El archivo del CV ya no esta disponible")

    return FileResponse(
        ruta,
        media_type=review.archivo_mime or "application/octet-stream",
        filename=review.archivo_nombre or ruta.name,
    )


@router.get("/recomendadas", response_model=list[VacanteOut])
def vacantes_recomendadas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("joven", "mentor")),
):
    """Recomienda vacantes segun el area detectada en el CV (o el sector de interes
    declarado en el perfil, si todavia no se subio ningun CV)."""
    perfil = db.get(Profile, current_user.id)
    area = (perfil.area_formacion if perfil else None) or (perfil.sector_interes if perfil else None)
    if not area:
        raise HTTPException(
            status_code=400,
            detail="Completa tu perfil o sube tu CV para recibir recomendaciones",
        )

    vacantes = (
        db.query(Vacante)
        .filter(Vacante.activa.is_(True), func.lower(Vacante.area) == area.lower())
        .order_by(desc(Vacante.fecha_publicacion))
        .all()
    )
    return [_vacante_out(db, v) for v in vacantes]


@router.post("/{vacante_id}/postular", response_model=PostulacionOut, status_code=201)
def postular(
    vacante_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("joven")),
):
    vacante = db.get(Vacante, vacante_id)
    if vacante is None or not vacante.activa:
        raise HTTPException(status_code=404, detail="Vacante no encontrada")

    ya_postulo = (
        db.query(Postulacion)
        .filter(Postulacion.vacante_id == vacante_id, Postulacion.joven_id == current_user.id)
        .first()
    )
    if ya_postulo:
        raise HTTPException(status_code=400, detail="Ya te postulaste a esta vacante")

    postulacion = Postulacion(vacante_id=vacante_id, joven_id=current_user.id)
    db.add(postulacion)
    db.commit()
    db.refresh(postulacion)
    return postulacion
