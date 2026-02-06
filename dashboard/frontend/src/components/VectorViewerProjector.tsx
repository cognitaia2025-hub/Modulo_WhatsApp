import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Html, Line, Text } from '@react-three/drei';
import { 
  Loader2, RefreshCw, Search, Filter, Users, User, 
  X, ChevronDown, Calendar, Tag, Info
} from 'lucide-react';
import * as THREE from 'three';

// ==================== INTERFACES ====================

interface MemoryVector {
  id: string;
  vector_number: number;
  x: number;
  y: number;
  z: number;
  color: string;
  tipo_usuario: 'paciente' | 'doctor';
  user_id: string;
  nombre_usuario: string;
  categoria: string;
  resumen: string;
  label: string;
  fecha_evento?: string;
  timestamp?: string;
  grupo_visual: string;
  doctor_id?: string;
  metadata?: string;
}

interface VectorStats {
  total: number;
  pacientes: number;
  doctores: number;
  grupos: Record<string, number>;
}

// ==================== CONSTANTS ====================

const CATEGORIA_COLORS: Record<string, string> = {
  cita: '#22c55e',        // Verde
  sintoma: '#ef4444',     // Rojo
  recordatorio: '#f59e0b', // Amarillo
  diagnostico: '#8b5cf6', // Púrpura
  tratamiento: '#06b6d4', // Cyan
  historial: '#6366f1',   // Indigo
  cancelacion: '#f97316', // Naranja
  general: '#94a3b8',     // Gris
};

const getBackendUrl = () => {
  // Detectar si estamos en desarrollo o producción
  if (window.location.hostname.includes('github.dev')) {
    return window.location.origin.replace('-3000.', '-8000.');
  }
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }
  return 'http://localhost:8000';
};

// ==================== 3D COMPONENTS ====================

// Punto individual en el espacio 3D
const VectorPoint: React.FC<{
  position: [number, number, number];
  color: string;
  size: number;
  isSelected: boolean;
  isHighlighted: boolean;
  isDimmed: boolean;
  vector: MemoryVector;
  onClick: () => void;
  onHover: (hovering: boolean) => void;
}> = ({ position, color, size, isSelected, isHighlighted, isDimmed, vector, onClick, onHover }) => {
  const meshRef = React.useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);
  
  useFrame(() => {
    if (meshRef.current) {
      const targetScale = isSelected ? 2.5 : hovered ? 1.8 : 1;
      meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
    }
  });
  
  const actualColor = isSelected ? '#fbbf24' : isHighlighted ? '#60a5fa' : color;
  const opacity = isDimmed ? 0.15 : 1;
  
  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={(e) => { e.stopPropagation(); onClick(); }}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true); onHover(true); }}
        onPointerOut={() => { setHovered(false); onHover(false); }}
      >
        <sphereGeometry args={[size, 16, 16]} />
        <meshStandardMaterial 
          color={actualColor} 
          transparent 
          opacity={opacity}
          emissive={isSelected || hovered ? actualColor : '#000000'}
          emissiveIntensity={isSelected ? 0.5 : hovered ? 0.3 : 0}
        />
      </mesh>
      
      {/* Tooltip on hover */}
      {hovered && !isSelected && (
        <Html distanceFactor={80} position={[0, size + 1, 0]}>
          <div className="bg-gray-900/95 border border-gray-600 rounded-lg p-3 min-w-[200px] max-w-[300px] shadow-xl pointer-events-none">
            <div className="flex items-center gap-2 mb-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: color }}
              />
              <span className="text-xs font-bold text-white">
                {vector.tipo_usuario === 'paciente' ? '👤 Paciente' : '🩺 Doctor'}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-700 text-gray-300">
                {vector.categoria}
              </span>
            </div>
            <p className="text-white text-xs font-medium mb-1">{vector.nombre_usuario}</p>
            <p className="text-gray-300 text-[11px] leading-relaxed">{vector.label}</p>
            {vector.fecha_evento && (
              <p className="text-blue-400 text-[10px] mt-1.5 flex items-center gap-1">
                <Calendar size={10} />
                {vector.fecha_evento}
              </p>
            )}
          </div>
        </Html>
      )}
    </group>
  );
};

