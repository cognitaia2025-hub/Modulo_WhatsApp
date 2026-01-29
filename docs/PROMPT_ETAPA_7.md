# ETAPA 7: HERRAMIENTAS MÉDICAS AVANZADAS

**Fecha de inicio:** 29 de Enero de 2026
**Duración estimada:** 5-6 días
**Prioridad:** 🟢 BAJA (después de sistema básico funcionando)

---

## 🎯 Objetivo General

Implementar **6 herramientas médicas avanzadas** para gestión completa del sistema médico, incluyendo:
- Registro de consultas médicas con embeddings
- Consulta de historial con búsqueda semántica
- Actualización de disponibilidad de doctores
- Generación de reportes de actividad
- Estadísticas y analytics de consultas
- Búsqueda de citas por periodo

---

## 📋 Componentes a Implementar

### 🔧 Herramientas Médicas Avanzadas (6 nuevas)

**Archivo principal:** `src/medical/advanced_tools.py`

#### T7.1 - registrar_consulta()
**Tipo:** Herramienta médica
**Función:** Registrar resultados de consulta en historial médico
**Incluye:** Generación de embeddings para búsqueda semántica

#### T7.2 - consultar_historial_paciente()
**Tipo:** Herramienta médica
**Función:** Consultar historial completo o búsqueda semántica específica
**Incluye:** Búsqueda por similitud de embeddings

#### T7.3 - actualizar_disponibilidad_doctor()
**Tipo:** Herramienta médica
**Función:** Permitir a doctores modificar sus horarios disponibles
**Incluye:** Validación de conflictos con citas existentes

#### T7.4 - generar_reporte_doctor()
**Tipo:** Herramienta de reportes
**Función:** Generar reportes de actividad (diario, mensual, ingresos)
**Incluye:** Formateo de datos en texto legible

#### T7.5 - obtener_estadisticas_consultas()
**Tipo:** Herramienta de analytics
**Función:** Obtener métricas de productividad (tasa asistencia, pacientes únicos)
**Incluye:** Cálculos de porcentajes y agregaciones

#### T7.6 - buscar_citas_por_periodo()
**Tipo:** Herramienta de búsqueda
**Función:** Buscar citas médicas en rango de fechas
**Incluye:** Filtros por doctor, paciente, estado

---

## 📝 Especificaciones Técnicas Detalladas

### T7.1 - Registrar Consulta Médica

```python
# Archivo: src/medical/advanced_tools.py

from langchain_core.tools import tool
from typing import List, Dict, Optional
from datetime import date
from src.database.db_config import get_db_session
from src.medical.models import CitasMedicas, HistorialesMedicos, Pacientes
from src.medical.crud import get_doctor_by_phone
from src.utilities import generate_embedding

@tool
def registrar_consulta(
    doctor_phone: str,
    cita_id: int,
    diagnostico_principal: str,
    sintomas: str,
    tratamiento: str,
    medicamentos: List[Dict],  # [{"nombre": "...", "dosis": "...", "duracion": "..."}]
    proxima_cita: Optional[str] = None
) -> str:
    """
    Registra los resultados de una consulta médica en el historial del paciente.

    Args:
        doctor_phone: Teléfono del doctor (formato: +526641234567)
        cita_id: ID de la cita médica completada
        diagnostico_principal: Diagnóstico principal de la consulta
        sintomas: Descripción de síntomas presentados
        tratamiento: Tratamiento prescrito
        medicamentos: Lista de medicamentos recetados
        proxima_cita: Fecha/hora sugerida para próxima cita (opcional)

    Returns:
        Mensaje de confirmación o error
    """
    try:
        with get_db_session() as db:
            # 1. Validar que el doctor existe
            doctor = get_doctor_by_phone(doctor_phone)
            if not doctor:
                return f"❌ Error: Doctor con teléfono {doctor_phone} no encontrado"

            # 2. Obtener la cita
            cita = db.query(CitasMedicas).filter(
                CitasMedicas.id == cita_id
            ).first()

            if not cita:
                return f"❌ Error: Cita {cita_id} no encontrada"

            # 3. Validar que la cita pertenece al doctor
            if cita.doctor_id != doctor.id:
                return f"❌ Error: La cita {cita_id} no pertenece al doctor {doctor.nombre_completo}"

            # 4. Actualizar estado de la cita
            cita.estado = 'completada'
            cita.diagnostico = diagnostico_principal
            cita.tratamiento_prescrito = tratamiento

            # 5. Crear registro en historial médico
            historial = HistorialesMedicos(
                paciente_id=cita.paciente_id,
                cita_id=cita_id,
                fecha_consulta=cita.fecha_hora_inicio.date(),
                diagnostico_principal=diagnostico_principal,
                sintomas=sintomas,
                tratamiento_prescrito=tratamiento,
                medicamentos=medicamentos  # JSON
            )

            # 6. Generar embedding para búsqueda semántica
            texto_para_embedding = f"{diagnostico_principal} {sintomas} {tratamiento}"
            historial.embedding = generate_embedding(texto_para_embedding)

            db.add(historial)
            db.commit()
            db.refresh(historial)

            # 7. Formatear respuesta
            meds_str = "\n".join([
                f"  • {m['nombre']} - {m.get('dosis', 'N/A')} - {m.get('duracion', 'N/A')}"
                for m in medicamentos
            ])

            respuesta = f"""✅ Consulta registrada exitosamente

📋 **Historial ID:** {historial.id}
👤 **Paciente:** {cita.paciente.nombre_completo}
🗓️ **Fecha:** {cita.fecha_hora_inicio.strftime('%d/%m/%Y')}

📝 **Diagnóstico:** {diagnostico_principal}
💊 **Medicamentos:**
{meds_str}"""

            if proxima_cita:
                respuesta += f"\n\n📅 **Próxima cita sugerida:** {proxima_cita}"

            return respuesta

    except Exception as e:
        return f"❌ Error registrando consulta: {str(e)}"
```

