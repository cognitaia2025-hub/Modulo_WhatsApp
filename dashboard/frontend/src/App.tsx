import { useEffect, useState, useCallback } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MarkerType,
  useNodesState,
  useEdgesState,
  MiniMap
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWebSocket } from './hooks/useWebSocket';
import VerboseNode, { nodeDescriptions } from './components/VerboseNode';
import DatabaseNode from './components/DatabaseNode';
import LLMNode from './components/LLMNode';
import ToolNode from './components/ToolNode';
import ServiceNode from './components/ServiceNode';
import TestChatbot from './components/TestChatbot';
import DatabaseView from './components/DatabaseView';
import { Play, Pause, RotateCcw, Save, RefreshCw, GitBranch, Database } from 'lucide-react';

// Tipos de pestañas principales
type MainTab = 'workflow' | 'database';

// Registrar todos los tipos de nodos custom
const nodeTypes = {
  verbose: VerboseNode,
  database: DatabaseNode,
  llm: LLMNode,
  tool: ToolNode,
  service: ServiceNode,
};

interface NodeDescription {
  title: string;
  description: string;
  timestamp?: string;
  duration_ms?: number;
  details?: string[];
}

// Detectar URL del backend (Codespaces o localhost)
const getBackendUrl = () => {
  if (window.location.hostname.includes('github.dev')) {
    return window.location.origin.replace('-3000.', '-8000.');
  }
  return 'http://localhost:8000';
};

