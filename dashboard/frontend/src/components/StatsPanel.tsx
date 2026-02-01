import React from 'react';

interface Execution {
  id: string;
  start_time: string;
  nodes: Record<string, {
    status: string;
    duration_ms?: number;
    timestamp: string;
  }>;
}

interface StatsPanelProps {
  execution: Execution | null;
}

export default function StatsPanel({ execution }: StatsPanelProps) {
  const completedNodes = execution 
    ? Object.values(execution.nodes).filter(n => n.status === 'completed').length
    : 0;
  
  const totalNodes = execution ? Object.keys(execution.nodes).length : 0;
  
  const avgDuration = execution 
    ? Object.values(execution.nodes)
        .filter(n => n.duration_ms)
        .reduce((acc, n) => acc + (n.duration_ms || 0), 0) / (completedNodes || 1)
    : 0;

  return (
    <div className="p-4 border-b border-gray-700">
      <h3 className="text-white font-semibold mb-3">Estadísticas</h3>
      
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-gray-900 p-3 rounded">
          <div className="text-gray-400">Nodos Completados</div>
          <div className="text-white text-xl font-bold">{completedNodes}/{totalNodes}</div>
        </div>
        
        <div className="bg-gray-900 p-3 rounded">
          <div className="text-gray-400">Tiempo Promedio</div>
          <div className="text-white text-xl font-bold">{avgDuration.toFixed(0)}ms</div>
        </div>
      </div>
    </div>
  );
}