---

### T7.2 - Consultar Historial Médico

```python
@tool
def consultar_historial_paciente(
    doctor_phone: str,
    paciente_id: int,
    busqueda: Optional[str] = None,
    limite: int = 10
) -> str:
    """
    Consulta el historial médico de un paciente con búsqueda semántica opcional.

    Args:
        doctor_phone: Teléfono del doctor
        paciente_id: ID del paciente
        busqueda: Texto de búsqueda semántica (ej: "diabetes", "dolor de cabeza")
        limite: Número máximo de registros a retornar

    Returns:
        Historial médico formateado o mensaje de error
    """
    try:
        with get_db_session() as db:
            # 1. Validar doctor
            doctor = get_doctor_by_phone(doctor_phone)
            if not doctor:
                return f"❌ Error: Doctor no encontrado"

            # 2. Validar paciente
            paciente = db.query(Pacientes).filter(Pacientes.id == paciente_id).first()
            if not paciente:
                return f"❌ Error: Paciente {paciente_id} no encontrado"

            # 3. Buscar historial
            if busqueda:
                # Búsqueda semántica con embeddings
                embedding_query = generate_embedding(busqueda)

                historiales = db.query(HistorialesMedicos).filter(
                    HistorialesMedicos.paciente_id == paciente_id
                ).order_by(
                    HistorialesMedicos.embedding.cosine_distance(embedding_query)
                ).limit(limite).all()

                titulo = f"🔍 Búsqueda: '{busqueda}'"
            else:
                # Historial completo ordenado por fecha
                historiales = db.query(HistorialesMedicos).filter(
                    HistorialesMedicos.paciente_id == paciente_id
                ).order_by(
                    HistorialesMedicos.fecha_consulta.desc()
                ).limit(limite).all()

                titulo = "📋 Historial Completo"

            if not historiales:
                return f"📋 No se encontraron registros para el paciente {paciente.nombre_completo}"

            # 4. Formatear respuesta
            respuesta = f"""{titulo}
👤 **Paciente:** {paciente.nombre_completo}
📊 **Total de registros:** {len(historiales)}

---
"""

            for h in historiales:
                meds = h.medicamentos or []
                meds_str = ", ".join([m.get('nombre', 'N/A') for m in meds]) if meds else "Ninguno"

                respuesta += f"""
📅 **{h.fecha_consulta.strftime('%d/%m/%Y')}**
   🏥 Diagnóstico: {h.diagnostico_principal}
   💊 Medicamentos: {meds_str}
   📝 Tratamiento: {h.tratamiento_prescrito[:100]}...

"""

            return respuesta

    except Exception as e:
        return f"❌ Error consultando historial: {str(e)}"
```

