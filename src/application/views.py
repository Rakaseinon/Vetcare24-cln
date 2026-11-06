"""Conversión de agregados a diccionarios serializables (respuestas de la API)."""
from __future__ import annotations

from typing import Any

from ..domain.agenda import Cita, MAQUINA_CITA
from ..domain.consulta import Consulta
from ..domain.hospitalizacion import Hospitalizacion, Jaula
from ..domain.orden_servicio import MAQUINA_ORDEN, OrdenServicio, ServicioCatalogo
from ..domain.paciente import Paciente
from ..domain.profilaxis import RegistroVacuna
from ..domain.tutor import Tutor


def tutor_view(t: Tutor) -> dict[str, Any]:
    return {"id": t.id, "nombre": t.nombre, "activo": t.activo, "es_preferente": t.es_preferente,
            "identificacion_oficial": t.identificacion_oficial, "telefono": t.telefono, "email": t.email,
            "ciudad": t.ciudad, "canal_preferido": t.canal_preferido}


def paciente_view(p: Paciente) -> dict[str, Any]:
    return {
        "id": p.id, "codigo_expediente": p.codigo_expediente, "nombre": p.nombre, "especie": p.especie,
        "raza": p.raza, "fecha_nacimiento": p.fecha_nacimiento, "tutor_id": p.tutor_id,
        "peso_kg": p.peso.valor_kg if p.peso else None, "microchip": p.microchip.codigo if p.microchip else None,
        "alerta_alergia": p.alerta_alergia, "alergias": [a.principio_activo for a in p.alergenos],
        "titularidad": [{"tutor_id": t.tutor_id, "desde": t.desde, "hasta": t.hasta} for t in p.titularidad],
        "triajes": [{"registrada_en": h.registrada_en, "peso_kg": h.peso.valor_kg, "temperatura_c": h.temperatura_c,
                     "motivo": h.motivo, "nivel": h.nivel.value} for h in p.triajes],
    }


def consulta_view(c: Consulta) -> dict[str, Any]:
    n = c.nota
    return {
        "id": c.id, "paciente_id": c.paciente_id, "cedula": c.cedula.numero if c.cedula else None,
        "abierta_en": c.abierta_en, "triage": c.triage.value if c.triage else None,
        "urgencia_descripcion": c.urgencia_descripcion,
        "nota": {"subjetivo": n.subjetivo, "objetivo": n.objetivo, "analisis": n.analisis, "plan": n.plan,
                 "estado": n.estado.value, "firmada_por": n.firmada_por.numero if n.firmada_por else None,
                 "firmada_en": n.firmada_en},
        "receta": [{"principio_activo": i.medicamento.principio_activo, "dosis_mg_por_kg": i.medicamento.dosis_mg_por_kg,
                    "dosis_calculada_mg": i.medicamento.dosis_calculada_mg, "via": i.medicamento.via,
                    "frecuencia_horas": i.medicamento.frecuencia_horas, "duracion_dias": i.medicamento.duracion_dias,
                    "justificacion_alergia": i.justificacion.texto if i.justificacion else None} for i in c.receta],
        "enmiendas": [{"id": e.id, "cedula": e.cedula.numero, "motivo": e.motivo, "detalle": e.detalle,
                       "fecha_hora": e.fecha_hora} for e in c.enmiendas],
        "estudios": [{"id": e.id, "tipo_estudio": e.tipo_estudio, "estado": e.estado, "solicitado_en": e.solicitado_en,
                      "resultado": ({"nombre_archivo": e.resultado.nombre_archivo, "sha256": e.resultado.sha256,
                                     "recibido_en": e.resultado.recibido_en} if e.resultado else None)}
                     for e in c.estudios],
    }


def cita_view(c: Cita) -> dict[str, Any]:
    return {"id": c.id, "paciente_id": c.paciente_id, "tipo": c.tipo.value, "sala": c.sala, "inicio": c.inicio,
            "fin": c.fin, "duracion_min": c.duracion_min, "estado": c.estado.value,
            "cancelada_en": c.cancelada_en, "cancelacion_tardia": c.cancelacion_tardia,
            "acciones_permitidas": MAQUINA_CITA.permitidas(c.estado)}


def vacuna_view(r: RegistroVacuna) -> dict[str, Any]:
    p = r.programacion
    return {"id": r.id, "paciente_id": r.paciente_id, "nombre_vacuna": r.nombre_vacuna, "lote": r.lote.codigo,
            "marca": r.marca.nombre, "fecha_aplicacion": r.fecha_aplicacion, "fecha_refuerzo": p.fecha_programada,
            "intervalo_dias": p.intervalo_dias, "recordatorio_enviado": p.notificado}


def jaula_view(j: Jaula) -> dict[str, Any]:
    return {"id": j.id, "tipo": j.tipo.value, "libre": j.libre, "hospitalizacion_id": j.hospitalizacion_id}


def hospitalizacion_view(h: Hospitalizacion, ahora=None) -> dict[str, Any]:
    return {
        "id": h.id, "paciente_id": h.paciente_id, "jaula_id": h.jaula_id, "plan_fluidoterapia": h.plan_fluidoterapia,
        "ingreso": h.ingreso, "estado": h.estado.value, "criticidad": h.criticidad.value,
        "alta_medica_firmada": h.alta_medica_firmada, "cuenta_liquidada": h.cuenta_liquidada,
        "apto_para_egreso": h.es_apto_para_egreso(), "egreso_en": h.egreso_en,
        "lectura_vencida": h.lectura_vencida(ahora) if ahora else None,
        "precuenta_total": h.precuenta_total,
        "consumos": [{"descripcion": c.descripcion, "monto": c.monto} for c in h.consumos],
        "bitacora": [{"registrada_en": l.registrada_en, "registrada_por": l.registrada_por,
                      "temperatura_c": l.constantes.temperatura_c, "frecuencia_cardiaca": l.constantes.frecuencia_cardiaca,
                      "frecuencia_respiratoria": l.constantes.frecuencia_respiratoria, "alertas": list(l.alertas)}
                     for l in h.bitacora],
    }


def servicio_view(s: ServicioCatalogo) -> dict[str, Any]:
    return {"id": s.id, "descripcion": s.descripcion, "precio": s.precio, "capacidad": s.capacidad,
            "habilitado": s.habilitado}


def orden_view(o: OrdenServicio, t: Tutor) -> dict[str, Any]:
    return {
        "id": o.id, "tutor_id": o.tutor_id, "estado": o.estado.value, "fecha_solicitud": o.fecha_solicitud,
        "referencia": o.referencia, "promocion_activa": o.promocion_activa, "autorizado": o.autorizado,
        "lineas": [{"servicio_id": l.servicio_id, "descripcion": l.descripcion, "precio": l.precio,
                    "cantidad": l.cantidad, "subtotal": l.subtotal} for l in o.lineas],
        "total": o.total(), "puede_procesarse": o.puede_procesarse(t),
        "motivos_no_procesable": o.motivos_no_procesable(t),
        "elegible_beneficio_referencia": o.elegible_beneficio_referencia(t),
        "acciones_permitidas": MAQUINA_ORDEN.permitidas(o.estado),
    }
