import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import { Loader2, RefreshCw, MessageSquare, Brain, X, User, Bot, Hash } from 'lucide-react';
import * as THREE from 'three';

interface Message {
  type: string;
  content: string;
  name?: string;
}

interface VectorPoint {
  id: string;
  vector_number?: number;
  x: number;
  y: number;
  z: number;
  label: string;
  message_preview?: string;
  message_count?: number;
  messages?: Message[];
  metadata?: string | Record<string, any>;
}

interface ParsedMetadata {
  thread_id?: string;
  channel?: string;
  blob_size?: number;
  step?: number;
  type?: string;
  checkpoint_id?: string;
  message_count?: number;
  [key: string]: any;
}

// Detectar URL del backend
const getBackendUrl = () => {
  if (window.location.hostname.includes('github.dev')) {
    return window.location.origin.replace('-3000.', '-8000.');
  }
  return 'http://localhost:8000';
};

// Componente para un punto individual con tooltip mejorado
const VectorPoint3D: React.FC<{
  position: [number, number, number];
  color: string;
  label: string;
  vectorNumber?: number;
  messagePreview?: string;
  metadata?: string | Record<string, any>;
  onClick?: () => void;
  isSelected?: boolean;
}> = ({ position, color, label, vectorNumber, messagePreview, metadata, onClick, isSelected }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  // Parsear metadata si es string
  const parsedMetadata: ParsedMetadata | null = useMemo(() => {
    if (!metadata) return null;
    if (typeof metadata === 'object') return metadata as ParsedMetadata;
    try {
      return JSON.parse(metadata);
    } catch {
      return { raw: metadata };
    }
  }, [metadata]);

  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.scale.setScalar(hovered || isSelected ? 1.5 : 1);
    }
  });

  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshStandardMaterial
          color={hovered || isSelected ? '#ffffff' : color}
          emissive={color}
          emissiveIntensity={hovered || isSelected ? 0.5 : 0.2}
        />
      </mesh>
      {hovered && !isSelected && (
        <Html distanceFactor={10}>
          <div className="bg-gray-900/95 border border-gray-600 rounded-lg p-3 min-w-[250px] max-w-[350px] shadow-xl backdrop-blur-sm pointer-events-none">
            {/* Header con número de vector e ID */}
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-700">
              <div className="bg-blue-500/30 text-blue-300 px-2 py-0.5 rounded text-xs font-bold flex items-center gap-1">
                <Hash size={10} />
                Vector {vectorNumber || '?'}
              </div>
              <span className="text-gray-400 text-xs font-mono truncate">{parsedMetadata?.thread_id?.slice(0, 15) || label.slice(0, 15)}...</span>
            </div>
            
            {/* Mensaje en texto natural */}
            <div className="mb-2">
              <p className="text-white text-sm leading-relaxed">
                {messagePreview || label || 'Sin contenido de mensaje'}
              </p>
            </div>
            
            {/* Info adicional */}
            <div className="text-xs text-gray-500 flex items-center gap-3 pt-2 border-t border-gray-700">
              {parsedMetadata?.message_count !== undefined && (
                <span className="flex items-center gap-1">
                  <MessageSquare size={10} />
                  {parsedMetadata.message_count} msgs
                </span>
              )}
              {parsedMetadata?.blob_size && (
                <span>{(parsedMetadata.blob_size / 1024).toFixed(1)} KB</span>
              )}
              <span className="text-blue-400">Click para más detalles</span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
};

// Componente para el grid de referencia
const ReferenceGrid: React.FC = () => {
  return (
    <group>
      <gridHelper args={[100, 20, '#444', '#333']} rotation={[0, 0, 0]} />
      <gridHelper args={[100, 20, '#444', '#333']} rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -50]} />
      <gridHelper args={[100, 20, '#444', '#333']} rotation={[0, 0, Math.PI / 2]} position={[-50, 0, 0]} />
      
      {/* Axes */}
      <arrowHelper args={[new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), 55, 0xff0000]} />
      <arrowHelper args={[new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), 55, 0x00ff00]} />
      <arrowHelper args={[new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), 55, 0x0000ff]} />
    </group>
  );
};

// Componente de escena
const Scene: React.FC<{
  vectors: VectorPoint[];
  selectedId: string | null;
  onSelectVector: (id: string) => void;
}> = ({ vectors, selectedId, onSelectVector }) => {
  // Generar colores basados en posición para crear clusters visuales
  const getColorForVector = (v: VectorPoint): string => {
    const hue = ((v.x + 50) / 100) * 360;
    return `hsl(${hue}, 70%, 50%)`;
  };

  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} />
      <pointLight position={[-10, -10, -10]} intensity={0.5} />
      
      <ReferenceGrid />
      
      {vectors.map((vector) => (
        <VectorPoint3D
          key={vector.id}
          position={[vector.x, vector.y, vector.z]}
          color={getColorForVector(vector)}
          label={vector.label}
          vectorNumber={vector.vector_number}
          messagePreview={vector.message_preview}
          metadata={vector.metadata}
          onClick={() => onSelectVector(vector.id)}
          isSelected={selectedId === vector.id}
        />
      ))}
      
      <OrbitControls
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={10}
        maxDistance={200}
      />
    </>
  );
};