---

### T7.3 - Actualizar Disponibilidad Doctor

```python
@tool
def actualizar_disponibilidad_doctor(
    doctor_phone: str,
    fecha: str,  # YYYY-MM-DD
    hora_inicio: str,  # HH:MM
    hora_fin: str,  # HH:MM
    disponible: bool
) -> str:
    """
    Actualiza la disponibilidad de un doctor para una fecha/hora específica.

    Args:
        doctor_phone: Teléfono del doctor
        fecha: Fecha en formato YYYY-MM-DD
        hora_inicio: Hora de inicio en formato HH:MM
        hora_fin: Hora de fin en formato HH:MM
        disponible: True para marcar disponible, False para bloquear

    Returns:
        Mensaje de confirmación o error
    """
    try:
        from datetime import datetime, timedelta

        with get_db_session() as db:
            # 1. Validar doctor
            doctor = get_doctor_by_phone(doctor_phone)
            if not doctor:
                return f"❌ Error: Doctor no encontrado"

            # 2. Parsear fecha y horas
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            inicio_obj = datetime.strptime(f"{fecha} {hora_inicio}", "%Y-%m-%d %H:%M")
            fin_obj = datetime.strptime(f"{fecha} {hora_fin}", "%Y-%m-%d %H:%M")

            # 3. Si se está bloqueando, verificar citas existentes
            if not disponible:
                citas_conflicto = db.query(CitasMedicas).filter(
                    CitasMedicas.doctor_id == doctor.id,
                    CitasMedicas.fecha_hora_inicio >= inicio_obj,
                    CitasMedicas.fecha_hora_fin <= fin_obj,
                    CitasMedicas.estado.in_(['programada', 'confirmada'])
                ).all()

                if citas_conflicto:
                    citas_str = "\n".join([
                        f"  • {c.fecha_hora_inicio.strftime('%H:%M')} - {c.paciente.nombre_completo}"
                        for c in citas_conflicto
                    ])
                    return f"""⚠️ No se puede bloquear este horario

🚫 Hay {len(citas_conflicto)} cita(s) programada(s):
{citas_str}

💡 Cancela o reprograma estas citas primero."""

            # 4. Actualizar disponibilidad en BD
            from src.medical.models import DisponibilidadMedica

            disponibilidad = db.query(DisponibilidadMedica).filter(
                DisponibilidadMedica.doctor_id == doctor.id,
                DisponibilidadMedica.fecha == fecha_obj
            ).first()

            if not disponibilidad:
                # Crear nuevo registro
                disponibilidad = DisponibilidadMedica(
                    doctor_id=doctor.id,
                    dia_semana=fecha_obj.strftime('%A'),
                    fecha=fecha_obj,
                    hora_inicio=inicio_obj.time(),
                    hora_fin=fin_obj.time(),
                    disponible=disponible
                )
                db.add(disponibilidad)
            else:
                # Actualizar existente
                disponibilidad.hora_inicio = inicio_obj.time()
                disponibilidad.hora_fin = fin_obj.time()
                disponibilidad.disponible = disponible

            db.commit()

            estado_str = "✅ DISPONIBLE" if disponible else "🚫 BLOQUEADO"

            return f"""{estado_str} - Disponibilidad actualizada

👨‍⚕️ **Doctor:** {doctor.nombre_completo}
📅 **Fecha:** {fecha_obj.strftime('%d/%m/%Y (%A)')}
🕐 **Horario:** {hora_inicio} - {hora_fin}"""

    except Exception as e:
        return f"❌ Error actualizando disponibilidad: {str(e)}"
```

---

### T7.4 - Generar Reporte de Actividad

