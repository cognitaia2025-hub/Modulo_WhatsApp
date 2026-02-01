export interface Log {
  timestamp: string;
  level: string;
  message: string;
  node_id?: string;
  execution_id: string;
  status?: string;
  duration_ms?: number;
}

export interface NodeExecution {
  status: 'idle' | 'running' | 'completed' | 'error';
  duration_ms?: number;
  timestamp: string;
}

export interface Execution {
  id: string;
  start_time: string;
  nodes: Record<string, NodeExecution>;
  logs: Log[];
}

export interface GraphNode {
  id: string;
  label: string;
  position: { x: number; y: number };
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphStructure {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
