import { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface LLMNodeProps {
  data: {
    label: string;
    status?: 'idle' | 'thinking' | 'completed' | 'error';
    tokensUsed?: number;
    latency?: number;
  };
}

const LLMNode: React.FC<LLMNodeProps> = ({ data }) => {
  const { label, status = 'idle', tokensUsed, latency } = data;

  const getStatusStyle = () => {
    switch (status) {
      case 'thinking': return 'border-purple-500 bg-purple-900/40 animate-pulse shadow-purple-500/30';
      case 'completed': return 'border-purple-400 bg-purple-900/30';
      case 'error': return 'border-red-500 bg-red-900/40';
      default: return 'border-violet-600 bg-violet-900/40';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'thinking': return '🧠';
      case 'completed': return '✨';
      case 'error': return '❌';
      default: return '💭';
    }
  };

  return (
    <div className="relative">
      <Handle type="target" position={Position.Left} className="!bg-purple-500" />
      <Handle type="source" position={Position.Right} className="!bg-purple-500" />
      
      {/* Nodo LLM con diseño especial */}
      <div className={`min-w-[130px] rounded-xl border-2 ${getStatusStyle()} shadow-lg transition-all duration-300`}>
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-white font-semibold text-sm">{label}</span>
            <span className="text-lg">{getStatusIcon()}</span>
          </div>
          
          {(tokensUsed !== undefined || latency !== undefined) && (
            <div className="mt-2 text-xs text-purple-300 space-y-1">
              {tokensUsed && <div>🎯 {tokensUsed} tokens</div>}
              {latency && <div>⚡ {latency}ms</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(LLMNode);