// Líneas de conexión entre vectores del mismo grupo
const GroupConnections: React.FC<{
  vectors: MemoryVector[];
  selectedGroup: string | null;
}> = ({ vectors, selectedGroup }) => {
  if (!selectedGroup) return null;
  
  const groupVectors = vectors.filter(v => v.grupo_visual === selectedGroup);
  if (groupVectors.length < 2) return null;
  
  // Crear líneas entre vectores consecutivos del grupo
  const points: [number, number, number][] = groupVectors.map(v => [v.x, v.y, v.z]);
  
  return (
    <Line
      points={points}
      color="#60a5fa"
      lineWidth={1}
      transparent
      opacity={0.4}
      dashed
      dashSize={1}
      gapSize={0.5}
    />
  );
};

// Ejes de referencia con etiquetas
const AxisHelper: React.FC = () => {
  return (
    <group>
      {/* Ejes */}
      <arrowHelper args={[new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0, 0), 50, 0xff4444, 3, 2]} />
      <arrowHelper args={[new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, 0), 50, 0x44ff44, 3, 2]} />
      <arrowHelper args={[new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, 0, 0), 50, 0x4444ff, 3, 2]} />
      
      {/* Etiquetas */}
      <Text position={[55, 0, 0]} fontSize={3} color="#ff4444">X</Text>
      <Text position={[0, 55, 0]} fontSize={3} color="#44ff44">Y</Text>
      <Text position={[0, 0, 55]} fontSize={3} color="#4444ff">Z</Text>
      
      {/* Grid */}
      <gridHelper args={[100, 20, '#333333', '#222222']} rotation={[0, 0, 0]} />
    </group>
  );
};

// Escena principal
const Scene: React.FC<{
  vectors: MemoryVector[];
  selectedId: string | null;
  highlightedIds: string[];
  selectedGroup: string | null;
  onSelectVector: (id: string | null) => void;
  colorMode: 'tipo' | 'categoria';
}> = ({ vectors, selectedId, highlightedIds, selectedGroup, onSelectVector, colorMode }) => {
  
  const getColor = (v: MemoryVector) => {
    if (colorMode === 'tipo') {
      return v.tipo_usuario === 'paciente' ? '#3b82f6' : '#ffffff';
    }
    return CATEGORIA_COLORS[v.categoria] || CATEGORIA_COLORS.general;
  };

  // Calcular centroide de los vectores para centrar la cámara
  const centroid = useMemo(() => {
    if (vectors.length === 0) return { x: 0, y: 0, z: 0 };
    const sum = vectors.reduce((acc, v) => ({
      x: acc.x + v.x,
      y: acc.y + v.y,
      z: acc.z + v.z
    }), { x: 0, y: 0, z: 0 });
    return {
      x: sum.x / vectors.length,
      y: sum.y / vectors.length,
      z: sum.z / vectors.length
    };
  }, [vectors]);
  
  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[50, 50, 50]} intensity={1} />
      <pointLight position={[-50, -50, -50]} intensity={0.3} />
      
      <AxisHelper />
      <GroupConnections vectors={vectors} selectedGroup={selectedGroup} />
      
      {vectors.map((vector) => (
        <VectorPoint
          key={vector.id}
          position={[vector.x, vector.y, vector.z]}
          color={getColor(vector)}
          size={1.2}
          isSelected={selectedId === vector.id}
          isHighlighted={highlightedIds.includes(vector.id)}
          isDimmed={selectedGroup !== null && vector.grupo_visual !== selectedGroup}
          vector={vector}
          onClick={() => onSelectVector(selectedId === vector.id ? null : vector.id)}
          onHover={() => {}} // No-op, tooltip se maneja internamente
        />
      ))}
      
      <OrbitControls
        target={[centroid.x, centroid.y, centroid.z]}
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={10}
        maxDistance={300}
        dampingFactor={0.05}
        enableDamping
      />
    </>
  );
};

// ==================== MAIN COMPONENT ====================