```python
# Archivo: src/medical/reports.py

from langchain_core.tools import tool
from datetime import date, datetime, timedelta
from sqlalchemy import func
from src.database.db_config import get_db_session
from src.medical.models import CitasMedicas
from src.medical.crud import get_doctor_by_phone

@tool
def generar_reporte_doctor(
    doctor_phone: str,
    tipo_reporte: str,  # 'citas_dia', 'citas_mes', 'ingresos'
    fecha_inicio: Optional[str] = None,  # YYYY-MM-DD
    fecha_fin: Optional[str] = None  # YYYY-MM-DD
) -> str:
    """
    Genera reportes de actividad médica del doctor.

    Args:
        doctor_phone: Teléfono del doctor
        tipo_reporte: Tipo de reporte ('citas_dia', 'citas_mes', 'ingresos')
        fecha_inicio: Fecha inicial (opcional, default: hoy o inicio del mes)
        fecha_fin: Fecha final (opcional, default: hoy o fin del mes)

    Returns:
        Reporte formateado en texto
    """
    try:
        with get_db_session() as db:
            # 1. Validar doctor
            doctor = get_doctor_by_phone(doctor_phone)
            if not doctor:
                return f"❌ Error: Doctor no encontrado"

            # 2. Determinar rango de fechas según tipo
            if tipo_reporte == 'citas_dia':
                fecha = date.today() if not fecha_inicio else datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                return _reporte_citas_dia(db, doctor, fecha)

            elif tipo_reporte == 'citas_mes':
                if not fecha_inicio:
                    fecha_inicio = date.today().replace(day=1)
                else:
                    fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()

                if not fecha_fin:
                    # Último día del mes
                    next_month = fecha_inicio.replace(day=28) + timedelta(days=4)
                    fecha_fin = next_month - timedelta(days=next_month.day)
                else:
                    fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

                return _reporte_citas_mes(db, doctor, fecha_inicio, fecha_fin)

            elif tipo_reporte == 'ingresos':
                if not fecha_inicio or not fecha_fin:
                    return "❌ Error: Para reporte de ingresos debes especificar fecha_inicio y fecha_fin"

                fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

                return _reporte_ingresos(db, doctor, fecha_inicio, fecha_fin)
            else:
                return f"❌ Error: Tipo de reporte '{tipo_reporte}' no válido. Usa: citas_dia, citas_mes, ingresos"

    except Exception as e:
        return f"❌ Error generando reporte: {str(e)}"


def _reporte_citas_dia(db, doctor, fecha: date) -> str:
    """Reporte de citas del día"""
    citas = db.query(CitasMedicas).filter(
        CitasMedicas.doctor_id == doctor.id,
        func.date(CitasMedicas.fecha_hora_inicio) == fecha
    ).order_by(CitasMedicas.fecha_hora_inicio).all()

    completadas = sum(1 for c in citas if c.estado == 'completada')
    pendientes = sum(1 for c in citas if c.estado in ['programada', 'confirmada'])
    canceladas = sum(1 for c in citas if c.estado == 'cancelada')
    no_asistieron = sum(1 for c in citas if c.estado == 'no_asistio')

    # Formatear lista de citas
    citas_str = ""
    for c in citas:
        emoji_estado = {
            'completada': '✅',
            'programada': '📅',
            'confirmada': '✓',
            'cancelada': '❌',
            'no_asistio': '⭕'
        }.get(c.estado, '•')

        citas_str += f"""
{emoji_estado} {c.fecha_hora_inicio.strftime('%H:%M')} - {c.paciente.nombre_completo}
   {c.motivo_consulta}"""

    return f"""📊 **REPORTE DEL DÍA**

👨‍⚕️ Dr. {doctor.nombre_completo}
📅 {fecha.strftime('%A %d de %B, %Y')}

📈 **Resumen:**
   Total de citas: {len(citas)}
   ✅ Completadas: {completadas}
   ⏳ Pendientes: {pendientes}
   ❌ Canceladas: {canceladas}
   ⭕ No asistieron: {no_asistieron}

📋 **Detalle de citas:**{citas_str if citas else "\n   (Sin citas programadas)"}"""


def _reporte_citas_mes(db, doctor, fecha_inicio: date, fecha_fin: date) -> str:
    """Reporte de citas del mes"""
    citas = db.query(CitasMedicas).filter(
        CitasMedicas.doctor_id == doctor.id,
        func.date(CitasMedicas.fecha_hora_inicio) >= fecha_inicio,
        func.date(CitasMedicas.fecha_hora_inicio) <= fecha_fin
    ).all()

    completadas = sum(1 for c in citas if c.estado == 'completada')
    canceladas = sum(1 for c in citas if c.estado == 'cancelada')
    no_asistieron = sum(1 for c in citas if c.estado == 'no_asistio')

    # Pacientes únicos
    pacientes_unicos = len(set(c.paciente_id for c in citas))

    # Tasa de asistencia
    tasa_asistencia = (completadas / len(citas) * 100) if len(citas) > 0 else 0

    return f"""📊 **REPORTE MENSUAL**

👨‍⚕️ Dr. {doctor.nombre_completo}
📅 Del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}

📈 **Estadísticas:**
   Total de citas: {len(citas)}
   ✅ Completadas: {completadas}
   ❌ Canceladas: {canceladas}
   ⭕ No asistieron: {no_asistieron}

   📊 Tasa de asistencia: {tasa_asistencia:.1f}%
   👥 Pacientes únicos: {pacientes_unicos}"""


def _reporte_ingresos(db, doctor, fecha_inicio: date, fecha_fin: date) -> str:
    """Reporte de ingresos (requiere campo 'costo' en citas_medicas)"""
    citas_completadas = db.query(CitasMedicas).filter(
        CitasMedicas.doctor_id == doctor.id,
        func.date(CitasMedicas.fecha_hora_inicio) >= fecha_inicio,
        func.date(CitasMedicas.fecha_hora_inicio) <= fecha_fin,
        CitasMedicas.estado == 'completada'
    ).all()

    # Suma de ingresos (asumiendo que existe campo 'costo' en CitasMedicas)
    ingresos_total = sum(c.costo if hasattr(c, 'costo') and c.costo else 0 for c in citas_completadas)

    return f"""💰 **REPORTE DE INGRESOS**

👨‍⚕️ Dr. {doctor.nombre_completo}
📅 Del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}

💵 **Ingresos:**
   Consultas completadas: {len(citas_completadas)}
   Ingreso total: ${ingresos_total:,.2f} MXN
   Promedio por consulta: ${(ingresos_total / len(citas_completadas)):.2f} MXN

⚠️ Nota: Este reporte requiere que las citas tengan el campo 'costo' registrado."""
```

