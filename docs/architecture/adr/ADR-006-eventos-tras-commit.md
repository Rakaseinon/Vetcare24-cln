# ADR-006 — Los eventos de dominio se publican solo después del commit

- **Estatus:** Aceptado · **Fecha:** 2026-11-01

## Contexto
Los agregados generan hechos relevantes (paciente hospitalizado, resultado de laboratorio adjuntado, bloqueo por alergia). Si un suscriptor
reacciona *antes* de que la transacción termine, puede avisar al médico de un resultado que luego se revierte («evento fantasma»).

## Decisión
Los agregados registran eventos (`_record`); `SqlAlchemyUnitOfWork.commit()` persiste y **después** los publica en el `InMemoryEventBus`.
Si la transacción falla o se hace `rollback()`, ningún suscriptor ve eventos falsos. Excepción deliberada: `BloqueoAlergiaDisparadoEvent`
se publica tras el rollback porque su propósito es auditar el *intento* bloqueado.

## Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| Publicar dentro del agregado en el momento en que ocurre | Los suscriptores verían hechos que después se revierten |
| Outbox transaccional con broker (Kafka, RabbitMQ) | Infraestructura desproporcionada para un único proceso; el puerto `EventBus` permite añadirlo después |
| Sin eventos (llamadas directas entre servicios) | Acopla módulos: laboratorio tendría que conocer al sistema de alertas |

## Consecuencias
Suscriptor activo: alerta al médico tratante cuando llega un resultado de laboratorio (US14, `build_container`). El resto de los eventos
(bloqueos RN-04, altas, citas, recordatorios…) queda en `bus.history` para auditoría y para las pruebas. Un bus en memoria es suficiente para un solo proceso; para múltiples réplicas se cambiaría por un broker detrás del puerto `EventBus`.
(−) Si el proceso cae justo entre el commit y la publicación se pierde el aviso; un *outbox* lo resolvería y queda como mejora.
