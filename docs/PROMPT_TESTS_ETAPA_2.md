# 🧪 PROMPT: CREAR TESTS PARA ETAPA 2

## 📍 Ubicación de Tests
**Carpeta:** `tests\Etapa_2\`

---

## 🎯 Tu Tarea

Crea **70 tests** para validar el Sistema de Turnos Automático (Etapa 2).

---

## 📁 Archivos a Crear

### 1. `tests\Etapa_2\test_turnos.py` - 15 tests
**Probar:** `src\medical\turnos.py`

```python
# Tests obligatorios:
def test_alternancia_null_santiago():
    """Primera vez: NULL → Santiago (ID=1)"""
    
def test_alternancia_santiago_joana():
    """Santiago → Joana (ID=2)"""
    
def test_alternancia_joana_santiago():
    """Joana → Santiago (ID=1)"""
    
def test_actualizar_contadores():
    """Incrementa citas_santiago/citas_joana"""
    
def test_estadisticas_turnos():
    """obtener_estadisticas_turnos() retorna métricas"""

# + 10 tests más (conflictos, errores, edge cases)
```

---

### 2. `tests\Etapa_2\test_disponibilidad.py` - 15 tests
**Probar:** `src\medical\disponibilidad.py`

```python
# Tests obligatorios:
def test_dia_cerrado():
    """Rechaza Martes (1) y Miércoles (2)"""
    
def test_dia_laborable():
    """Acepta Jueves-Lunes (0,3,4,5,6)"""
    
def test_horario_valido():
    """08:30-18:30 es válido"""
    
def test_horario_fuera_rango():
    """Rechaza 07:00 o 20:00"""
    
def test_conflicto_exacto():
    """Detecta overlap cuando horarios son iguales"""
    
def test_conflicto_parcial():
    """Detecta overlap parcial"""

# + 9 tests más (timezone, doctor inactivo, BD)
```

---

### 3. `tests\Etapa_2\test_slots.py` - 15 tests
**Probar:** `src\medical\slots.py`

```python
# Tests obligatorios:
def test_generar_slots_7_dias():
    """Genera slots para 7 días adelante"""
    
def test_filtrar_dias_cerrados():
    """NO genera slots para Martes/Miércoles"""
    
def test_slots_1_hora():
    """Cada slot dura 1 hora"""
    
def test_aplicar_turnos():
    """Usa obtener_siguiente_doctor_turno() para cada slot"""
    
def test_no_revelar_doctor_frontend():
    """formatear_slots_para_frontend() elimina doctor_id"""
    
def test_fallback_doctor_ocupado():
    """Si doctor en turno ocupado → usa otro doctor"""

# + 9 tests más (agrupación, conteo, edge cases)
```

---

### 4. `tests\Etapa_2\test_agendamiento_turnos.py` - 15 tests
**Probar:** Integración completa del flujo de agendamiento

```python
# Tests obligatorios:
def test_agendar_con_turno_normal():
    """Agendamiento normal con doctor del turno"""
    
def test_agendar_con_reasignacion():
    """Reasignación automática si doctor ocupado"""
    
def test_actualizar_control_turnos_despues_agendar():
    """Se llama actualizar_control_turnos() después de crear cita"""
    
def test_campo_fue_asignacion_automatica():
    """fue_asignacion_automatica = TRUE"""
    
def test_campo_doctor_turno_original():
    """Guarda doctor_turno_original correctamente"""

# + 10 tests más (sincronización Google Calendar, errores)
```

---

### 5. `tests\Etapa_2\test_integration_etapa2.py` - 10 tests
**Probar:** Flujos completos end-to-end

```python
# Tests obligatorios:
def test_flujo_completo():
    """generar_slots() → seleccionar → agendar → confirmar"""
    
def test_10_agendamientos_consecutivos():
    """Alternancia perfecta en 10 citas"""
    
def test_equidad_distribucion():
    """Después de 20 citas, Santiago y Joana ~50% cada uno"""
    
def test_multiples_usuarios_simultaneos():
    """Sistema maneja concurrencia"""

# + 6 tests más
```

---

### 6. `tests\Etapa_2\README.md`
Documenta:
- Cómo ejecutar: `pytest tests/Etapa_2/ -v`
- Qué se prueba en cada archivo
- Cómo ejecutar tests individuales

---

## 📚 Referencias

### Ejemplo de Etapa 1 (Usa como referencia):
- `tests\Etapa_1\test_identificacion_node.py`
- `tests\Etapa_1\test_integration_identificacion.py`

### Fixtures necesarias:
```python
@pytest.fixture
def db_connection():
    """Conexión a BD de prueba"""
    
@pytest.fixture
def limpiar_control_turnos():
    """Resetea control_turnos antes de cada test"""
    
@pytest.fixture
def crear_doctores_prueba():
    """Crea Santiago (ID=1) y Joana (ID=2)"""
```

---

## ✅ Criterios de Éxito

- [ ] 70+ tests implementados
- [ ] Todos los tests pasan (100%)
- [ ] Cobertura >95% en código nuevo
- [ ] README.md de tests creado
- [ ] Tests usan fixtures para setup/teardown

---

## 🚀 Empezar

```bash
# 1. Crear archivos
cd tests\Etapa_2

# 2. Empezar con el más simple
# Crea test_turnos.py primero (más fácil)

# 3. Ejecutar mientras desarrollas
pytest tests\Etapa_2\test_turnos.py -v
```

---

## 📖 Documentación Útil

- **pytest:** https://docs.pytest.org/en/stable/
- **pytest fixtures:** https://docs.pytest.org/en/stable/fixture.html
- **psycopg3 testing:** https://www.psycopg.org/psycopg3/docs/api/connections.html

---

## ⚠️ Importante

1. **NO modifiques** el código de `src/medical/` (está perfecto)
2. **USA** BD de prueba (no la de producción)
3. **RESETEA** estado entre tests (fixtures)
4. **COMPARA** con tests de Etapa 1 para mantener calidad

---

**Meta:** Llevar Etapa 2 de **59/100 (F)** a **95+/100 (A)**

Solo faltan los tests. ¡El código ya es excelente!
