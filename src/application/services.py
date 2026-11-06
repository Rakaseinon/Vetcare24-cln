"""Servicios de aplicación (casos de uso). Solo ORQUESTAN: cargar agregado -> invocar dominio -> guardar -> commit.

Las reglas de negocio viven en src/domain (ADR-001, Riesgo 2: sin fugas de lógica a esta capa).
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from ..domain.agenda import ServicioAgenda, TipoServicioAgenda
from ..domain.common import (AlergiaBloqueoError, BusinessRuleViolation, EntityNotFound, ValidationDomainError,
                             new_id, utcnow)
from ..domain.consulta import CedulaProfesional, Consulta, JustificacionClinica, MedicamentoDosificado
from ..domain.hospitalizacion import ConstantesVitales
from ..domain.orden_servicio import EstadoOrden, OrdenServicio
from ..domain.paciente import Alergeno, NivelTriage, Paciente, Peso
from ..domain.profilaxis import EsquemaRefuerzo, IntervaloRefuerzo, RegistroVacuna
from ..domain.servicios import ServicioAltaHospitalaria, ServicioIngresoHospitalario, ServicioValidacionAlergias
from ..domain.specifications import RefuerzoPorNotificarSpec
from ..domain.tutor import Tutor
from . import views as v
from .ports import Clock, EventBus, Notificador, UowFactory


class _Servicio:
    def __init__(self, uow_factory: UowFactory, bus: EventBus, clock: Clock = utcnow) -> None:
        self.uow_factory, self.bus, self.clock = uow_factory, bus, clock

    def hoy(self) -> date:
        return self.clock().date()

    @staticmethod
    def _req(obj: Any, nombre: str, id_: str) -> Any:
        if obj is None:
            raise EntityNotFound(f"{nombre} '{id_}' no existe")
        return obj


# =========================================================================== Módulo 1: identidad
class PacienteService(_Servicio):
    def registrar_tutor(self, nombre: str, identificacion_oficial: str, telefono: str | None = None,
                        email: str | None = None, ciudad: str | None = None, canal_preferido: str = "CORREO") -> dict:
        with self.uow_factory() as uow:
            t = Tutor.registrar(new_id("TUT"), nombre, identificacion_oficial, telefono, email, ciudad, canal_preferido)
            uow.tutores.save(t)
            uow.commit()
            return v.tutor_view(t)

    def obtener_tutor(self, tutor_id: str) -> dict:
        with self.uow_factory() as uow:
            return v.tutor_view(self._req(uow.tutores.get(tutor_id), "Tutor", tutor_id))

    def registrar_mascota(self, tutor_id: str, nombre: str, especie: str, raza: str | None = None,
                          fecha_nacimiento: date | None = None, peso_kg: Decimal | None = None,
                          microchip: str | None = None) -> dict:
        """US01 — RegistrarMascota."""
        with self.uow_factory() as uow:
            tutor = self._req(uow.tutores.get(tutor_id), "Tutor", tutor_id)
            tutor.asegurar_activo("registrar mascotas")
            p = Paciente.registrar(new_id("PAC"), nombre, especie, tutor.id, uow.pacientes.siguiente_codigo(),
                                   self.hoy(), raza, fecha_nacimiento, peso_kg, microchip)
            if p.microchip and uow.pacientes.por_microchip(p.microchip.codigo):
                raise BusinessRuleViolation("Ya existe un paciente con ese microchip (registro duplicado)")
            uow.pacientes.save(p)
            uow.commit()
            return v.paciente_view(p)

    def obtener(self, paciente_id: str) -> dict:
        with self.uow_factory() as uow:
            return v.paciente_view(self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id))

    def buscar(self, q: str) -> list[dict]:
        """US12 — BuscarPacientesPredictivo: por nombre, teléfono del dueño, microchip o código."""
        with self.uow_factory() as uow:
            tutores = [t.id for t in uow.tutores.buscar(q)]
            return [v.paciente_view(p) for p in uow.pacientes.buscar(q, tutores)]

    def capturar_triaje(self, paciente_id: str, peso_kg: Decimal, temperatura_c: Decimal, motivo: str,
                        alergias: list[str] | None = None, nivel: str = "VERDE") -> dict:
        """US04 — CapturarTriajeInicial (delega peso y alérgenos al dominio)."""
        with self.uow_factory() as uow:
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            p.registrar_triaje(self.clock(), Peso(peso_kg), temperatura_c, motivo, alergias, NivelTriage(nivel))
            uow.pacientes.save(p)
            uow.commit()
            return v.paciente_view(p)

    def registrar_alergia(self, paciente_id: str, principio_activo: str) -> dict:
        with self.uow_factory() as uow:
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            p.registrar_alergia(Alergeno(principio_activo))
            uow.pacientes.save(p)
            uow.commit()
            return v.paciente_view(p)

    def transferir(self, paciente_id: str, nuevo_tutor_id: str) -> dict:
        """RN-05: cambia el tutor responsable conservando el historial clínico."""
        with self.uow_factory() as uow:
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            nuevo = self._req(uow.tutores.get(nuevo_tutor_id), "Tutor", nuevo_tutor_id)
            nuevo.asegurar_activo("recibir la titularidad de un paciente")
            p.transferir_a(nuevo.id, self.hoy())
            uow.pacientes.save(p)
            uow.commit()
            return v.paciente_view(p)

    def expediente(self, paciente_id: str) -> dict:
        """Expediente clínico digital (datos clínicos: solo roles médicos, RNF-03)."""
        with self.uow_factory() as uow:
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            return {"paciente": v.paciente_view(p),
                    "consultas": [v.consulta_view(c) for c in uow.consultas.de_paciente(paciente_id)],
                    "vacunas": [v.vacuna_view(r) for r in uow.vacunas.de_paciente(paciente_id)],
                    "hospitalizaciones": [v.hospitalizacion_view(h) for h in uow.hospitalizaciones.de_paciente(paciente_id)]}


# =========================================================================== Módulos 2-3: urgencias, consulta, receta
class ConsultaService(_Servicio):
    def admitir_urgencia(self, descripcion_trauma: str, paciente_id: str | None = None) -> dict:
        """US03 — ActivarAdmisionUrgencia (RN-02): pre-expediente temporal sin trámites administrativos."""
        with self.uow_factory() as uow:
            if paciente_id:
                self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            c = Consulta.admitir_urgencia(new_id("CON"), descripcion_trauma, self.clock(), paciente_id)
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def regularizar_urgencia(self, consulta_id: str, paciente_id: str) -> dict:
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            c.vincular_paciente(paciente_id)
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def abrir(self, paciente_id: str, cedula_veterinario: str) -> dict:
        with self.uow_factory() as uow:
            self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            c = Consulta.abrir(new_id("CON"), paciente_id, cedula_veterinario, self.clock())
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def obtener(self, consulta_id: str) -> dict:
        with self.uow_factory() as uow:
            return v.consulta_view(self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id))

    def redactar_nota(self, consulta_id: str, subjetivo: str, objetivo: str, analisis: str, plan: str) -> dict:
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            c.redactar_soap(subjetivo, objetivo, analisis, plan)
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def firmar_y_cerrar_nota(self, consulta_id: str, cedula: str) -> dict:
        """US05 — FirmarYCerrarNotaSOAP (RN-01)."""
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            c.firmar_y_cerrar(cedula, self.clock())
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def anexar_enmienda(self, consulta_id: str, cedula: str, motivo: str, detalle: str) -> dict:
        """US13 — AnexarNotaEnmienda (RN-01)."""
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            c.anexar_enmienda(cedula, motivo, detalle, self.clock())
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def solicitar_estudio(self, consulta_id: str, tipo_estudio: str) -> dict:
        """US14 — SolicitarEstudioLaboratorio."""
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            c.solicitar_estudio(tipo_estudio, self.clock())
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def adjuntar_resultado(self, consulta_id: str, estudio_id: str, nombre_archivo: str,
                           sha256: str | None = None) -> dict:
        """US14 — AdjuntarResultadoLaboratorio: asocia el archivo y emite el evento que alerta al médico tratante."""
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            c.adjuntar_resultado(estudio_id, nombre_archivo, sha256, self.clock())
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)

    def prescribir(self, consulta_id: str, principio_activo: str, dosis_mg_por_kg: Decimal, via: str,
                   frecuencia_horas: int, duracion_dias: int, justificacion: str | None = None,
                   cedula_justificante: str | None = None) -> dict:
        """US06 — PrescribirMedicamento (RN-04). Rollback + evento si hay alergia."""
        with self.uow_factory() as uow:
            c = self._req(uow.consultas.get(consulta_id), "Consulta", consulta_id)
            paciente_id = c.paciente_requerido()
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            med = MedicamentoDosificado.para_peso(principio_activo, dosis_mg_por_kg, via, frecuencia_horas,
                                                  duracion_dias, p.peso)
            just = (JustificacionClinica(justificacion, CedulaProfesional(cedula_justificante or ""))
                    if justificacion else None)
            try:
                ServicioValidacionAlergias().prescribir(c, p, med, just)
            except AlergiaBloqueoError as e:
                uow.rollback()
                self.bus.publish(e.event)  # BloqueoAlergiaDisparadoEvent (auditoría)
                raise
            uow.consultas.save(c)
            uow.commit()
            return v.consulta_view(c)


# =========================================================================== Módulo 4: profilaxis
class ProfilaxisService(_Servicio):
    def __init__(self, uow_factory: UowFactory, bus: EventBus, notificador: Notificador, clock: Clock = utcnow) -> None:
        super().__init__(uow_factory, bus, clock)
        self.notificador = notificador

    def registrar_vacuna(self, paciente_id: str, nombre_vacuna: str, lote: str | None, marca: str | None,
                         fecha_aplicacion: date | None = None, esquema: str | None = None) -> dict:
        """US07 — RegistrarAplicacionVacuna (RN-03) con cálculo automático del refuerzo."""
        with self.uow_factory() as uow:
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            hoy = self.hoy()
            intervalo = IntervaloRefuerzo.para(p.edad_meses(hoy), EsquemaRefuerzo(esquema) if esquema else None)
            r = RegistroVacuna.aplicar(new_id("VAC"), p.id, nombre_vacuna, lote, marca, fecha_aplicacion or hoy, hoy,
                                       intervalo)
            uow.vacunas.save(r)
            uow.commit()
            return v.vacuna_view(r)

    def procesar_recordatorios(self) -> dict:
        """US08 — ProcesarRecordatoriosPendientes: avisa 48 h antes por el canal preferido del tutor."""
        enviados = []
        with self.uow_factory() as uow:
            spec = RefuerzoPorNotificarSpec(self.hoy())
            for r in uow.vacunas.candidatos_recordatorio(self.hoy()):
                if not spec.is_satisfied_by(r):
                    continue
                p = uow.pacientes.get(r.paciente_id)
                t = uow.tutores.get(p.tutor_id) if p else None
                if not t:
                    continue
                canal = t.canal_preferido
                destino = (t.telefono if canal == "WHATSAPP" else t.email) or t.telefono or t.email or ""
                self.notificador.enviar(canal, destino, f"Refuerzo de {r.nombre_vacuna} para {p.nombre} el "
                                                        f"{r.programacion.fecha_programada.isoformat()}")
                r.marcar_notificado(canal, self.clock())
                uow.vacunas.save(r)
                enviados.append({"registro_id": r.id, "paciente_id": p.id, "canal": canal})
            uow.commit()
        return {"enviados": len(enviados), "detalle": enviados}


# =========================================================================== Módulo 5: hospitalización
class HospitalizacionService(_Servicio):
    def listar_jaulas(self, solo_libres: bool = False) -> list[dict]:
        with self.uow_factory() as uow:
            return [v.jaula_view(j) for j in uow.jaulas.listar(solo_libres)]

    def ingresar(self, paciente_id: str, jaula_id: str, plan_fluidoterapia: str, contagioso: bool = False,
                 critico: bool = False) -> dict:
        """US09 — IngresarAHospitalizacion."""
        with self.uow_factory() as uow:
            p = self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            j = self._req(uow.jaulas.get(jaula_id), "Jaula", jaula_id)
            if uow.hospitalizaciones.activa_de(paciente_id):
                raise BusinessRuleViolation("El paciente ya tiene una hospitalización activa")
            h = ServicioIngresoHospitalario().ingresar(p, j, plan_fluidoterapia, contagioso, self.clock(), critico)
            uow.hospitalizaciones.save(h)
            uow.jaulas.save(j)
            uow.commit()
            return v.hospitalizacion_view(h, self.clock())

    def obtener(self, hospitalizacion_id: str) -> dict:
        with self.uow_factory() as uow:
            h = self._req(uow.hospitalizaciones.get(hospitalizacion_id), "Hospitalización", hospitalizacion_id)
            return v.hospitalizacion_view(h, self.clock())

    def registrar_constantes(self, hospitalizacion_id: str, temperatura_c: Decimal, frecuencia_cardiaca: int,
                             frecuencia_respiratoria: int, registrada_por: str) -> dict:
        """US10 — RegistrarConstantesVitales (RF-06)."""
        with self.uow_factory() as uow:
            h = self._req(uow.hospitalizaciones.get(hospitalizacion_id), "Hospitalización", hospitalizacion_id)
            h.registrar_constantes(ConstantesVitales(temperatura_c, frecuencia_cardiaca, frecuencia_respiratoria),
                                   registrada_por, self.clock())
            uow.hospitalizaciones.save(h)
            uow.commit()
            return v.hospitalizacion_view(h, self.clock())

    def agregar_consumo(self, hospitalizacion_id: str, descripcion: str, monto: Decimal) -> dict:
        with self.uow_factory() as uow:
            h = self._req(uow.hospitalizaciones.get(hospitalizacion_id), "Hospitalización", hospitalizacion_id)
            h.agregar_consumo(descripcion, monto)
            uow.hospitalizaciones.save(h)
            uow.commit()
            return v.hospitalizacion_view(h, self.clock())

    def procesar_alta(self, hospitalizacion_id: str, accion_origen: str, cedula: str | None = None) -> dict:
        """US11 — ProcesarAltaHospitalaria (RN-06)."""
        with self.uow_factory() as uow:
            h = self._req(uow.hospitalizaciones.get(hospitalizacion_id), "Hospitalización", hospitalizacion_id)
            j = self._req(uow.jaulas.get(h.jaula_id), "Jaula", h.jaula_id)
            resultado = ServicioAltaHospitalaria().procesar(h, j, accion_origen, self.clock(), cedula)
            uow.hospitalizaciones.save(h)
            uow.jaulas.save(j)
            uow.commit()
            return {"resultado": resultado, "hospitalizacion": v.hospitalizacion_view(h, self.clock())}

    def lecturas_vencidas(self) -> list[dict]:
        """Hospitalizaciones activas sin constantes dentro de la ventana (4 h / 2 h)."""
        ahora = self.clock()
        with self.uow_factory() as uow:
            return [v.hospitalizacion_view(h, ahora) for h in uow.hospitalizaciones.activas()
                    if h.lectura_vencida(ahora)]


# =========================================================================== Servicios / órdenes de servicio (paquete de datos)
class OrdenService(_Servicio):
    def listar_servicios(self) -> list[dict]:
        with self.uow_factory() as uow:
            return [v.servicio_view(s) for s in uow.servicios.list_all()]

    def solicitar(self, tutor_id: str, lineas: list[tuple[str, int]], promocion_activa: bool = False,
                  autorizado: bool = True, referencia: str | None = None) -> dict:
        with self.uow_factory() as uow:
            tutor = self._req(uow.tutores.get(tutor_id), "Tutor", tutor_id)
            pedidos = [(self._req(uow.servicios.get(sid), "Servicio", sid), cant) for sid, cant in lineas]
            o = OrdenServicio.solicitar(new_id("ORD"), tutor, pedidos, self.hoy(), promocion_activa, autorizado,
                                        referencia)
            uow.ordenes.save(o)
            uow.commit()
            return v.orden_view(o, tutor)

    def obtener(self, orden_id: str) -> dict:
        with self.uow_factory() as uow:
            o = self._req(uow.ordenes.get(orden_id), "Orden", orden_id)
            return v.orden_view(o, self._req(uow.tutores.get(o.tutor_id), "Tutor", o.tutor_id))

    def transicionar(self, orden_id: str, accion: str) -> dict:
        with self.uow_factory() as uow:
            o = self._req(uow.ordenes.get(orden_id), "Orden", orden_id)
            t = self._req(uow.tutores.get(o.tutor_id), "Tutor", o.tutor_id)
            acciones = {"aprobar": lambda: o.aprobar(t), "completar": o.completar, "cancelar": o.cancelar}
            if accion not in acciones:
                raise BusinessRuleViolation(f"Acción desconocida: {accion}")
            acciones[accion]()
            uow.ordenes.save(o)
            uow.commit()
            return v.orden_view(o, t)


# =========================================================================== US15: reporte operativo
class ReporteService(_Servicio):
    def operativo(self, desde: date | None = None, hasta: date | None = None) -> dict:
        hasta = hasta or self.hoy()
        desde = desde or hasta - timedelta(days=7)
        if desde > hasta:
            raise BusinessRuleViolation("'desde' no puede ser posterior a 'hasta'")
        with self.uow_factory() as uow:
            jaulas = uow.jaulas.listar()
            ocupadas = sum(1 for j in jaulas if not j.libre)
            canceladas = uow.citas.canceladas_entre(desde, hasta)
            return {"desde": desde, "hasta": hasta, "jaulas_total": len(jaulas), "jaulas_ocupadas": ocupadas,
                    "tasa_ocupacion": round(ocupadas / len(jaulas), 4) if jaulas else 0.0,
                    "vacunas_aplicadas": uow.vacunas.aplicadas_entre(desde, hasta),
                    "refuerzos_pendientes": uow.vacunas.refuerzos_pendientes(self.hoy()),
                    "ordenes_canceladas": uow.ordenes.contar_por_estado(EstadoOrden.CANCELADA.value, desde, hasta),
                    "citas_canceladas": len(canceladas),
                    "citas_canceladas_tardias": sum(1 for c in canceladas if c.cancelacion_tardia)}


# =========================================================================== Módulo 2: agenda inteligente (US02)
class AgendaService(_Servicio):
    def agendar(self, paciente_id: str, tipo: str, inicio: Any, duracion_min: int | None = None) -> dict:
        """US02 — AgendarCita: bloquea la duración del servicio y asigna sala/quirófano libre."""
        try:
            tipo_servicio = TipoServicioAgenda(tipo)
        except ValueError:
            raise ValidationDomainError(
                f"Tipo de servicio desconocido '{tipo}'. Válidos: {', '.join(t.value for t in TipoServicioAgenda)}") from None
        with self.uow_factory() as uow:
            self._req(uow.pacientes.get(paciente_id), "Paciente", paciente_id)
            ini, fin = ServicioAgenda.ventana(tipo_servicio, inicio, duracion_min)
            existentes = uow.citas.activas_en(ini, fin)
            cita = ServicioAgenda().agendar(new_id("CIT"), paciente_id, tipo_servicio, ini, existentes,
                                            self.clock(), duracion_min)
            uow.citas.save(cita)
            uow.commit()
            return v.cita_view(cita)

    def obtener(self, cita_id: str) -> dict:
        with self.uow_factory() as uow:
            return v.cita_view(self._req(uow.citas.get(cita_id), "Cita", cita_id))

    def del_dia(self, dia: date) -> list[dict]:
        with self.uow_factory() as uow:
            return [v.cita_view(c) for c in uow.citas.del_dia(dia)]

    def cancelar(self, cita_id: str) -> dict:
        with self.uow_factory() as uow:
            c = self._req(uow.citas.get(cita_id), "Cita", cita_id)
            c.cancelar(self.clock())  # libera la sala: solo las PROGRAMADAS bloquean agenda
            uow.citas.save(c)
            uow.commit()
            return v.cita_view(c)
