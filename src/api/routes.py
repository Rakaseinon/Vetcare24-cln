"""Controllers REST. Sin lógica de negocio: validan el contrato, delegan en los servicios de aplicación."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from . import schemas as s
from .container import Container
from .security import CLINICOS, TODOS, requiere

def _err(descripcion: str, codigo: str, mensaje: str) -> dict:
    return {"model": s.ErrorOut, "description": descripcion,
            "content": {"application/json": {"example": {"codigo": codigo, "mensaje": mensaje}}}}


ERR = {400: _err("Dato inválido (el mensaje dice cuál)", "ValidationDomainError", "Se requiere al menos teléfono o correo de contacto"),
       404: _err("El id indicado no existe", "EntityNotFound", "Paciente 'PAC-000000000000' no existe"),
       409: _err("Se violó una regla de negocio o el estado no lo permite", "NotaInmutableError",
                 "RN-01: la nota/receta está firmada y congelada; solo se admite una Nota de Enmienda")}


def _c(request: Request) -> Container:
    return request.app.state.container


router = APIRouter()
_clin = [Depends(requiere(*CLINICOS))]
_ord = [Depends(requiere("RECEPCION", "VETERINARIO", "DIRECTOR"))]
_todos = [Depends(requiere(*TODOS))]


# ------------------------------------------------------------------ Tutores / pacientes (Módulo 1)
@router.post("/tutores", response_model=s.TutorOut, status_code=201, tags=["1 · Tutores y mascotas"], responses=ERR,
             dependencies=_todos)
def crear_tutor(body: s.TutorIn, c: Container = Depends(_c)):
    return c.pacientes.registrar_tutor(**body.model_dump())


@router.get("/tutores/{tutor_id}", response_model=s.TutorOut, tags=["1 · Tutores y mascotas"], responses=ERR, dependencies=_todos)
def obtener_tutor(tutor_id: str, c: Container = Depends(_c)):
    return c.pacientes.obtener_tutor(tutor_id)


@router.post("/pacientes", response_model=s.PacienteOut, status_code=201, tags=["1 · Tutores y mascotas"], responses=ERR,
             summary="US01 Registrar mascota", dependencies=_todos)
def registrar_mascota(body: s.MascotaIn, c: Container = Depends(_c)):
    return c.pacientes.registrar_mascota(**body.model_dump())


@router.get("/pacientes/buscar", response_model=list[s.PacienteOut], tags=["1 · Tutores y mascotas"],
            summary="US12 Búsqueda predictiva", dependencies=_todos)
def buscar_pacientes(q: str = Query(min_length=2), c: Container = Depends(_c)):
    return c.pacientes.buscar(q)


@router.get("/pacientes/{paciente_id}", response_model=s.PacienteOut, tags=["1 · Tutores y mascotas"], responses=ERR,
            dependencies=_todos)
def obtener_paciente(paciente_id: str, c: Container = Depends(_c)):
    return c.pacientes.obtener(paciente_id)


@router.get("/pacientes/{paciente_id}/expediente", tags=["3 · Consultas y expediente"], responses=ERR,
            summary="Expediente clínico (solo personal médico, RNF-03)", dependencies=_clin)
def expediente(paciente_id: str, c: Container = Depends(_c)):
    return c.pacientes.expediente(paciente_id)


@router.post("/pacientes/{paciente_id}/triaje", response_model=s.PacienteOut, tags=["2 · Triaje y urgencias"],
             responses=ERR, summary="US04 Capturar triaje inicial", dependencies=_todos)
def capturar_triaje(paciente_id: str, body: s.TriajeIn, c: Container = Depends(_c)):
    return c.pacientes.capturar_triaje(paciente_id, **body.model_dump())


@router.post("/pacientes/{paciente_id}/alergias", response_model=s.PacienteOut, status_code=201,
             tags=["2 · Triaje y urgencias"], responses=ERR,
             dependencies=[Depends(requiere("VETERINARIO", "ENFERMERIA", "DIRECTOR"))])
def registrar_alergia(paciente_id: str, body: s.AlergiaIn, c: Container = Depends(_c)):
    return c.pacientes.registrar_alergia(paciente_id, body.principio_activo)


@router.post("/pacientes/{paciente_id}/transferencia", response_model=s.PacienteOut, tags=["1 · Tutores y mascotas"],
             responses=ERR, summary="RN-05 Transferir titularidad",
             dependencies=[Depends(requiere("RECEPCION", "DIRECTOR"))])
def transferir(paciente_id: str, body: s.TransferenciaIn, c: Container = Depends(_c)):
    return c.pacientes.transferir(paciente_id, body.nuevo_tutor_id)


@router.post("/urgencias", response_model=s.ConsultaOut, status_code=201, tags=["2 · Triaje y urgencias"],
             responses=ERR, summary="US03 Admisión de emergencia (Código Rojo, RN-02)", dependencies=_todos)
def admitir_urgencia(body: s.UrgenciaIn, c: Container = Depends(_c)):
    return c.consultas.admitir_urgencia(body.descripcion_trauma, body.paciente_id)


@router.post("/urgencias/{consulta_id}/regularizar", response_model=s.ConsultaOut, tags=["2 · Triaje y urgencias"],
             responses=ERR, dependencies=_todos)
def regularizar_urgencia(consulta_id: str, paciente_id: str = Query(), c: Container = Depends(_c)):
    return c.consultas.regularizar_urgencia(consulta_id, paciente_id)


# ------------------------------------------------------------------ Consultas (Módulo 3)
@router.post("/consultas", response_model=s.ConsultaOut, status_code=201, tags=["3 · Consultas y expediente"],
             responses=ERR, dependencies=_clin)
def abrir_consulta(body: s.ConsultaIn, c: Container = Depends(_c)):
    return c.consultas.abrir(body.paciente_id, body.cedula_veterinario)


@router.get("/consultas/{consulta_id}", response_model=s.ConsultaOut, tags=["3 · Consultas y expediente"], responses=ERR,
            dependencies=_clin)
def obtener_consulta(consulta_id: str, c: Container = Depends(_c)):
    return c.consultas.obtener(consulta_id)


@router.put("/consultas/{consulta_id}/nota", response_model=s.ConsultaOut, tags=["3 · Consultas y expediente"],
            responses=ERR, summary="Redactar nota SOAP (409 si está firmada, RN-01)", dependencies=_clin)
def redactar_nota(consulta_id: str, body: s.NotaIn, c: Container = Depends(_c)):
    return c.consultas.redactar_nota(consulta_id, **body.model_dump())


@router.post("/consultas/{consulta_id}/nota/firmar", response_model=s.ConsultaOut, tags=["3 · Consultas y expediente"],
             responses=ERR, summary="US05 Firmar y cerrar nota (RN-01)", dependencies=_clin)
def firmar_nota(consulta_id: str, body: s.FirmaIn, c: Container = Depends(_c)):
    return c.consultas.firmar_y_cerrar_nota(consulta_id, body.cedula)


@router.post("/consultas/{consulta_id}/enmiendas", response_model=s.ConsultaOut, status_code=201,
             tags=["3 · Consultas y expediente"], responses=ERR, summary="US13 Anexar nota de enmienda",
             dependencies=_clin)
def anexar_enmienda(consulta_id: str, body: s.EnmiendaIn, c: Container = Depends(_c)):
    return c.consultas.anexar_enmienda(consulta_id, **body.model_dump())


@router.post("/consultas/{consulta_id}/recetas", response_model=s.ConsultaOut, status_code=201,
             tags=["3 · Consultas y expediente"], responses=ERR, summary="US06 Prescribir (bloqueo por alergia, RN-04)",
             dependencies=_clin)
def prescribir(consulta_id: str, body: s.RecetaIn, c: Container = Depends(_c)):
    return c.consultas.prescribir(consulta_id, **body.model_dump())


# ------------------------------------------------------------------ Laboratorio (US14)
@router.post("/consultas/{consulta_id}/laboratorio", response_model=s.ConsultaOut, status_code=201,
             tags=["3 · Consultas y expediente"], responses=ERR, summary="US14 Solicitar estudio de laboratorio",
             dependencies=_clin)
def solicitar_estudio(consulta_id: str, body: s.EstudioIn, c: Container = Depends(_c)):
    return c.consultas.solicitar_estudio(consulta_id, body.tipo_estudio)


@router.post("/consultas/{consulta_id}/laboratorio/{estudio_id}/resultado", response_model=s.ConsultaOut,
             status_code=201, tags=["3 · Consultas y expediente"], responses=ERR,
             summary="US14 Adjuntar resultado y alertar al médico tratante", dependencies=_clin)
def adjuntar_resultado(consulta_id: str, estudio_id: str, body: s.ResultadoLabIn, c: Container = Depends(_c)):
    return c.consultas.adjuntar_resultado(consulta_id, estudio_id, body.nombre_archivo, body.sha256)


# ------------------------------------------------------------------ Profilaxis (Módulo 4)
@router.post("/vacunas", response_model=s.VacunaOut, status_code=201, tags=["4 · Vacunas y recordatorios"], responses=ERR,
             summary="US07 Registrar vacuna (RN-03) y programar refuerzo",
             dependencies=[Depends(requiere("VETERINARIO", "ENFERMERIA", "DIRECTOR"))])
def registrar_vacuna(body: s.VacunaIn, c: Container = Depends(_c)):
    return c.profilaxis.registrar_vacuna(**body.model_dump())


@router.post("/recordatorios/procesar", tags=["4 · Vacunas y recordatorios"], summary="US08 Despachar recordatorios (48 h antes)",
             dependencies=[Depends(requiere("RECEPCION", "DIRECTOR"))])
def procesar_recordatorios(c: Container = Depends(_c)):
    return c.profilaxis.procesar_recordatorios()


# ------------------------------------------------------------------ Agenda inteligente (US02)
@router.post("/citas", response_model=s.CitaOut, status_code=201, tags=["5 · Citas"], responses=ERR,
             summary="US02 Agendar cita (bloqueo por servicio y asignación de sala)", dependencies=_ord)
def agendar_cita(body: s.CitaIn, c: Container = Depends(_c)):
    return c.agenda.agendar(body.paciente_id, body.tipo, body.inicio, body.duracion_min)


@router.get("/citas", response_model=list[s.CitaOut], tags=["5 · Citas"], summary="US02 Citas de un día",
            dependencies=_ord)
def citas_del_dia(dia: date = Query(description="YYYY-MM-DD (UTC)"), c: Container = Depends(_c)):
    return c.agenda.del_dia(dia)


@router.get("/citas/{cita_id}", response_model=s.CitaOut, tags=["5 · Citas"], responses=ERR, dependencies=_ord)
def obtener_cita(cita_id: str, c: Container = Depends(_c)):
    return c.agenda.obtener(cita_id)


@router.post("/citas/{cita_id}/cancelar", response_model=s.CitaOut, tags=["5 · Citas"], responses=ERR,
             summary="US02 Cancelar cita (libera la sala)", dependencies=_ord)
def cancelar_cita(cita_id: str, c: Container = Depends(_c)):
    return c.agenda.cancelar(cita_id)


# ------------------------------------------------------------------ Hospitalización (Módulo 5)
@router.get("/jaulas", response_model=list[s.JaulaOut], tags=["6 · Hospitalización"], dependencies=_todos)
def listar_jaulas(libres: bool = False, c: Container = Depends(_c)):
    return c.hospitalizacion.listar_jaulas(libres)


@router.post("/hospitalizaciones", response_model=s.HospitalizacionOut, status_code=201, tags=["6 · Hospitalización"],
             responses=ERR, summary="US09 Ingresar a hospitalización", dependencies=_clin)
def ingresar(body: s.HospitalizacionIn, c: Container = Depends(_c)):
    return c.hospitalizacion.ingresar(**body.model_dump())


@router.get("/hospitalizaciones/alertas/lecturas-vencidas", response_model=list[s.HospitalizacionOut],
            tags=["6 · Hospitalización"], summary="Pacientes sin constantes dentro de la ventana de 4 h / 2 h",
            dependencies=[Depends(requiere("ENFERMERIA", "VETERINARIO", "DIRECTOR"))])
def lecturas_vencidas(c: Container = Depends(_c)):
    return c.hospitalizacion.lecturas_vencidas()


@router.get("/hospitalizaciones/{hid}", response_model=s.HospitalizacionOut, tags=["6 · Hospitalización"],
            responses=ERR, dependencies=_todos)
def obtener_hospitalizacion(hid: str, c: Container = Depends(_c)):
    return c.hospitalizacion.obtener(hid)


@router.post("/hospitalizaciones/{hid}/constantes", response_model=s.HospitalizacionOut, status_code=201,
             tags=["6 · Hospitalización"], responses=ERR, summary="US10 Registrar constantes vitales",
             dependencies=[Depends(requiere("ENFERMERIA", "VETERINARIO", "DIRECTOR"))])
def registrar_constantes(hid: str, body: s.ConstantesIn, c: Container = Depends(_c)):
    return c.hospitalizacion.registrar_constantes(hid, **body.model_dump())


@router.post("/hospitalizaciones/{hid}/consumos", response_model=s.HospitalizacionOut, status_code=201,
             tags=["6 · Hospitalización"], responses=ERR, summary="Agregar consumo a la precuenta",
             dependencies=[Depends(requiere("ENFERMERIA", "VETERINARIO", "DIRECTOR"))])
def agregar_consumo(hid: str, body: s.ConsumoIn, c: Container = Depends(_c)):
    return c.hospitalizacion.agregar_consumo(hid, body.descripcion, body.monto)


@router.post("/hospitalizaciones/{hid}/alta-medica", response_model=s.AltaOut, tags=["6 · Hospitalización"],
             responses=ERR, summary="US11 / RN-06 paso 1: firma del veterinario",
             dependencies=[Depends(requiere("VETERINARIO", "DIRECTOR"))])
def firmar_alta(hid: str, body: s.FirmaIn, c: Container = Depends(_c)):
    return c.hospitalizacion.procesar_alta(hid, "FIRMAR_ALTA", body.cedula)


@router.post("/hospitalizaciones/{hid}/liquidacion", response_model=s.AltaOut, tags=["6 · Hospitalización"],
             responses=ERR, summary="US11 / RN-06 paso 2: liquidación en recepción",
             dependencies=[Depends(requiere("RECEPCION", "DIRECTOR"))])
def liquidar(hid: str, c: Container = Depends(_c)):
    return c.hospitalizacion.procesar_alta(hid, "LIQUIDAR_CUENTA")


# ------------------------------------------------------------------ Órdenes de servicio (paquete de datos VetCare 24)
@router.get("/servicios", response_model=list[s.ServicioOut], tags=["7 · Órdenes de servicio"], dependencies=_ord)
def listar_servicios(c: Container = Depends(_c)):
    return c.ordenes.listar_servicios()


@router.post("/ordenes", response_model=s.OrdenOut, status_code=201, tags=["7 · Órdenes de servicio"], responses=ERR,
             dependencies=_ord)
def solicitar_orden(body: s.OrdenIn, c: Container = Depends(_c)):
    return c.ordenes.solicitar(body.tutor_id, [(l.servicio_id, l.cantidad) for l in body.lineas],
                               body.promocion_activa, body.autorizado, body.referencia)


@router.get("/ordenes/{orden_id}", response_model=s.OrdenOut, tags=["7 · Órdenes de servicio"], responses=ERR,
            dependencies=_ord)
def obtener_orden(orden_id: str, c: Container = Depends(_c)):
    return c.ordenes.obtener(orden_id)


@router.post("/ordenes/{orden_id}/transiciones", response_model=s.OrdenOut, tags=["7 · Órdenes de servicio"],
             responses=ERR, summary="Máquina de estados: aprobar | completar | cancelar", dependencies=_ord)
def transicionar(orden_id: str, body: s.TransicionIn, c: Container = Depends(_c)):
    return c.ordenes.transicionar(orden_id, body.accion)


# ------------------------------------------------------------------ Reportes (US15)
@router.get("/reportes/operativo", response_model=s.ReporteOut, tags=["8 · Reportes"], responses=ERR,
            summary="US15 KPIs de ocupación e inmunizaciones", dependencies=[Depends(requiere("DIRECTOR"))])
def reporte(desde: date | None = None, hasta: date | None = None, c: Container = Depends(_c)):
    return c.reportes.operativo(desde, hasta)
