import { useState } from 'react';

interface Log {
  timestamp: string;
  level: string;
  message: string;
  node_id?: string;
  execution_id: string;
  user_type?: 'doctor' | 'patient' | 'unknown';
}

interface Execution {
  id: string;
  execution_id?: string;
  start_time: string;
  nodes: Record<string, { status: string; duration_ms?: number; timestamp: string }>;
  logs: Log[];
  user_type?: 'doctor' | 'patient' | 'unknown';
}

/**
 * Hook deshabilitado - Socket.IO no está configurado en el backend.
 * Cuando se implemente WebSocket en el backend, descomentar la lógica de conexión.
 */
export function useWebSocket(_url: string) {
  const [connected] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [currentExecution, setCurrentExecution] = useState<Execution | null>(null);

  // Socket.IO deshabilitado - el backend usa REST API en lugar de WebSockets
  // Para reactivar, implementar socket.io-server en el backend

  const clearLogs = () => {
    setLogs([]);
    setCurrentExecution(null);
  };

  return { socket: null, connected, logs, currentExecution, clearLogs };
}
