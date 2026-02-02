import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface NodeDescription {
  title: string;
  description: string;
  timestamp?: string;
  duration_ms?: number;
  details?: string[];
}

interface VerboseNodeProps {
  data: {
    label: string;
    status: 'idle' | 'running' | 'completed' | 'error';
    duration_ms?: number;
    userType?: 'doctor' | 'patient' | 'unknown';
    descriptions: NodeDescription[];
  };
  selected?: boolean;
}

// Descripciones en lenguaje natural para cada nodo
export const nodeDescriptions: Record<string, (userType?: string) => string> = {
  // Nodos principales
  'n0': () => '🔍 Analizando el mensaje entrante para identificar si el usuario es un paciente, doctor o usuario nuevo...',
  'n1': () => '💾 Buscando en caché si existe una respuesta previa similar para acelerar la respuesta...',
  'n2': (userType) => userType === 'doctor' 
    ? '🩺 Usuario identificado como DOCTOR - Redirigiendo al flujo médico especializado...'
    : '👤 Usuario identificado como PACIENTE - Preparando asistente personal Maya...',
  'n2a': () => '🤖 Maya (Asistente Personal) activada. Procesando solicitud del paciente con empatía y claridad...',
  'n2b': () => '👨‍⚕️ Maya (Asistente Médico) activada. Accediendo a funcionalidades avanzadas para doctores...',
  'n3a': () => '🧠 Buscando en memoria episódica conversaciones previas relevantes del paciente...',
  'n3b': () => '📋 Accediendo a registros médicos y citas del sistema para el doctor...',
  'n4a': () => '⚡ Analizando intención del paciente y seleccionando herramientas apropiadas...',
  'n4b': () => '⚡ Analizando solicitud del doctor y preparando acciones médicas...',
  'n5a': () => '📅 Ejecutando acción en calendario personal: crear, modificar o consultar eventos...',
  'n5b': () => '🏥 Ejecutando acción médica: gestionar citas, consultar disponibilidad, o actualizar registros...',
  'n6': () => '✍️ Generando respuesta natural y amigable basada en los resultados obtenidos...',
  'n7': () => '💾 Guardando contexto de la conversación para mantener continuidad en futuras interacciones...',
  'n6r': () => '📞 Recepcionista virtual procesando solicitud de agendamiento o información...',
  'n8': () => '🔄 Sincronizando datos con Google Calendar y base de datos PostgreSQL...',
  'n9': () => '⏰ Programando recordatorios automáticos 24h y 2h antes de las citas...',
  'conv': () => '💬 Generando respuesta conversacional amigable para el usuario...',
  
  // Bases de datos
  'db_postgres': () => '🐘 PostgreSQL: Base de datos principal con usuarios, citas y conversaciones...',
  'db_pgvector': () => '🔢 pgVector: Almacenando y buscando embeddings para memoria semántica...',
  'db_cache': () => '⚡ Redis: Cache de sesiones activas para respuestas ultra-rápidas...',
  
  // LLMs
  'llm_deepseek': () => '🧠 DeepSeek: Procesando lenguaje natural con modelo primario...',
  'llm_claude': () => '🤖 Claude Sonnet: Modelo de respaldo con capacidades avanzadas...',
  
  // Herramientas
  'tool_calendar': () => '📅 Google Calendar API: Gestionando eventos y sincronización...',
  'tool_citas': () => '🗓️ Gestor de Citas: Manejando agenda médica y disponibilidad...',
  'tool_search': () => '🔍 Buscador: Consultando información relevante...',
  
  // Servicios
  'whatsapp': () => '📱 WhatsApp: Recibiendo mensaje del usuario...',
  'response': () => '📤 Enviando respuesta al usuario por WhatsApp...',
};

const VerboseNode: React.FC<VerboseNodeProps> = ({ data }) => {
  const { label, status, duration_ms, descriptions = [] } = data;

  const getStatusColor = () => {
    switch (status) {
      case 'running': return 'border-blue-500 bg-blue-900/50';
      case 'completed': return 'border-green-500 bg-green-900/50';
      case 'error': return 'border-red-500 bg-red-900/50';
      default: return 'border-gray-600 bg-gray-800/50';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'running': return '⏳';
      case 'completed': return '✅';
      case 'error': return '❌';
      default: return '⚪';
    }
  };

  return (
    <div className="relative">
      {/* Handles para conexiones */}
      <Handle type="target" position={Position.Left} className="!bg-gray-500" />
      <Handle type="source" position={Position.Right} className="!bg-gray-500" />
      
      {/* Nodo principal */}
      <div className={`min-w-[180px] rounded-lg border-2 ${getStatusColor()} transition-all duration-300`}>
        <div className="px-4 py-3 flex items-center justify-between">
          <span className="text-white font-semibold text-sm">{label}</span>
          <span className="text-lg">{getStatusIcon()}</span>
        </div>
        
        {duration_ms !== undefined && duration_ms !== null && (
          <div className="px-4 pb-2 text-xs text-gray-400">
            ⏱️ {duration_ms.toFixed(0)}ms
          </div>
        )}
      </div>

      {/* Panel de descripciones verbosas (acumulativas) */}
      {descriptions.length > 0 && (
        <div className="absolute top-full left-0 mt-2 w-[300px] max-h-[200px] overflow-y-auto 
                        bg-gray-900/95 border border-gray-700 rounded-lg shadow-xl z-50">
          {descriptions.map((desc, idx) => (
            <div 
              key={idx} 
              className={`p-3 border-b border-gray-700/50 last:border-b-0 
                         ${idx === descriptions.length - 1 ? 'bg-gray-800/50' : ''}`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-blue-400">{desc.title}</span>
                {desc.timestamp && (
                  <span className="text-xs text-gray-500">
                    {new Date(desc.timestamp).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-300 leading-relaxed">{desc.description}</p>
              {desc.details && desc.details.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {desc.details.map((detail, dIdx) => (
                    <li key={dIdx} className="text-xs text-gray-400 flex items-start gap-1">
                      <span className="text-gray-600">•</span>
                      {detail}
                    </li>
                  ))}
                </ul>
              )}
              {desc.duration_ms && (
                <div className="mt-1 text-xs text-green-400">
                  Completado en {desc.duration_ms.toFixed(0)}ms
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default memo(VerboseNode);