---

### T7.5 - Obtener Estadísticas de Consultas

```python
# Archivo: src/medical/analytics.py

from langchain_core.tools import tool
from datetime import datetime, timedelta
from src.database.db_config import get_db_session
from src.medical.models import CitasMedicas, Pacientes
from src.medical.crud import get_doctor_by_phone

@tool
def obtener_estadisticas_consultas(
    doctor_phone: str,
    periodo: str = "mes"  # 'dia', 'semana', 'mes'
) -> str:
    """
    Obtiene estadísticas de productividad del doctor.

    Args:
        doctor_phone: Teléfono del doctor
        periodo: Periodo a analizar ('dia', 'semana', 'mes')

    Returns:
        Estadísticas formateadas
    """
    try:
        with get_db_session() as db:
            # 1. Validar doctor
            doctor = get_doctor_by_phone(doctor_phone)
            if not doctor:
                return f"❌ Error: Doctor no encontrado"

            # 2. Calcular rango de fechas
            ahora = datetime.now()

            if periodo == 'dia':
                inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
                fin = ahora
                titulo = "HOY"
            elif periodo == 'semana':
                inicio = ahora - timedelta(days=7)
                fin = ahora
                titulo = "ÚLTIMOS 7 DÍAS"
            elif periodo == 'mes':
                inicio = ahora - timedelta(days=30)
                fin = ahora
                titulo = "ÚLTIMOS 30 DÍAS"
            else:
                return f"❌ Error: Periodo '{periodo}' no válido. Usa: dia, semana, mes"

            # 3. Consultar citas
            total_citas = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor.id,
                CitasMedicas.fecha_hora_inicio >= inicio,
                CitasMedicas.fecha_hora_inicio <= fin
            ).count()

            citas_completadas = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor.id,
                CitasMedicas.fecha_hora_inicio >= inicio,
                CitasMedicas.fecha_hora_inicio <= fin,
                CitasMedicas.estado == 'completada'
            ).count()

            no_asistieron = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor.id,
                CitasMedicas.fecha_hora_inicio >= inicio,
                CitasMedicas.fecha_hora_inicio <= fin,
                CitasMedicas.estado == 'no_asistio'
            ).count()

            canceladas = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor.id,
                CitasMedicas.fecha_hora_inicio >= inicio,
                CitasMedicas.fecha_hora_inicio <= fin,
                CitasMedicas.estado == 'cancelada'
            ).count()

            # 4. Calcular métricas
            tasa_asistencia = (citas_completadas / total_citas * 100) if total_citas > 0 else 0

            # Pacientes únicos
            citas_periodo = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor.id,
                CitasMedicas.fecha_hora_inicio >= inicio,
                CitasMedicas.fecha_hora_inicio <= fin
            ).all()

            pacientes_unicos = len(set(c.paciente_id for c in citas_periodo))

            # Pacientes recurrentes (más de 1 cita)
            from collections import Counter
            contador_pacientes = Counter(c.paciente_id for c in citas_periodo)
            pacientes_recurrentes = sum(1 for count in contador_pacientes.values() if count > 1)

            return f"""📊 **ESTADÍSTICAS - {titulo}**

👨‍⚕️ Dr. {doctor.nombre_completo}
📅 Del {inicio.strftime('%d/%m/%Y')} al {fin.strftime('%d/%m/%Y')}

📈 **Citas:**
   Total: {total_citas}
   ✅ Completadas: {citas_completadas}
   ❌ Canceladas: {canceladas}
   ⭕ No asistieron: {no_asistieron}

📊 **Métricas:**
   Tasa de asistencia: {tasa_asistencia:.1f}%
   Tasa de cancelación: {(canceladas / total_citas * 100):.1f}% si total_citas > 0 else 0

👥 **Pacientes:**
   Pacientes únicos: {pacientes_unicos}
   Pacientes recurrentes: {pacientes_recurrentes}
   Promedio citas por paciente: {(total_citas / pacientes_unicos):.1f} si pacientes_unicos > 0 else 0"""

    except Exception as e:
        return f"❌ Error obteniendo estadísticas: {str(e)}"
```

