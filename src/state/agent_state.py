"""
Estado del Agente de WhatsApp

Define la estructura de datos compartida que fluye a través del grafo.
"""

from typing import TypedDict, Optional, Annotated, Any, Dict, List
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class WhatsAppAgentState(TypedDict):
    """
    Estado compartido del agente que fluye a través de todos los nodos.
    
    Campos:
        messages: Historial de conversación
        user_id: Identificador único del usuario (número de teléfono)
        session_id: ID de la sesión actual
        es_admin: Indica si el usuario actual es administrador
        usuario_info: Diccionario con información completa del usuario desde BD
        usuario_registrado: True si ya existía, False si fue creado automáticamente
        tipo_usuario: Tipo de usuario (personal, doctor, paciente_externo, admin)
        doctor_id: ID del doctor si el usuario es doctor
        paciente_id: ID del paciente si el usuario tiene registro de paciente
        contexto_episodico: Resúmenes previos recuperados de pgvector
        herramientas_seleccionadas: IDs de herramientas a ejecutar
        requiere_herramientas: Indica si se detectó intención de usar herramientas de calendario
        resumen_actual: Resumen generado de la conversación
        timestamp: Marca de tiempo de la interacción
    """
    # Conversación
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str  # Número de teléfono en formato internacional (+52664...)
    session_id: str
    
    # Identificación de Usuario (ETAPA 1)
    es_admin: bool  # True si es el administrador del sistema
    usuario_info: Dict[str, Any]  # Datos completos del usuario desde BD
    usuario_registrado: bool  # True si ya existía, False si fue auto-creado
    tipo_usuario: str  # 'personal', 'doctor', 'paciente_externo', 'admin'
    doctor_id: Optional[int]  # ID del doctor si tipo_usuario = 'doctor'
    paciente_id: Optional[int]  # ID del paciente si tiene registro médico
    
    # Memoria Episódica (recuperada de pgvector)
    contexto_episodico: Optional[Dict[str, Any]]
    
    # Memoria Procedimental (consultada en PostgreSQL)
    herramientas_seleccionadas: List[str]
    
    # Control de flujo
    requiere_herramientas: bool  # True si se detectó intención de usar alguna de las 6 herramientas de calendario
    resumen_actual: Optional[str]
    sesion_expirada: bool  # True si han pasado >24h desde último mensaje
    
    # Resultado de último listado de eventos (para contexto en delete/update)
    ultimo_listado: Optional[List[Dict[str, Any]]]
    
    # Clasificación Inteligente (ETAPA 3)
    clasificacion_mensaje: Optional[str]  # 'personal', 'medica', 'chat', 'solicitud_cita_paciente'
    confianza_clasificacion: Optional[float]  # 0.0 - 1.0
    modelo_clasificacion_usado: Optional[str]  # 'deepseek', 'claude'
    tiempo_clasificacion_ms: Optional[int]  # Tiempo de procesamiento
    
    # Router por Identidad (ETAPA 9 - Optimización)
    ruta_siguiente: Optional[str]  # 'recepcionista', 'medica', 'personal', 'clasificador_llm'
    requiere_clasificacion_llm: bool  # True solo si el mensaje es genuinamente ambiguo
    
    # Recuperación Médica (ETAPA 3)
    contexto_medico: Optional[Dict[str, Any]]  # Pacientes recientes, citas, estadísticas
    
    # Conversación de Recepcionista (ETAPA 4)
    estado_conversacion: str = "inicial"  # inicial, solicitando_nombre, mostrando_opciones, esperando_seleccion, confirmando, completado
    slots_disponibles: List[Dict] = []  # Lista de slots mostrados al paciente
    paciente_nombre_temporal: Optional[str] = None  # Nombre extraído antes de registro
    
    # Campos para Slot Filling (optimización recepcionista)
    fecha_deseada: Optional[str]  # "lunes", "25 de octubre", "mañana"
    hora_deseada: Optional[str]  # "por la tarde", "9am", "en la mañana"
    intencion_confirmada: bool  # Para evitar que el LLM agende por error
    especialidad_preferida: Optional[str]  # "cardiología", "medicina general"
    cambio_de_tema: bool  # True si el LLM detectó cambio de contexto
    
    # Metadata
    timestamp: str
