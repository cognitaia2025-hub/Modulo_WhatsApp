● PROMPT ETAPA 1: IDENTIFICACIÓN DE USUARIOS

  🎯 Objetivo

  Implementar sistema que identifica automáticamente quién habla por WhatsApp (doctor, paciente o usuario personal) basado en número de teléfono, diferenciando roles sin requerir login.

  📋 Componentes

  🤖 Nodo N0 - Identificación Usuario

  Crear: src/nodes/identificacion_usuario_node.py
  Función:

- Extraer phone_number del mensaje WhatsApp
- Buscar usuario en tabla usuarios
- Si NO existe → crear automáticamente como 'paciente_externo'
- Si existe → cargar perfil y determinar tipo (doctor/personal)
- Agregar user_info, tipo_usuario, es_admin, doctor_id al estado

  Sin LLM - Solo consultas SQL

  🗄️ Tabla usuarios (Actualizar)

  Modificar: Tabla existente usuarios
  Agregar columnas:

- email VARCHAR UNIQUE
- is_active BOOLEAN DEFAULT TRUE
- tipo_usuario VARCHAR CHECK IN ('personal', 'doctor', 'paciente_externo', 'admin')

  Índices:

- idx_usuarios_tipo en tipo_usuario
- idx_usuarios_phone en phone_number (si no existe)

  🗄️ Tabla doctores (Validar)

  Ya existe - Solo verificar que tiene:

- phone_number FK a usuarios
- nombre_completo, especialidad
- orden_turno, total_citas_asignadas

  📝 Estado del Grafo (Actualizar)

  Modificar: src/state/agent_state.py
  Agregar campos:
  user_info: Dict[str, Any]
  tipo_usuario: str
  es_admin: bool
  doctor_id: Optional[int]
  paciente_id: Optional[int]

  🧪 Tests Requeridos

  Test 1: test_identificacion_node.py

- Usuario nuevo se registra automáticamente
- Usuario existente se identifica correctamente
- Doctor obtiene su doctor_id
- Admin se detecta correctamente
- Phone number se extrae bien del mensaje

  Test 2: test_user_registration.py

- Auto-registro crea usuario 'paciente_externo'
- No duplica usuarios existentes
- Actualiza last_seen en cada mensaje
- Campos obligatorios se llenan correctamente

  Test 3: test_user_types.py

- Diferencia entre doctor/personal/paciente
- Doctor tiene acceso a doctor_id
- Paciente NO tiene doctor_id
- Usuario personal tiene tipo correcto

  Test 4: test_integration_identificacion.py

- Nodo se integra correctamente en el grafo
- Estado se actualiza con user_info
- Flujo continúa después de identificación
- Maneja errores de BD gracefully

  Total esperado: ~15 tests pasando 100%

  ✅ Criterios de Aceptación

- Nodo identifica usuarios por phone_number
- Auto-registro de usuarios nuevos funciona
- Tabla usuarios tiene nuevas columnas
- Estado del grafo tiene campos user_info
- Todos los tests pasan (15/15)
- No rompe funcionalidad existente

  📚 Documentación

  Crear:

- tests/Etapa_1/README.md - Explicación de tests
- docs/ETAPA_1_COMPLETADA.md - Reporte final

  🚀 Resultado Esperado

  pytest tests/Etapa_1/ -v

# ====== 15 passed in X.XXs ======

  Referencias:

- Ver docs/PLAN_ESTRUCTURADO_IMPLEMENTACION.md sección ETAPA 1
- Ver .claude/CLAUDE.md para reglas de tests

  ---
  RECORDAR: Si test falla → reparar código, NO modificar tests