// Componente principal
const VectorViewer: React.FC = () => {
  const [vectors, setVectors] = useState<VectorPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVector, setSelectedVector] = useState<string | null>(null);
  const [stats, setStats] = useState<{ total: number; table?: string; isReal?: boolean } | null>(null);
  const [dataSource, setDataSource] = useState<'conversations' | 'embeddings'>('conversations');

  const backendUrl = getBackendUrl();

  const loadVectors = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Cargar SOLO conversaciones reales - sin datos mock
      const convResponse = await fetch(`${backendUrl}/api/database/conversation-vectors?limit=500`);
      const convData = await convResponse.json();
      
      if (convData.success && convData.vectors && convData.vectors.length > 0) {
        setVectors(convData.vectors);
        setStats({ total: convData.total, table: convData.table, isReal: true });
        setDataSource('conversations');
      } else {
        // No hay datos - mostrar mensaje, NO datos falsos
        setVectors([]);
        setStats({ total: 0, table: 'Sin datos', isReal: true });
        setError('No hay conversaciones almacenadas en la base de datos. Inicia una conversación con el agente para ver datos aquí.');
      }
    } catch (err) {
      setError(`Error de conexión: ${err}. Verifica que el backend esté corriendo en el puerto 8000.`);
      setVectors([]);
      setStats({ total: 0, table: 'Error', isReal: false });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVectors();
  }, []);

  const selectedVectorData = useMemo(() => 
    vectors.find(v => v.id === selectedVector),
    [vectors, selectedVector]
  );

  // Parsear metadata del vector seleccionado
  const parsedSelectedMetadata: ParsedMetadata | null = useMemo(() => {
    if (!selectedVectorData?.metadata) return null;
    if (typeof selectedVectorData.metadata === 'object') return selectedVectorData.metadata as ParsedMetadata;
    try {
      return JSON.parse(selectedVectorData.metadata);
    } catch {
      return { raw: selectedVectorData.metadata };
    }
  }, [selectedVectorData]);

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            {dataSource === 'conversations' ? <MessageSquare size={20} /> : <Brain size={20} />}
            {dataSource === 'conversations' ? 'Conversation Vectors' : 'Memory Embeddings'}
          </h2>
          <p className="text-xs text-gray-400 mt-1 flex items-center gap-2">
            {stats ? (
              <>
                <span>{stats.total} vectors from {stats.table || 'database'}</span>
                {stats.isReal ? (
                  <span className="bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded text-[10px]">REAL DATA</span>
                ) : (
                  <span className="bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 rounded text-[10px]">EXAMPLE</span>
                )}
              </>
            ) : 'Loading...'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={loadVectors}
            disabled={loading}
            className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Reload
          </button>
        </div>
      </div>

      {/* Controls Legend */}
      <div className="bg-gray-800/50 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-red-500"></span> X-axis
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-green-500"></span> Y-axis
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-blue-500"></span> Z-axis
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500">
          <span>🖱️ Left click: Rotate</span>
          <span>🖱️ Right click: Pan</span>
          <span>🖱️ Scroll: Zoom</span>
        </div>
      </div>

      {/* 3D Canvas */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center">
              <Loader2 size={48} className="animate-spin text-blue-500 mx-auto mb-4" />
              <p className="text-gray-400">Loading vectors...</p>
            </div>
          </div>
        ) : (
          <Canvas
            camera={{ position: [60, 40, 60], fov: 50 }}
            style={{ background: '#111827' }}
          >
            <Scene
              vectors={vectors}
              selectedId={selectedVector}
              onSelectVector={setSelectedVector}
            />
          </Canvas>
        )}

        {/* Selected Vector Info - Panel expandido con todos los detalles */}
        {selectedVectorData && (
          <div className="absolute bottom-4 left-4 right-4 md:right-auto md:max-w-xl bg-gray-800/98 border border-gray-600 rounded-lg shadow-2xl backdrop-blur-sm max-h-[70vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-750 rounded-t-lg">
              <div className="flex items-center gap-3">
                <div className="bg-blue-500/30 text-blue-300 px-3 py-1 rounded-full text-sm font-bold flex items-center gap-1">
                  <Hash size={14} />
                  Vector {selectedVectorData.vector_number || '?'}
                </div>
                <h3 className="text-white font-semibold">Detalles del Chunk</h3>
              </div>
              <button
                onClick={() => setSelectedVector(null)}
                className="text-gray-400 hover:text-white p-1.5 hover:bg-gray-700 rounded-full transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            
            {/* Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Info Grid */}
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-gray-700/50 rounded p-2">
                  <span className="text-gray-400 block mb-1">ID</span>
                  <span className="text-white font-mono text-[10px] break-all">{selectedVectorData.id}</span>
                </div>
                <div className="bg-gray-700/50 rounded p-2">
                  <span className="text-gray-400 block mb-1">Posición 3D</span>
                  <span className="text-cyan-300 font-mono text-[11px]">
                    ({selectedVectorData.x.toFixed(1)}, {selectedVectorData.y.toFixed(1)}, {selectedVectorData.z.toFixed(1)})
                  </span>
                </div>
                <div className="bg-gray-700/50 rounded p-2">
                  <span className="text-gray-400 block mb-1">Mensajes</span>
                  <span className="text-green-300 font-bold">{selectedVectorData.message_count || 0}</span>
                </div>
              </div>
              
              {/* Metadata */}
              {parsedSelectedMetadata && (
                <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600">
                  <h4 className="text-xs text-gray-400 mb-2 font-medium">📋 Metadata</h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {parsedSelectedMetadata.thread_id && (
                      <div>
                        <span className="text-gray-500">Thread ID:</span>
                        <p className="text-blue-300 font-mono text-[10px] break-all">{parsedSelectedMetadata.thread_id}</p>
                      </div>
                    )}
                    {parsedSelectedMetadata.channel && (
                      <div>
                        <span className="text-gray-500">Channel:</span>
                        <p className="text-green-300">{parsedSelectedMetadata.channel}</p>
                      </div>
                    )}
                    {parsedSelectedMetadata.blob_size && (
                      <div>
                        <span className="text-gray-500">Tamaño:</span>
                        <p className="text-yellow-300">{(parsedSelectedMetadata.blob_size / 1024).toFixed(2)} KB</p>
                      </div>
                    )}
                    {parsedSelectedMetadata.step !== undefined && (
                      <div>
                        <span className="text-gray-500">Step:</span>
                        <p className="text-purple-300">{parsedSelectedMetadata.step}</p>
                      </div>
                    )}
                    {parsedSelectedMetadata.checkpoint_id && (
                      <div className="col-span-2">
                        <span className="text-gray-500">Checkpoint:</span>
                        <p className="text-cyan-300 font-mono text-[10px] break-all">{parsedSelectedMetadata.checkpoint_id}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Mensajes de la conversación */}
              {selectedVectorData.messages && selectedVectorData.messages.length > 0 && (
                <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600">
                  <h4 className="text-xs text-gray-400 mb-3 font-medium flex items-center gap-2">
                    <MessageSquare size={12} />
                    Mensajes de la Conversación
                  </h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedVectorData.messages.map((msg, idx) => (
                      <div 
                        key={idx} 
                        className={`rounded-lg p-3 ${
                          msg.type === 'human' 
                            ? 'bg-blue-900/40 border-l-2 border-blue-400' 
                            : msg.type === 'ai' 
                            ? 'bg-purple-900/40 border-l-2 border-purple-400'
                            : 'bg-gray-600/40 border-l-2 border-gray-400'
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          {msg.type === 'human' ? (
                            <User size={12} className="text-blue-400" />
                          ) : (
                            <Bot size={12} className="text-purple-400" />
                          )}
                          <span className={`text-xs font-medium ${
                            msg.type === 'human' ? 'text-blue-300' : 'text-purple-300'
                          }`}>
                            {msg.type === 'human' ? 'Usuario' : msg.type === 'ai' ? 'Asistente' : msg.type}
                          </span>
                          {msg.name && (
                            <span className="text-gray-500 text-[10px]">({msg.name})</span>
                          )}
                        </div>
                        <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">
                          {msg.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Preview si no hay mensajes decodificados */}
              {(!selectedVectorData.messages || selectedVectorData.messages.length === 0) && selectedVectorData.message_preview && (
                <div className="bg-gray-700/30 rounded-lg p-3 border border-gray-600">
                  <h4 className="text-xs text-gray-400 mb-2 font-medium">💬 Preview del Mensaje</h4>
                  <p className="text-white text-sm leading-relaxed">{selectedVectorData.message_preview}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error overlay */}
        {error && (
          <div className="absolute top-4 right-4 bg-red-900/90 border border-red-600 rounded-lg p-3 max-w-sm">
            <p className="text-red-200 text-sm">{error}</p>
            <p className="text-red-300 text-xs mt-1">Showing example data</p>
          </div>
        )}

        {/* Stats overlay */}
        <div className="absolute top-4 left-4 bg-gray-800/90 border border-gray-600 rounded-lg p-3 backdrop-blur-sm">
          <div className="text-xs space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-gray-400">Vectors:</span>
              <span className="text-white font-bold">{vectors.length}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-400">Source:</span>
              <span className={`font-medium ${dataSource === 'conversations' ? 'text-blue-400' : 'text-purple-400'}`}>
                {dataSource === 'conversations' ? 'Conversations' : 'Embeddings'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-400">Selected:</span>
              <span className="text-white">{selectedVector ? '1' : '0'}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VectorViewer;
