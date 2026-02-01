import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface Log {
  timestamp: string;
  level: string;
  message: string;
  node_id?: string;
  execution_id: string;
}

interface Execution {
  id: string;
  start_time: string;
  nodes: Record<string, {
    status: string;
    duration_ms?: number;
    timestamp: string;
  }>;
  logs: Log[];
}

export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connected, setConnected] = useState(false);
  const [logs, setLogs] = useState<Log[]>([]);
  const [currentExecution, setCurrentExecution] = useState<Execution | null>(null);

  useEffect(() => {
    const newSocket = io(url);

    newSocket.on('connect', () => {
      console.log('✅ Conectado al dashboard backend');
      setConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('❌ Desconectado del dashboard backend');
      setConnected(false);
    });

    newSocket.on('log', (log: Log) => {
      setLogs(prev => [...prev.slice(-100), log]); // Mantener últimos 100
    });

    newSocket.on('execution_update', (execution: Execution) => {
      setCurrentExecution(execution);
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, [url]);

  return { socket, connected, logs, currentExecution };
}