const VectorViewerProjector: React.FC = () => {
  // Estado principal
  const [vectors, setVectors] = useState<MemoryVector[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<VectorStats | null>(null);
  
  // Estado de selección
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<string[]>([]);
  
  // Filtros y opciones
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTipo, setFilterTipo] = useState<'all' | 'paciente' | 'doctor'>('all');
  const [filterCategoria, setFilterCategoria] = useState<string>('all');
  const [colorMode, setColorMode] = useState<'tipo' | 'categoria'>('tipo');
  const [showFilters, setShowFilters] = useState(false);
  
  const backendUrl = getBackendUrl();

  // Cargar vectores
  const loadVectors = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      params.append('limit', '500');
      if (filterTipo !== 'all') params.append('tipo_usuario', filterTipo);
      if (filterCategoria !== 'all') params.append('categoria', filterCategoria);
      
      const response = await fetch(`${backendUrl}/api/database/memory-vectors?${params}`);
      const data = await response.json();
      
      if (data.success && data.vectors?.length > 0) {
        setVectors(data.vectors);
        setStats({
          total: data.total,
          pacientes: data.tipos?.pacientes || 0,
          doctores: data.tipos?.doctores || 0,
          grupos: data.grupos || {}
        });
      } else {
        setVectors([]);
        setStats({ total: 0, pacientes: 0, doctores: 0, grupos: {} });
        setError(data.message || 'No hay memorias episódicas. Inicia conversaciones para generar vectores.');
      }
    } catch (err) {
      setError(`Error de conexión: ${err}`);
      setVectors([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVectors();
  }, [filterTipo, filterCategoria]);

  // Cuando se selecciona un vector, cargar vectores relacionados
  const handleSelectVector = useCallback(async (id: string | null) => {
    setSelectedId(id);
    
    if (id) {
      const vector = vectors.find(v => v.id === id);
      if (vector) {
        // Resaltar todos los vectores del mismo usuario
        const sameUser = vectors.filter(v => v.user_id === vector.user_id).map(v => v.id);
        setHighlightedIds(sameUser);
        setSelectedGroup(vector.grupo_visual);
        
        // Cargar vecinos semánticos
        try {
          const response = await fetch(`${backendUrl}/api/database/user-vectors/${vector.user_id}?include_neighbors=true`);
          const data = await response.json();
          if (data.success) {
            setHighlightedIds([...data.user_vectors, ...data.neighbor_vectors]);
          }
        } catch (e) {
          console.warn('No se pudieron cargar vecinos:', e);
        }
      }
    } else {
      setHighlightedIds([]);
      setSelectedGroup(null);
    }
  }, [vectors, backendUrl]);

  // Filtrar vectores por búsqueda
  const filteredVectors = useMemo(() => {
    if (!searchQuery.trim()) return vectors;
    const query = searchQuery.toLowerCase();
    return vectors.filter(v => 
      v.resumen.toLowerCase().includes(query) ||
      v.nombre_usuario.toLowerCase().includes(query) ||
      v.user_id.toLowerCase().includes(query)
    );
  }, [vectors, searchQuery]);

  // Vector seleccionado
  const selectedVector = useMemo(() => 
    vectors.find(v => v.id === selectedId),
    [vectors, selectedId]
  );

  // Categorías únicas
  const categorias = useMemo(() => 
    [...new Set(vectors.map(v => v.categoria))].sort(),
    [vectors]
  );

  // Grupos/Usuarios únicos
  const grupos = useMemo(() => 
    [...new Set(vectors.map(v => v.grupo_visual))],
    [vectors]
  );

  return (
    <div className="h-full flex bg-gray-950">
      {/* Panel izquierdo - Controles estilo TensorFlow Projector */}
      <div className="w-72 bg-gray-900 border-r border-gray-700 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <Users size={18} />
            </div>
            Embedding Projector
          </h2>
          <p className="text-xs text-gray-400 mt-1">
            Memoria Episódica • {stats?.total || 0} vectores
          </p>
        </div>
        
        {/* Stats */}
        <div className="p-3 border-b border-gray-700 grid grid-cols-2 gap-2">
          <div className="bg-blue-900/30 rounded-lg p-2 text-center">
            <div className="text-xl font-bold text-blue-400">{stats?.pacientes || 0}</div>
            <div className="text-[10px] text-gray-400">Pacientes</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-2 text-center">
            <div className="text-xl font-bold text-white">{stats?.doctores || 0}</div>
            <div className="text-[10px] text-gray-400">Doctores</div>
          </div>
        </div>
        
        {/* Search */}
        <div className="p-3 border-b border-gray-700">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
            <input
              type="text"
              placeholder="Buscar resúmenes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>
        
        {/* Color Mode */}
        <div className="p-3 border-b border-gray-700">
          <label className="text-xs text-gray-400 mb-2 block">Colorear por</label>
          <div className="flex gap-2">
            <button
              onClick={() => setColorMode('tipo')}
              className={`flex-1 py-1.5 px-2 rounded text-xs font-medium transition-colors ${
                colorMode === 'tipo' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <User size={12} className="inline mr-1" />
              Tipo Usuario
            </button>
            <button
              onClick={() => setColorMode('categoria')}
              className={`flex-1 py-1.5 px-2 rounded text-xs font-medium transition-colors ${
                colorMode === 'categoria' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <Tag size={12} className="inline mr-1" />
              Categoría
            </button>
          </div>
        </div>
        
        {/* Filters */}
        <div className="p-3 border-b border-gray-700">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center justify-between w-full text-xs text-gray-400 hover:text-white"
          >
            <span className="flex items-center gap-1">
              <Filter size={12} />
              Filtros
            </span>
            <ChevronDown size={14} className={`transition-transform ${showFilters ? 'rotate-180' : ''}`} />
          </button>
          
          {showFilters && (
            <div className="mt-3 space-y-3">
              {/* Filtro tipo usuario */}
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Tipo Usuario</label>
                <select
                  value={filterTipo}
                  onChange={(e) => setFilterTipo(e.target.value as any)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white"
                >
                  <option value="all">Todos</option>
                  <option value="paciente">🔵 Pacientes</option>
                  <option value="doctor">⚪ Doctores</option>
                </select>
              </div>
              
              {/* Filtro categoría */}
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Categoría</label>
                <select
                  value={filterCategoria}
                  onChange={(e) => setFilterCategoria(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-white"
                >
                  <option value="all">Todas</option>
                  {categorias.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
        
        {/* Legend */}
        <div className="p-3 border-b border-gray-700">
          <label className="text-xs text-gray-400 mb-2 block">Leyenda</label>
          {colorMode === 'tipo' ? (
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-xs text-gray-300">Paciente</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-white" />
                <span className="text-xs text-gray-300">Doctor</span>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-1">
              {Object.entries(CATEGORIA_COLORS).map(([cat, color]) => (
                <div key={cat} className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-[10px] text-gray-400 capitalize">{cat}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Usuarios/Grupos */}
        <div className="flex-1 overflow-y-auto p-3">
          <label className="text-xs text-gray-400 mb-2 block flex items-center justify-between">
            <span>Usuarios ({grupos.length})</span>
            {selectedGroup && (
              <button 
                onClick={() => { setSelectedGroup(null); setHighlightedIds([]); setSelectedId(null); }}
                className="text-blue-400 hover:text-blue-300"
              >
                Limpiar
              </button>
            )}
          </label>
          <div className="space-y-1">
            {grupos.slice(0, 20).map(grupo => {
              const count = vectors.filter(v => v.grupo_visual === grupo).length;
              const isActive = selectedGroup === grupo;
              return (
                <button
                  key={grupo}
                  onClick={() => {
                    if (isActive) {
                      setSelectedGroup(null);
                      setHighlightedIds([]);
                    } else {
                      setSelectedGroup(grupo);
                      setHighlightedIds(vectors.filter(v => v.grupo_visual === grupo).map(v => v.id));
                    }
                  }}
                  className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                    isActive 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-800/50 text-gray-400 hover:bg-gray-800 hover:text-gray-300'
                  }`}
                >
                  <span className="truncate block">{grupo.slice(0, 20)}...</span>
                  <span className="text-[10px] opacity-60">{count} vectores</span>
                </button>
              );
            })}
          </div>
        </div>
        
        {/* Actions */}
        <div className="p-3 border-t border-gray-700">
          <button
            onClick={loadVectors}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-gray-800 hover:bg-gray-700 text-white py-2 px-3 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Recargar
          </button>
        </div>
      </div>
      
      {/* Área principal - Canvas 3D */}
      <div className="flex-1 relative">
        {loading ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950">
            <div className="text-center">
              <Loader2 size={48} className="animate-spin text-blue-500 mx-auto mb-4" />
              <p className="text-gray-400">Cargando vectores...</p>
            </div>
          </div>
        ) : error && vectors.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950">
            <div className="text-center max-w-md p-6">
              <Info size={48} className="text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">{error}</p>
              <button
                onClick={loadVectors}
                className="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm"
              >
                Reintentar
              </button>
            </div>
          </div>
        ) : (
          <>
            <Canvas
              camera={{ position: [80, 60, 80], fov: 50 }}
              style={{ background: 'linear-gradient(to bottom, #0f172a, #020617)' }}
            >
              <Scene
                vectors={filteredVectors}
                selectedId={selectedId}
                highlightedIds={highlightedIds}
                selectedGroup={selectedGroup}
                onSelectVector={handleSelectVector}
                colorMode={colorMode}
              />
            </Canvas>
            
            {/* Info overlay */}
            <div className="absolute top-4 left-4 bg-gray-900/80 backdrop-blur rounded-lg px-3 py-2 text-xs text-gray-400">
              <span className="text-white font-medium">{filteredVectors.length}</span> vectores
              {searchQuery && <span className="ml-2">• Buscando: "{searchQuery}"</span>}
            </div>
            
            {/* Controls hint */}
            <div className="absolute bottom-4 left-4 bg-gray-900/60 backdrop-blur rounded-lg px-3 py-2 text-[10px] text-gray-500 flex gap-4">
              <span>🖱️ Click: Rotar</span>
              <span>🖱️ Derecho: Pan</span>
              <span>⚙️ Scroll: Zoom</span>
            </div>
          </>
        )}
        
        {/* Panel de detalles del vector seleccionado */}
        {selectedVector && (
          <div className="absolute top-4 right-4 w-96 bg-gray-900/95 backdrop-blur border border-gray-700 rounded-xl shadow-2xl max-h-[80vh] overflow-hidden flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gradient-to-r from-gray-800 to-gray-900">
              <div className="flex items-center gap-3">
                <div 
                  className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                  style={{ backgroundColor: selectedVector.tipo_usuario === 'paciente' ? '#3b82f6' : '#ffffff' }}
                >
                  {selectedVector.tipo_usuario === 'paciente' ? '👤' : '🩺'}
                </div>
                <div>
                  <h3 className="text-white font-semibold text-sm">{selectedVector.nombre_usuario}</h3>
                  <p className="text-gray-400 text-[10px]">
                    Vector #{selectedVector.vector_number} • {selectedVector.tipo_usuario}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleSelectVector(null)}
                className="text-gray-400 hover:text-white p-1.5 hover:bg-gray-700 rounded-full"
              >
                <X size={18} />
              </button>
            </div>
            
            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {/* Categoría y fecha */}
              <div className="flex items-center gap-2 flex-wrap">
                <span 
                  className="px-2 py-1 rounded-full text-xs font-medium"
                  style={{ 
                    backgroundColor: `${CATEGORIA_COLORS[selectedVector.categoria]}20`,
                    color: CATEGORIA_COLORS[selectedVector.categoria]
                  }}
                >
                  {selectedVector.categoria}
                </span>
                {selectedVector.fecha_evento && (
                  <span className="flex items-center gap-1 text-xs text-blue-400">
                    <Calendar size={12} />
                    {selectedVector.fecha_evento}
                  </span>
                )}
              </div>
              
              {/* Resumen completo */}
              <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                <label className="text-[10px] text-gray-500 uppercase tracking-wide mb-1 block">Resumen</label>
                <p className="text-gray-200 text-sm leading-relaxed">{selectedVector.resumen}</p>
              </div>
              
              {/* Metadata */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-gray-800/30 rounded-lg p-2">
                  <label className="text-gray-500 text-[10px]">ID Usuario</label>
                  <p className="text-gray-300 font-mono truncate">{selectedVector.user_id}</p>
                </div>
                <div className="bg-gray-800/30 rounded-lg p-2">
                  <label className="text-gray-500 text-[10px]">Grupo Visual</label>
                  <p className="text-gray-300 font-mono truncate">{selectedVector.grupo_visual}</p>
                </div>
                <div className="bg-gray-800/30 rounded-lg p-2">
                  <label className="text-gray-500 text-[10px]">Posición 3D</label>
                  <p className="text-cyan-400 font-mono">
                    ({selectedVector.x.toFixed(1)}, {selectedVector.y.toFixed(1)}, {selectedVector.z.toFixed(1)})
                  </p>
                </div>
                {selectedVector.timestamp && (
                  <div className="bg-gray-800/30 rounded-lg p-2">
                    <label className="text-gray-500 text-[10px]">Timestamp</label>
                    <p className="text-gray-300 text-[11px]">{new Date(selectedVector.timestamp).toLocaleString()}</p>
                  </div>
                )}
              </div>
              
              {/* Vectores relacionados */}
              <div>
                <label className="text-xs text-gray-400 mb-2 block">
                  Vectores del mismo usuario ({highlightedIds.filter(id => id !== selectedVector.id).length})
                </label>
                <div className="flex flex-wrap gap-1">
                  {highlightedIds.slice(0, 10).map(id => {
                    if (id === selectedVector.id) return null;
                    const v = vectors.find(vec => vec.id === id);
                    if (!v) return null;
                    return (
                      <button
                        key={id}
                        onClick={() => handleSelectVector(id)}
                        className="px-2 py-1 bg-gray-800 hover:bg-gray-700 rounded text-[10px] text-gray-400 hover:text-white transition-colors"
                      >
                        #{v.vector_number}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VectorViewerProjector;