// Mapeo de tipo de edge a estilos
const getEdgeStyle = (edgeType: string) => {
  switch (edgeType) {
    case 'flow':
      return { stroke: '#6b7280', strokeWidth: 2 };
    case 'conditional':
      return { stroke: '#f59e0b', strokeWidth: 2, strokeDasharray: '5,5' };
    case 'data':
      return { stroke: '#10b981', strokeWidth: 1.5, strokeDasharray: '3,3' };
    case 'api':
      return { stroke: '#8b5cf6', strokeWidth: 1.5 };
    case 'fallback':
      return { stroke: '#ef4444', strokeWidth: 1, strokeDasharray: '2,4' };
    default:
      return { stroke: '#6b7280', strokeWidth: 2 };
  }
};

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [userType, setUserType] = useState<'doctor' | 'patient' | 'unknown'>('unknown');
  const [nodeDescriptionsState, setNodeDescriptionsState] = useState<Record<string, NodeDescription[]>>({});
  const [isPaused, setIsPaused] = useState(false);
  const [layoutSaved, setLayoutSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<MainTab>('workflow');
  const [backendConnected, setBackendConnected] = useState(false);
  
  const backendUrl = getBackendUrl();
  const { logs, currentExecution } = useWebSocket(backendUrl);

  // Verificar conexión con el backend via REST
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/graph`);
        setBackendConnected(res.ok);
      } catch {
        setBackendConnected(false);
      }
    };
    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Verificar cada 30s
    return () => clearInterval(interval);
  }, [backendUrl]);

  // Clave para localStorage
  const LAYOUT_STORAGE_KEY = 'whatsapp-dashboard-node-positions';

  // Guardar posiciones de nodos
  const handleSaveLayout = useCallback(() => {
    const positions: Record<string, { x: number; y: number }> = {};
    nodes.forEach(node => {
      positions[node.id] = node.position;
    });
    localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(positions));
    setLayoutSaved(true);
    setTimeout(() => setLayoutSaved(false), 2000);
  }, [nodes]);

  // Resetear a posiciones originales del servidor
  const handleResetLayout = useCallback(() => {
    localStorage.removeItem(LAYOUT_STORAGE_KEY);
    window.location.reload();
  }, []);

  // Cargar estructura del grafo
  useEffect(() => {
    fetch(`${backendUrl}/api/graph`)
      .then(res => res.json())
      .then(data => {
        // Intentar cargar posiciones guardadas
        const savedPositions = localStorage.getItem(LAYOUT_STORAGE_KEY);
        const positions: Record<string, { x: number; y: number }> = savedPositions 
          ? JSON.parse(savedPositions) 
          : {};

        const reactFlowNodes = data.nodes.map((node: any) => {
          // Determinar el tipo de nodo basado en la categoría
          let nodeType = 'verbose';
          if (node.type === 'database') nodeType = 'database';
          else if (node.type === 'llm') nodeType = 'llm';
          else if (node.type === 'tool') nodeType = 'tool';
          else if (node.type === 'service') nodeType = 'service';
          
          // Usar posición guardada si existe, sino la del servidor
          const position = positions[node.id] || node.position;
          
          return {
            id: node.id,
            position: position,
            data: { 
              label: node.label,
              status: 'idle',
              duration_ms: null,
              userType: 'unknown',
              descriptions: [],
              category: node.category
            },
            type: nodeType,
          };
        });
        
        const reactFlowEdges = data.edges.map((edge: any, i: number) => {
          const style = getEdgeStyle(edge.type);
          return {
            id: `e${i}`,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            animated: edge.type === 'flow',
            style: style,
            labelStyle: { fill: '#9ca3af', fontSize: 10 },
            labelBgStyle: { fill: '#1f2937', fillOpacity: 0.8 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: style.stroke,
            },
          };
        });
        
        setNodes(reactFlowNodes);
        setEdges(reactFlowEdges);
      })
      .catch(err => console.error('Error cargando grafo:', err));
  }, [backendUrl]);

  // Detectar tipo de usuario desde los logs
  useEffect(() => {
    if (isPaused) return;
    
    const lastLogs = logs.slice(-20);
    for (const log of lastLogs) {
      const msg = log.message.toLowerCase();
      if (msg.includes('doctor') || msg.includes('médico') || msg.includes('n2b')) {
        setUserType('doctor');
        break;
      } else if (msg.includes('paciente') || msg.includes('patient') || msg.includes('n2a') || msg.includes('usuario')) {
        setUserType('patient');
        break;
      }
    }
  }, [logs, isPaused]);

  // Actualizar colores de edges según tipo de usuario
  useEffect(() => {
    if (userType === 'unknown') return;

    const edgeColor = userType === 'doctor' ? '#ffffff' : '#3b82f6'; // Blanco para doctor, azul para paciente
    
    // Nodos que corresponden a cada flujo
    const doctorPath = ['n0', 'n1', 'n2', 'n2b', 'n3b', 'n4', 'n5b', 'n6', 'n7'];
    const patientPath = ['n0', 'n1', 'n2', 'n2a', 'n3a', 'n4', 'n5a', 'n6', 'n7'];
    const activePath = userType === 'doctor' ? doctorPath : patientPath;

    setEdges(prevEdges => prevEdges.map(edge => {
      // Verificar si este edge está en el camino activo
      const sourceInPath = activePath.includes(edge.source);
      const targetInPath = activePath.includes(edge.target);
      const isActivePath = sourceInPath && targetInPath;

      if (isActivePath) {
        return {
          ...edge,
          animated: true,
          style: { 
            stroke: edgeColor, 
            strokeWidth: 3,
            filter: userType === 'doctor' ? 'drop-shadow(0 0 4px white)' : 'drop-shadow(0 0 4px #3b82f6)'
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: edgeColor,
          },
        };
      }
      return {
        ...edge,
        animated: false,
        style: { stroke: '#6b7280', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#6b7280',
        },
      };
    }));
  }, [userType, setEdges]);

  // Actualizar estados de nodos y agregar descripciones
  useEffect(() => {
    if (isPaused || !currentExecution) return;

    setNodes(prevNodes => prevNodes.map(node => {
      const execution = currentExecution.nodes?.[node.id];
      
      if (execution) {
        // Agregar nueva descripción si el estado cambió
        const newDescriptions = [...(nodeDescriptionsState[node.id] || [])];
        
        if (execution.status === 'running' || execution.status === 'completed') {
          const descriptionFn = nodeDescriptions[node.id];
          const descText = descriptionFn ? descriptionFn(userType) : `Procesando ${node.data.label}...`;
          
          // Solo agregar si no existe ya una descripción con el mismo timestamp
          const exists = newDescriptions.some(d => d.timestamp === execution.timestamp);
          if (!exists) {
            newDescriptions.push({
              title: execution.status === 'running' ? '⏳ Ejecutando...' : '✅ Completado',
              description: descText,
              timestamp: execution.timestamp,
              duration_ms: execution.duration_ms,
            });
            
            // Actualizar estado global de descripciones
            setNodeDescriptionsState(prev => ({
              ...prev,
              [node.id]: newDescriptions
            }));
          }
        }

        return {
          ...node,
          data: {
            ...node.data,
            status: execution.status,
            duration_ms: execution.duration_ms,
            userType: userType,
            descriptions: newDescriptions.slice(-5), // Mantener últimas 5
          },
        };
      }
      
      return {
        ...node,
        data: {
          ...node.data,
          descriptions: nodeDescriptionsState[node.id] || [],
        }
      };
    }));
  }, [currentExecution, userType, isPaused]);

  // Handlers para botones
  const handleReset = useCallback(() => {
    setUserType('unknown');
    setNodeDescriptionsState({});
    setNodes(prevNodes => prevNodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        status: 'idle',
        duration_ms: null,
        userType: 'unknown',
        descriptions: [],
      }
    })));
    setEdges(prevEdges => prevEdges.map(edge => ({
      ...edge,
      animated: false,
      style: { stroke: '#6b7280', strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#6b7280',
      },
    })));
  }, [setNodes, setEdges]);

  const handlePause = useCallback(() => {
    setIsPaused(prev => !prev);
  }, []);

  // Calcular estadísticas
  const completedNodes = currentExecution 
    ? Object.values(currentExecution.nodes).filter(n => n.status === 'completed').length
    : 0;
  const totalNodes = currentExecution ? Object.keys(currentExecution.nodes).length : 0;
  const avgDuration = currentExecution 
    ? Object.values(currentExecution.nodes)
        .filter(n => n.duration_ms)
        .reduce((acc, n) => acc + (n.duration_ms || 0), 0) / (completedNodes || 1)
    : 0;

  // Tabs de navegación principal
  const mainTabs: { id: MainTab; label: string; icon: React.ReactNode }[] = [
    { id: 'workflow', label: 'Workflow', icon: <GitBranch size={18} /> },
    { id: 'database', label: 'Database', icon: <Database size={18} /> },
  ];

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Tab Navigation Bar */}
      <nav className="bg-gray-950 border-b border-gray-800">
        <div className="flex items-center justify-between px-4">
          <div className="flex items-center">
            {/* Logo/Title */}
            <div className="flex items-center gap-3 pr-6 border-r border-gray-800">
              <span className="text-2xl">🤖</span>
              <span className="text-white font-bold">WhatsApp Agent</span>
            </div>
            
            {/* Main Tabs */}
            <div className="flex">
              {mainTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-6 py-3.5 text-sm font-medium transition-colors relative ${
                    activeTab === tab.id
                      ? 'text-white bg-gray-900'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-900/50'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                  {activeTab === tab.id && (
                    <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
                  )}
                </button>
              ))}
            </div>
          </div>
          
          {/* Connection Status */}
          <div className="flex items-center gap-3">
            <span className={`text-xs px-2 py-1 rounded ${
              backendConnected 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {backendConnected ? '🟢 Connected' : '🔴 Disconnected'}
            </span>
          </div>
        </div>
      </nav>

      {/* Content based on active tab */}
      {activeTab === 'workflow' ? (
        <>
          {/* Workflow Header */}
          <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div>
                  <h1 className="text-lg font-semibold text-white">
                    Agent Workflow Monitor
                  </h1>
                  <div className="flex items-center gap-3 mt-1">
                    {userType !== 'unknown' && (
                      <span className={`text-xs px-2 py-1 rounded ${
                        userType === 'doctor' 
                          ? 'bg-white/20 text-white border border-white/50' 
                          : 'bg-blue-500/20 text-blue-300 border border-blue-500/50'
                      }`}>
                        {userType === 'doctor' ? '👨‍⚕️ Doctor' : '👤 Paciente'}
                      </span>
                    )}
                    {isPaused && (
                      <span className="text-xs px-2 py-1 rounded bg-yellow-500/20 text-yellow-300 border border-yellow-500/50">
                        ⏸️ Pausado
                      </span>
                    )}
                  </div>
                </div>
                
                {/* Estadísticas en el header */}
                <div className="flex items-center gap-4 ml-4 pl-4 border-l border-gray-600">
                  <div className="text-center">
                    <div className="text-xs text-gray-400">Nodos</div>
                    <div className="text-lg font-bold text-white">{completedNodes}/{totalNodes}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-gray-400">Tiempo</div>
                    <div className="text-lg font-bold text-green-400">{avgDuration.toFixed(0)}ms</div>
                  </div>
                </div>
              </div>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => setIsPaused(false)}
                  className={`px-3 py-2 rounded flex items-center gap-2 transition-colors text-sm ${
                    !isPaused 
                      ? 'bg-green-600 text-white' 
                      : 'bg-gray-700 hover:bg-green-600 text-white'
                  }`}
                >
                  <Play size={14} />
                  Iniciar
                </button>
                <button 
                  onClick={handlePause}
                  className={`px-3 py-2 rounded flex items-center gap-2 transition-colors text-sm ${
                    isPaused 
                      ? 'bg-yellow-600 text-white' 
                      : 'bg-gray-700 hover:bg-yellow-600 text-white'
                  }`}
                >
                  <Pause size={14} />
              Pausar
            </button>
            <button 
              onClick={handleReset}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded flex items-center gap-2 text-sm"
            >
              <RotateCcw size={14} />
              Reset
            </button>
            
            {/* Separador */}
            <div className="w-px h-8 bg-gray-600 mx-1"></div>
            
            {/* Botones de Layout */}
            <button 
              onClick={handleSaveLayout}
              className={`px-3 py-2 rounded flex items-center gap-2 transition-colors text-sm ${
                layoutSaved 
                  ? 'bg-green-600 text-white' 
                  : 'bg-purple-600 hover:bg-purple-700 text-white'
              }`}
            >
              <Save size={14} />
              {layoutSaved ? '¡Guardado!' : 'Guardar Layout'}
            </button>
            <button 
              onClick={handleResetLayout}
              className="bg-gray-600 hover:bg-gray-500 text-white px-3 py-2 rounded flex items-center gap-2 text-sm"
              title="Restaurar posiciones originales"
            >
              <RefreshCw size={14} />
              Reset Layout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph Visualization */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2, maxZoom: 0.8 }}
            minZoom={0.2}
            maxZoom={2}
            snapToGrid={true}
            snapGrid={[25, 25]}
            nodesDraggable={true}
            nodesConnectable={false}
            elementsSelectable={true}
            panOnDrag={true}
            zoomOnScroll={true}
            className="bg-gray-900"
          >
            <Background color="#374151" gap={25} size={1} />
            <Controls className="bg-gray-800 border-gray-700" />
            <MiniMap 
              nodeColor={(node) => {
                switch (node.type) {
                  case 'database': return '#10b981';
                  case 'llm': return '#8b5cf6';
                  case 'tool': return '#f59e0b';
                  case 'service': return '#06b6d4';
                  default: return '#6b7280';
                }
              }}
              maskColor="rgba(0,0,0,0.8)"
              className="bg-gray-800 border border-gray-700"
              pannable={true}
              zoomable={true}
            />
          </ReactFlow>
          
          {/* Leyenda completa */}
          <div className="absolute bottom-4 left-4 bg-gray-800/95 p-4 rounded-lg border border-gray-700 max-w-md">
            <p className="text-xs text-gray-400 mb-3 font-semibold">📊 Leyenda del Sistema</p>
            
            {/* Tipos de Nodos */}
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-2">Componentes:</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-gray-600 border border-gray-500"></div>
                  <span className="text-xs text-gray-300">Nodos Proceso</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-emerald-600 border border-emerald-500"></div>
                  <span className="text-xs text-emerald-300">Base de Datos</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-violet-600 border border-violet-500"></div>
                  <span className="text-xs text-violet-300">LLM / IA</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded bg-orange-600 border border-orange-500"></div>
                  <span className="text-xs text-orange-300">Herramientas</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 rounded-full bg-cyan-600 border border-cyan-500"></div>
                  <span className="text-xs text-cyan-300">Servicios</span>
                </div>
              </div>
            </div>
            
            {/* Tipos de Conexiones */}
            <div className="mb-3">
              <p className="text-xs text-gray-500 mb-2">Conexiones:</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 bg-gray-400"></div>
                  <span className="text-xs text-gray-300">Flujo</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 bg-amber-400" style={{backgroundImage: 'repeating-linear-gradient(90deg, #f59e0b 0, #f59e0b 5px, transparent 5px, transparent 10px)'}}></div>
                  <span className="text-xs text-amber-300">Condicional</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 bg-emerald-400" style={{backgroundImage: 'repeating-linear-gradient(90deg, #10b981 0, #10b981 3px, transparent 3px, transparent 6px)'}}></div>
                  <span className="text-xs text-emerald-300">Datos</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-0.5 bg-violet-400"></div>
                  <span className="text-xs text-violet-300">API</span>
                </div>
              </div>
            </div>
            
            {/* Flujos de Usuario */}
            <div>
              <p className="text-xs text-gray-500 mb-2">Flujo Activo:</p>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-1 bg-white rounded shadow-[0_0_6px_white]"></div>
                  <span className="text-xs text-white">Doctor</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-6 h-1 bg-blue-500 rounded shadow-[0_0_6px_#3b82f6]"></div>
                  <span className="text-xs text-blue-400">Paciente</span>
                </div>
              </div>
            </div>
          </div>
          
          {/* Test Chatbot - Al lado de la leyenda */}
          <div className="absolute bottom-4 left-[440px]">
            <TestChatbot />
          </div>
        </div>
      </div>
        </>
      ) : (
        /* Database View */
        <DatabaseView />
      )}
    </div>
  );
}

export default App;
