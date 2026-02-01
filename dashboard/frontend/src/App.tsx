import React, { useEffect, useState } from 'react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import { useWebSocket } from './hooks/useWebSocket';
import LogPanel from './components/LogPanel';
import StatsPanel from './components/StatsPanel';
import { Play, Pause, RotateCcw } from 'lucide-react';

interface Node {
  id: string;
  label: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  duration_ms?: number;
}

function App() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const { logs, connected, currentExecution } = useWebSocket('http://localhost:8000');

  // Cargar estructura del grafo
  useEffect(() => {
    fetch('http://localhost:8000/api/graph')
      .then(res => res.json())
      .then(data => {
        // Convertir a formato React Flow
        const reactFlowNodes = data.nodes.map((node: any) => ({
          id: node.id,
          position: node.position,
          data: { 
            label: node.label,
            status: 'idle',
            duration_ms: null
          },
          type: 'default',
          style: getNodeStyle('idle')
        }));
        
        const reactFlowEdges = data.edges.map((edge: any, i: number) => ({
          id: `e${i}`,
          source: edge.source,
          target: edge.target,
          animated: false
        }));
        
        setNodes(reactFlowNodes);
        setEdges(reactFlowEdges);
      });
  }, []);

  // Actualizar estados de nodos según logs
  useEffect(() => {
    if (currentExecution) {
      setNodes(prev => prev.map(node => {
        const execution = currentExecution.nodes[node.id];
        if (execution) {
          return {
            ...node,
            data: {
              ...node.data,
              status: execution.status,
              duration_ms: execution.duration_ms
            },
            style: getNodeStyle(execution.status)
          };
        }
        return node;
      }));
    }
  }, [currentExecution]);

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              WhatsApp Agent Dashboard
            </h1>
            <p className="text-gray-400 text-sm">
              {connected ? '🟢 Conectado' : '🔴 Desconectado'}
            </p>
          </div>
          
          <div className="flex gap-2">
            <button className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded flex items-center gap-2">
              <Play size={16} />
              Iniciar
            </button>
            <button className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded flex items-center gap-2">
              <Pause size={16} />
              Pausar
            </button>
            <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex items-center gap-2">
              <RotateCcw size={16} />
              Reset
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
            fitView
            className="bg-gray-900"
          >
            <Background color="#374151" />
            <Controls className="bg-gray-800 border-gray-700" />
          </ReactFlow>
        </div>

        {/* Sidebar */}
        <div className="w-96 bg-gray-800 border-l border-gray-700 flex flex-col">
          <StatsPanel execution={currentExecution} />
          <LogPanel logs={logs} />
        </div>
      </div>
    </div>
  );
}

function getNodeStyle(status: string) {
  const baseStyle = {
    padding: '10px 20px',
    borderRadius: '8px',
    border: '2px solid',
    fontSize: '12px',
    fontWeight: '600'
  };

  switch (status) {
    case 'running':
      return { ...baseStyle, background: '#3b82f6', borderColor: '#60a5fa', color: 'white' };
    case 'completed':
      return { ...baseStyle, background: '#10b981', borderColor: '#34d399', color: 'white' };
    case 'error':
      return { ...baseStyle, background: '#ef4444', borderColor: '#f87171', color: 'white' };
    default:
      return { ...baseStyle, background: '#374151', borderColor: '#4b5563', color: '#9ca3af' };
  }
}

export default App;
