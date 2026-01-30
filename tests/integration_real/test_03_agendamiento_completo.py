"""
Test de Integración: Flujo Completo de Agendamiento de Cita
============================================================

Este test simula una conversación real donde un paciente agenda una cita.

Flujo probado:
1. Paciente envía mensaje → Sistema identifica usuario
2. Clasificación LLM → solicitud_cita_paciente  
3. Recepcionista muestra opciones (A, B, C)
4. Paciente selecciona opción → Cita creada en BD
5. Confirmación al paciente con detalles
"""

import pytest
import logging
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestFlujoAgendamientoCompleto:
    """Tests end-to-end para el flujo de agendamiento."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        from src.graph_whatsapp_etapa8 import crear_grafo_whatsapp
        from src.database.db_config import get_db_session
        from src.medical.models import CitasMedicas
        
        self.grafo = crear_grafo_whatsapp()
        self.thread_id = f"test_agendar_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.paciente_phone = '+526649876543'  # Juan Pérez (Test)
        
        # Limpiar citas de prueba anteriores
        with get_db_session() as db:
            db.query(CitasMedicas).filter(
                CitasMedicas.motivo_consulta.like('%WhatsApp%')
            ).delete()
            db.commit()
        
        yield
    
    def test_paso1_solicitar_cita_muestra_opciones(self):
        """
        PASO 1: El paciente solicita una cita y el sistema muestra opciones.
        
        Verifica:
        - Usuario identificado correctamente
        - LLM clasifica como solicitud_cita_paciente
        - Respuesta incluye opciones A, B, C
        - Estado cambia a esperando_seleccion
        """
        estado = {
            'messages': [HumanMessage(content='Hola, quiero agendar una cita médica')],
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'inicial',
        }
        
        config = {'configurable': {'thread_id': self.thread_id}}
        resultado = self.grafo.invoke(estado, config)
        
        # Verificar clasificación
        assert resultado.get('clasificacion_mensaje') in ['solicitud_cita_paciente', 'solicitud_cita', 'cita']
        assert resultado.get('confianza_clasificacion', 0) >= 0.8
        
        # Verificar tipo usuario
        assert resultado.get('tipo_usuario') == 'paciente_externo'
        
        # Verificar estado
        assert resultado.get('estado_conversacion') == 'esperando_seleccion'
        
        # Verificar slots disponibles
        slots = resultado.get('slots_disponibles', [])
        assert len(slots) >= 1, "Debe haber al menos 1 slot disponible"
        
        # Verificar respuesta incluye opciones
        ai_messages = [m for m in resultado.get('messages', []) if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1, "Debe haber al menos una respuesta AI"
        
        respuesta_texto = ai_messages[-1].content
        assert 'A)' in respuesta_texto or '**A)**' in respuesta_texto
        assert 'Juan' in respuesta_texto  # Nombre del paciente
        
        logger.info("✅ PASO 1 completado: Opciones mostradas correctamente")
    
    def test_paso2_seleccionar_opcion_crea_cita(self):
        """
        PASO 2: El paciente selecciona una opción y se crea la cita en BD.
        
        Verifica:
        - Selección procesada correctamente
        - Cita creada en base de datos
        - Estado cambia a completado
        - Respuesta incluye confirmación con detalles
        """
        from src.database.db_config import get_db_session
        from src.medical.models import CitasMedicas
        
        # Primero ejecutar paso 1
        estado1 = {
            'messages': [HumanMessage(content='Necesito agendar una cita')],
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'inicial',
        }
        
        resultado1 = self.grafo.invoke(estado1, {'configurable': {'thread_id': self.thread_id}})
        slots = resultado1.get('slots_disponibles', [])
        
        assert len(slots) >= 1, "Necesitamos al menos 1 slot para continuar"
        
        # Ejecutar paso 2: seleccionar opción A
        estado2 = {
            'messages': [HumanMessage(content='A')],
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'esperando_seleccion',
            'slots_disponibles': slots,
        }
        
        resultado2 = self.grafo.invoke(estado2, {'configurable': {'thread_id': self.thread_id + '_2'}})
        
        # Verificar estado final
        assert resultado2.get('estado_conversacion') == 'completado'
        
        # Verificar respuesta incluye confirmación
        ai_messages = [m for m in resultado2.get('messages', []) if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1
        
        respuesta_texto = ai_messages[-1].content
        assert '🎉' in respuesta_texto or 'agendada' in respuesta_texto.lower()
        assert 'Doctor' in respuesta_texto or 'Dr.' in respuesta_texto
        
        # Verificar cita en BD
        with get_db_session() as db:
            cita = db.query(CitasMedicas).filter(
                CitasMedicas.paciente_id == 1,  # Juan Pérez
                CitasMedicas.motivo_consulta.like('%WhatsApp%')
            ).order_by(CitasMedicas.id.desc()).first()
            
            assert cita is not None, "La cita debe existir en la base de datos"
            assert cita.estado.value == 'programada'
            assert cita.doctor_id in [1, 2]  # Santiago o Joana
        
        logger.info("✅ PASO 2 completado: Cita creada en BD")
    
    def test_flujo_completo_e2e(self):
        """
        Test end-to-end completo: Solicitar → Seleccionar → Confirmar
        """
        from src.database.db_config import get_db_session
        from src.medical.models import CitasMedicas
        
        logger.info("🚀 Iniciando test E2E de agendamiento")
        
        # === PASO 1 ===
        estado1 = {
            'messages': [HumanMessage(content='Buenas tardes, quisiera sacar una cita')],
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'inicial',
        }
        
        resultado1 = self.grafo.invoke(estado1, {'configurable': {'thread_id': self.thread_id}})
        
        assert resultado1.get('estado_conversacion') == 'esperando_seleccion'
        slots = resultado1.get('slots_disponibles', [])
        assert len(slots) >= 1
        
        # === PASO 2 ===
        estado2 = {
            'messages': [HumanMessage(content='B')],  # Elegir opción B
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'esperando_seleccion',
            'slots_disponibles': slots,
        }
        
        resultado2 = self.grafo.invoke(estado2, {'configurable': {'thread_id': self.thread_id + '_2'}})
        
        # Verificaciones finales
        assert resultado2.get('estado_conversacion') == 'completado'
        
        # Verificar cita en BD
        with get_db_session() as db:
            citas = db.query(CitasMedicas).filter(
                CitasMedicas.motivo_consulta.like('%WhatsApp%')
            ).all()
            
            assert len(citas) >= 1, "Debe existir al menos una cita creada"
            
            ultima_cita = citas[-1]
            logger.info(f"✅ Cita creada: ID={ultima_cita.id}, Fecha={ultima_cita.fecha_hora_inicio}")
        
        logger.info("🎉 Test E2E completado exitosamente")


class TestFlujoAgendamientoErrores:
    """Tests para manejo de errores en el flujo de agendamiento."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        from src.graph_whatsapp_etapa8 import crear_grafo_whatsapp
        
        self.grafo = crear_grafo_whatsapp()
        self.thread_id = f"test_error_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.paciente_phone = '+526649876543'
        
        yield
    
    def test_seleccion_invalida_solicita_nueva_opcion(self):
        """
        Cuando el usuario envía una selección inválida, el sistema debe
        pedir que elija una opción válida.
        """
        # Paso 1: Obtener opciones
        estado1 = {
            'messages': [HumanMessage(content='Quiero una cita')],
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'inicial',
        }
        
        resultado1 = self.grafo.invoke(estado1, {'configurable': {'thread_id': self.thread_id}})
        slots = resultado1.get('slots_disponibles', [])
        
        # Paso 2: Enviar selección inválida
        estado2 = {
            'messages': [HumanMessage(content='Z')],  # Opción inválida
            'user_id': self.paciente_phone,
            'session_id': self.thread_id,
            'estado_conversacion': 'esperando_seleccion',
            'slots_disponibles': slots,
        }
        
        resultado2 = self.grafo.invoke(estado2, {'configurable': {'thread_id': self.thread_id + '_2'}})
        
        # Debe permanecer en esperando_seleccion
        assert resultado2.get('estado_conversacion') == 'esperando_seleccion'
        
        # Respuesta debe indicar error
        ai_messages = [m for m in resultado2.get('messages', []) if isinstance(m, AIMessage)]
        respuesta = ai_messages[-1].content if ai_messages else ''
        
        assert 'válida' in respuesta.lower() or 'opción' in respuesta.lower() or 'A' in respuesta
        
        logger.info("✅ Selección inválida manejada correctamente")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