---

### T7.6 - Buscar Citas por Periodo

```python
@tool
def buscar_citas_por_periodo(
    doctor_phone: str,
    fecha_inicio: str,  # YYYY-MM-DD
    fecha_fin: str,  # YYYY-MM-DD
    estado: Optional[str] = None,  # 'programada', 'completada', etc.
    paciente_id: Optional[int] = None
) -> str:
    """
    Busca citas médicas en un rango de fechas con filtros opcionales.

    Args:
        doctor_phone: Teléfono del doctor
        fecha_inicio: Fecha inicial (YYYY-MM-DD)
        fecha_fin: Fecha final (YYYY-MM-DD)
        estado: Filtro de estado (opcional)
        paciente_id: Filtro por paciente (opcional)

    Returns:
        Lista de citas formateada
    """
    try:
        from datetime import datetime

        with get_db_session() as db:
            # 1. Validar doctor
            doctor = get_doctor_by_phone(doctor_phone)
            if not doctor:
                return f"❌ Error: Doctor no encontrado"

            # 2. Parsear fechas
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

            # 3. Construir query base
            query = db.query(CitasMedicas).filter(
                CitasMedicas.doctor_id == doctor.id,
                CitasMedicas.fecha_hora_inicio >= inicio,
                CitasMedicas.fecha_hora_inicio <= fin
            )

            # 4. Aplicar filtros opcionales
            if estado:
                query = query.filter(CitasMedicas.estado == estado)

            if paciente_id:
                query = query.filter(CitasMedicas.paciente_id == paciente_id)

            # 5. Ejecutar query
            citas = query.order_by(CitasMedicas.fecha_hora_inicio).all()

            if not citas:
                filtros_str = f" (Estado: {estado})" if estado else ""
                filtros_str += f" (Paciente ID: {paciente_id})" if paciente_id else ""
                return f"📋 No se encontraron citas del {fecha_inicio} al {fecha_fin}{filtros_str}"

            # 6. Formatear respuesta
            titulo = f"📋 **CITAS DEL {inicio.strftime('%d/%m/%Y')} AL {fin.strftime('%d/%m/%Y')}**"

            if estado:
                titulo += f"\n🔍 Filtro: Estado = {estado}"
            if paciente_id:
                titulo += f"\n🔍 Filtro: Paciente ID = {paciente_id}"

            respuesta = f"""{titulo}

👨‍⚕️ Dr. {doctor.nombre_completo}
📊 Total: {len(citas)} cita(s)

---
"""

            for c in citas:
                emoji_estado = {
                    'completada': '✅',
                    'programada': '📅',
                    'confirmada': '✓',
                    'cancelada': '❌',
                    'no_asistio': '⭕'
                }.get(c.estado, '•')

                respuesta += f"""
{emoji_estado} **{c.fecha_hora_inicio.strftime('%d/%m/%Y %H:%M')}**
   👤 {c.paciente.nombre_completo}
   📝 {c.motivo_consulta}
   📊 Estado: {c.estado}
"""

            return respuesta

    except Exception as e:
        return f"❌ Error buscando citas: {str(e)}"
```

