import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, Settings, Send, X, User, Stethoscope, ChevronDown, ChevronUp } from 'lucide-react';

// Detectar URL del backend principal (Codespaces o localhost)
const getAgentBackendUrl = () => {
  if (window.location.hostname.includes('github.dev')) {
    return window.location.origin.replace('-3000.', '-8002.');
  }
  return 'http://localhost:8002';
};

interface UserProfile {
  id: string;
  name: string;
  type: 'patient' | 'doctor';
  phone: string;
  chat_id: string;
  // Campos adicionales para doctores
  especialidad?: string;
  // Campos adicionales para pacientes
  fecha_nacimiento?: string;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const defaultProfiles: UserProfile[] = [
  {
    id: 'patient_1',
    name: 'Carlos López',
    type: 'patient',
    phone: '+52 55 1234 5678',
    chat_id: 'test_paciente_001',
    fecha_nacimiento: '1990-05-15'
  },
  {
    id: 'patient_2',
    name: 'María García',
    type: 'patient',
    phone: '+52 55 8765 4321',
    chat_id: 'test_paciente_002',
    fecha_nacimiento: '1985-08-22'
  },
  {
    id: 'doctor_1',
    name: 'Dr. Roberto Hernández',
    type: 'doctor',
    phone: '+52 55 1111 2222',
    chat_id: 'test_doctor_001',
    especialidad: 'Medicina General'
  },
  {
    id: 'doctor_2',
    name: 'Dra. Ana Martínez',
    type: 'doctor',
    phone: '+52 55 3333 4444',
    chat_id: 'test_doctor_002',
    especialidad: 'Pediatría'
  }
];

const TestChatbot: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [profiles, setProfiles] = useState<UserProfile[]>(defaultProfiles);
  const [selectedProfile, setSelectedProfile] = useState<UserProfile>(defaultProfiles[0]);
  const [editingProfile, setEditingProfile] = useState<UserProfile | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const backendUrl = getAgentBackendUrl();
      const response = await fetch(`${backendUrl}/api/whatsapp-agent/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          chat_id: selectedProfile.chat_id,
          message: inputText,
          sender_name: selectedProfile.name,
          phone: selectedProfile.phone,
          user_type: selectedProfile.type
        }),
      });

      const data = await response.json();
      
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response || data.message || 'Respuesta recibida',
        sender: 'bot',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `Error: ${error instanceof Error ? error.message : 'No se pudo conectar'}`,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const updateProfile = (updatedProfile: UserProfile) => {
    setProfiles(prev => prev.map(p => p.id === updatedProfile.id ? updatedProfile : p));
    if (selectedProfile.id === updatedProfile.id) {
      setSelectedProfile(updatedProfile);
    }
    setEditingProfile(null);
  };

  const clearChat = () => {
    setMessages([]);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="bg-blue-600/90 hover:bg-blue-500 text-white p-3 rounded-full shadow-lg transition-all hover:scale-110 backdrop-blur-sm"
        title="Abrir Chat de Prueba"
      >
        <MessageCircle size={24} />
      </button>
    );
  }

  return (
    <>
      {/* Chat Window */}
      <div className={`w-80 bg-gray-800/95 backdrop-blur-sm rounded-lg border border-gray-600 shadow-2xl flex flex-col transition-all ${isMinimized ? 'h-12' : 'h-96'}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-600 bg-gray-700/50 rounded-t-lg">
          <div className="flex items-center gap-2">
            {selectedProfile.type === 'doctor' ? (
              <Stethoscope size={16} className="text-white" />
            ) : (
              <User size={16} className="text-blue-400" />
            )}
            <span className="text-sm font-medium text-white truncate max-w-[120px]">
              {selectedProfile.name}
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
              selectedProfile.type === 'doctor' 
                ? 'bg-white/20 text-white' 
                : 'bg-blue-500/20 text-blue-300'
            }`}>
              {selectedProfile.type === 'doctor' ? 'Doctor' : 'Paciente'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowSettings(true)}
              className="p-1.5 hover:bg-gray-600 rounded transition-colors"
              title="Configuración"
            >
              <Settings size={14} className="text-gray-400 hover:text-white" />
            </button>
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1.5 hover:bg-gray-600 rounded transition-colors"
              title={isMinimized ? 'Expandir' : 'Minimizar'}
            >
              {isMinimized ? (
                <ChevronUp size={14} className="text-gray-400 hover:text-white" />
              ) : (
                <ChevronDown size={14} className="text-gray-400 hover:text-white" />
              )}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 hover:bg-gray-600 rounded transition-colors"
              title="Cerrar"
            >
              <X size={14} className="text-gray-400 hover:text-white" />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {messages.length === 0 && (
                <div className="text-center text-gray-500 text-xs py-4">
                  <MessageCircle size={24} className="mx-auto mb-2 opacity-50" />
                  <p>Envía un mensaje para probar el agente</p>
                  <p className="mt-1 text-gray-600">Usuario: {selectedProfile.name}</p>
                </div>
              )}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                      msg.sender === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-gray-700 text-gray-100 rounded-bl-none'
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words">{msg.text}</p>
                    <p className={`text-[10px] mt-1 ${
                      msg.sender === 'user' ? 'text-blue-200' : 'text-gray-400'
                    }`}>
                      {msg.timestamp.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-700 text-gray-100 px-3 py-2 rounded-lg rounded-bl-none">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-2 border-t border-gray-600">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Escribe un mensaje..."
                  className="flex-1 bg-gray-700 text-white text-sm px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none placeholder-gray-400"
                  disabled={isLoading}
                />
                <button
                  onClick={sendMessage}
                  disabled={isLoading || !inputText.trim()}
                  className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white p-2 rounded-lg transition-colors"
                >
                  <Send size={16} />
                </button>
              </div>
              <button
                onClick={clearChat}
                className="text-[10px] text-gray-500 hover:text-gray-300 mt-1 transition-colors"
              >
                Limpiar chat
              </button>
            </div>
          </>
        )}
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl border border-gray-600 shadow-2xl w-[500px] max-h-[80vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-600 bg-gray-700/50">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Settings size={20} />
                Configuración de Usuarios
              </h2>
              <button
                onClick={() => {
                  setShowSettings(false);
                  setEditingProfile(null);
                }}
                className="p-1 hover:bg-gray-600 rounded transition-colors"
              >
                <X size={20} className="text-gray-400 hover:text-white" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              {editingProfile ? (
                /* Edit Profile Form */
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-gray-300 mb-3">
                    Editando: {editingProfile.name}
                  </h3>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Nombre</label>
                      <input
                        type="text"
                        value={editingProfile.name}
                        onChange={(e) => setEditingProfile({ ...editingProfile, name: e.target.value })}
                        className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Tipo</label>
                      <select
                        value={editingProfile.type}
                        onChange={(e) => setEditingProfile({ ...editingProfile, type: e.target.value as 'patient' | 'doctor' })}
                        className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                      >
                        <option value="patient">Paciente</option>
                        <option value="doctor">Doctor</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Teléfono</label>
                      <input
                        type="text"
                        value={editingProfile.phone}
                        onChange={(e) => setEditingProfile({ ...editingProfile, phone: e.target.value })}
                        className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Chat ID</label>
                      <input
                        type="text"
                        value={editingProfile.chat_id}
                        onChange={(e) => setEditingProfile({ ...editingProfile, chat_id: e.target.value })}
                        className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                      />
                    </div>
                    {editingProfile.type === 'doctor' && (
                      <div className="col-span-2">
                        <label className="block text-xs text-gray-400 mb-1">Especialidad</label>
                        <input
                          type="text"
                          value={editingProfile.especialidad || ''}
                          onChange={(e) => setEditingProfile({ ...editingProfile, especialidad: e.target.value })}
                          className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                        />
                      </div>
                    )}
                    {editingProfile.type === 'patient' && (
                      <div className="col-span-2">
                        <label className="block text-xs text-gray-400 mb-1">Fecha de Nacimiento</label>
                        <input
                          type="date"
                          value={editingProfile.fecha_nacimiento || ''}
                          onChange={(e) => setEditingProfile({ ...editingProfile, fecha_nacimiento: e.target.value })}
                          className="w-full bg-gray-700 text-white text-sm px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                        />
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => updateProfile(editingProfile)}
                      className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded transition-colors"
                    >
                      Guardar Cambios
                    </button>
                    <button
                      onClick={() => setEditingProfile(null)}
                      className="flex-1 bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded transition-colors"
                    >
                      Cancelar
                    </button>
                  </div>
                </div>
              ) : (
                /* Profile List */
                <div className="space-y-3">
                  <p className="text-xs text-gray-400 mb-2">
                    Selecciona un usuario para el chat de prueba o edita sus datos:
                  </p>
                  
                  {/* Doctors */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <Stethoscope size={12} />
                      Doctores
                    </h4>
                    <div className="space-y-2">
                      {profiles.filter(p => p.type === 'doctor').map((profile) => (
                        <div
                          key={profile.id}
                          className={`flex items-center justify-between p-3 rounded-lg border transition-all cursor-pointer ${
                            selectedProfile.id === profile.id
                              ? 'bg-white/10 border-white/50'
                              : 'bg-gray-700/50 border-gray-600 hover:border-gray-500'
                          }`}
                          onClick={() => setSelectedProfile(profile)}
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium text-white">{profile.name}</p>
                            <p className="text-xs text-gray-400">{profile.phone} • {profile.especialidad}</p>
                            <p className="text-[10px] text-gray-500 font-mono">{profile.chat_id}</p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingProfile(profile);
                            }}
                            className="p-2 hover:bg-gray-600 rounded transition-colors"
                          >
                            <Settings size={14} className="text-gray-400" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Patients */}
                  <div>
                    <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <User size={12} />
                      Pacientes
                    </h4>
                    <div className="space-y-2">
                      {profiles.filter(p => p.type === 'patient').map((profile) => (
                        <div
                          key={profile.id}
                          className={`flex items-center justify-between p-3 rounded-lg border transition-all cursor-pointer ${
                            selectedProfile.id === profile.id
                              ? 'bg-blue-500/20 border-blue-500/50'
                              : 'bg-gray-700/50 border-gray-600 hover:border-gray-500'
                          }`}
                          onClick={() => setSelectedProfile(profile)}
                        >
                          <div className="flex-1">
                            <p className="text-sm font-medium text-white">{profile.name}</p>
                            <p className="text-xs text-gray-400">{profile.phone} • {profile.fecha_nacimiento}</p>
                            <p className="text-[10px] text-gray-500 font-mono">{profile.chat_id}</p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingProfile(profile);
                            }}
                            className="p-2 hover:bg-gray-600 rounded transition-colors"
                          >
                            <Settings size={14} className="text-gray-400" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            {!editingProfile && (
              <div className="px-4 py-3 border-t border-gray-600 bg-gray-700/30">
                <p className="text-[10px] text-gray-500 text-center">
                  Usuario seleccionado: <span className="text-gray-300">{selectedProfile.name}</span>
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default TestChatbot;
