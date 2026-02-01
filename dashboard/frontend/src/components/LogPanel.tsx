import React from 'react';
import { format } from 'date-fns';

interface Log {
  timestamp: string;
  level: string;
  message: string;
  node_id?: string;
}

interface LogPanelProps {
  logs: Log[];
}

export default function LogPanel({ logs }: LogPanelProps) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-white font-semibold">Logs en Tiempo Real</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-xs">
        {logs.map((log, i) => (
          <div 
            key={i}
            className={`p-2 rounded ${getLevelColor(log.level)}`}
          >
            <div className="flex items-center gap-2">
              <span className="text-gray-400">
                {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
              </span>
              {log.node_id && (
                <span className="bg-blue-600 px-2 py-0.5 rounded text-white">
                  {log.node_id.toUpperCase()}
                </span>
              )}
              <span className={getLevelBadge(log.level)}>
                {log.level}
              </span>
            </div>
            <div className="mt-1 text-gray-300">
              {log.message}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getLevelColor(level: string) {
  switch (level) {
    case 'ERROR':
      return 'bg-red-900/50 border border-red-700';
    case 'WARNING':
      return 'bg-yellow-900/50 border border-yellow-700';
    case 'INFO':
      return 'bg-blue-900/50 border border-blue-700';
    default:
      return 'bg-gray-800 border border-gray-700';
  }
}

function getLevelBadge(level: string) {
  const base = 'px-2 py-0.5 rounded text-xs font-semibold';
  switch (level) {
    case 'ERROR':
      return `${base} bg-red-600 text-white`;
    case 'WARNING':
      return `${base} bg-yellow-600 text-white`;
    case 'INFO':
      return `${base} bg-green-600 text-white`;
    default:
      return `${base} bg-gray-600 text-white`;
  }
}