---

### 🗄️ Validar Embeddings en historiales_medicos

```sql
-- Verificar que la columna embedding existe
-- Ya fue creada en ETAPA 3 (migrate_medical_system.sql)

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'historiales_medicos'
  AND column_name = 'embedding';

-- Debería retornar: embedding | USER-DEFINED (vector)
```

---

## ✅ Criterios de Aceptación

- [ ] Las 6 herramientas están implementadas y funcionan correctamente
- [ ] `registrar_consulta()` crea historial y genera embedding
- [ ] `consultar_historial_paciente()` soporta búsqueda semántica
- [ ] `actualizar_disponibilidad_doctor()` valida conflictos
- [ ] `generar_reporte_doctor()` genera los 3 tipos de reportes
- [ ] `obtener_estadisticas_consultas()` calcula métricas correctamente
- [ ] `buscar_citas_por_periodo()` aplica todos los filtros
- [ ] Todas las herramientas validan permisos del doctor
- [ ] Mensajes de error claros y descriptivos
- [ ] Formato de salida legible y consistente

---

## 🧪 TESTS REQUERIDOS

### ⚠️ REGLA DE ORO: REPARAR CÓDIGO, NO TESTS

**CRÍTICO:** Si un test falla:
- ✅ **CORRECTO:** Reparar el código para que pase el test
- ❌ **INCORRECTO:** Modificar el test para que pase
- ⚖️ **ÚNICA EXCEPCIÓN:** Si el test tiene un error lógico evidente

---

### Tests Mínimos Obligatorios

**Ubicación:** `tests/Etapa_7/`

#### 1. test_registrar_consulta.py (8 tests)
```python
def test_registrar_consulta_exitoso()
def test_registrar_consulta_cita_inexistente()
def test_registrar_consulta_doctor_no_autorizado()
def test_registrar_consulta_genera_embedding()
def test_registrar_consulta_actualiza_cita()
def test_registrar_consulta_sin_medicamentos()
def test_registrar_consulta_con_proxima_cita()
def test_registrar_consulta_error_bd()
```

#### 2. test_consultar_historial.py (8 tests)
```python
def test_consultar_historial_completo()
def test_consultar_historial_con_busqueda_semantica()
def test_consultar_historial_paciente_inexistente()
def test_consultar_historial_vacio()
def test_consultar_historial_con_limite()
def test_consultar_historial_busqueda_sin_resultados()
def test_consultar_historial_formato_respuesta()
def test_consultar_historial_ordenado_por_fecha()
```

#### 3. test_actualizar_disponibilidad.py (7 tests)
```python
def test_actualizar_disponibilidad_bloquear()
def test_actualizar_disponibilidad_desbloquear()
def test_actualizar_disponibilidad_conflicto_citas()
def test_actualizar_disponibilidad_crear_nuevo()
def test_actualizar_disponibilidad_modificar_existente()
def test_actualizar_disponibilidad_fecha_invalida()
def test_actualizar_disponibilidad_doctor_inexistente()
```

#### 4. test_generar_reportes.py (9 tests)
```python
def test_reporte_citas_dia_con_citas()
def test_reporte_citas_dia_sin_citas()
def test_reporte_citas_mes()
def test_reporte_ingresos()
def test_reporte_tipo_invalido()
def test_reporte_fecha_personalizada()
def test_reporte_formato_correcto()
def test_reporte_citas_multiples_estados()
def test_reporte_doctor_inexistente()
```

#### 5. test_estadisticas.py (7 tests)
```python
def test_estadisticas_dia()
def test_estadisticas_semana()
def test_estadisticas_mes()
def test_estadisticas_calculo_tasa_asistencia()
def test_estadisticas_pacientes_unicos()
def test_estadisticas_pacientes_recurrentes()
def test_estadisticas_periodo_invalido()
```

#### 6. test_buscar_citas.py (8 tests)
```python
def test_buscar_citas_sin_filtros()
def test_buscar_citas_filtro_estado()
def test_buscar_citas_filtro_paciente()
def test_buscar_citas_filtros_combinados()
def test_buscar_citas_sin_resultados()
def test_buscar_citas_formato_respuesta()
def test_buscar_citas_ordenadas_por_fecha()
def test_buscar_citas_fecha_invalida()
```

#### 7. test_integration_advanced_tools.py (10 tests)
```python
def test_flujo_completo_consulta_historial()
def test_reporte_refleja_nueva_consulta()
def test_estadisticas_actualizadas_tras_registro()
def test_busqueda_semantica_encuentra_diagnostico()
def test_bloqueo_disponibilidad_impide_nueva_cita()
def test_multiples_reportes_consistentes()
def test_historial_multiple_doctors_aislado()
def test_permisos_doctor_diferentes_pacientes()
def test_embedding_similarity_search()
def test_estadisticas_con_diferentes_periodos()
```

### Cobertura Mínima

**Meta: 80%+ de cobertura de código**

- ✅ Casos exitosos (happy path)
- ✅ Casos de error (error handling)
- ✅ Casos edge (límites, nulos, vacíos)
- ✅ Validación de permisos
- ✅ Búsqueda semántica con embeddings
- ✅ Conflictos de disponibilidad

---

## 📚 Documentación Requerida

Al finalizar la etapa, crear:

### 1. `tests/Etapa_7/README.md`
```markdown
# Tests - ETAPA 7: Herramientas Médicas Avanzadas

## Ejecución
pytest tests/Etapa_7/ -v

## Cobertura
pytest tests/Etapa_7/ --cov=src/medical/advanced_tools --cov=src/medical/reports --cov=src/medical/analytics

## Tests por Componente
[Lista de archivos de tests y descripción]
```

### 2. `docs/ETAPA_7_COMPLETADA.md`
```markdown
# ✅ ETAPA 7 COMPLETADA: Herramientas Médicas Avanzadas

**Fecha de inicio:** [fecha]
**Fecha de finalización:** [fecha]
**Duración real:** X días

## Componentes Implementados
[Lista de herramientas con descripción]

## Tests Ejecutados
Total: X tests
Pasando: X (100%)

## Problemas Encontrados y Resueltos
[Documentar problemas]
```

### 3. Actualizar `docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md`
Marcar ETAPA 7 como ✅ COMPLETADA

---

## 🔍 Checklist de Finalización

- [ ] Las 6 herramientas implementadas correctamente
- [ ] Tests creados (mínimo 47 tests)
- [ ] 100% de tests pasando
- [ ] Cobertura >80%
- [ ] Validación de permisos en todas las herramientas
- [ ] Búsqueda semántica funciona correctamente
- [ ] Reportes generan formato correcto
- [ ] Estadísticas calculan métricas precisas
- [ ] Sin vulnerabilidades de seguridad
- [ ] Código cumple PEP8
- [ ] Sin warnings en logs
- [ ] Documentación completa (README + reporte)

---

## 📞 Comunicación

Al finalizar, reportar:

```
✅ ETAPA 7 COMPLETADA

Componentes: 6 herramientas médicas avanzadas
Tests: X/X pasando (100%)
Duración: X días
Cobertura: X%

Próximo paso: ETAPA 8 - Actualización del Grafo LangGraph

¿Proceder con la siguiente etapa?
```

---

**Última actualización:** 29 de Enero de 2026
**Prioridad:** 🟢 BAJA (implementar después del sistema básico)
