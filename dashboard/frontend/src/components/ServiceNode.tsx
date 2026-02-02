import { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface ServiceNodeProps {
  data: {
    label: string;
    status?: 'idle' | 'connected' | 'disconnected';
    messageCount?: number;
    category?: string;
  };
}

const ServiceNode: React.FC<ServiceNodeProps> = ({ data }) => {
  const { label, status = 'idle', messageCount, category } = data;

  const isInput = category === 'external';
  const isOutput = category === 'output';

  const getStatusStyle = () => {
    if (isInput) {
      return status === 'connected' 
        ? 'border-green-500 bg-green-900/50 shadow-green-500/20' 
        : 'border-green-700 bg-green-900/30';
    }
    if (isOutput) {
      return 'border-cyan-500 bg-cyan-900/40 shadow-cyan-500/20';
    }
    return 'border-gray-600 bg-gray-800/50';
  };

  return (
    <div className="relative">
      {!isInput && (
        <Handle type="target" position={Position.Left} className="!bg-green-500" />
      )}
      {!isOutput && (
        <Handle type="source" position={Position.Right} className="!bg-cyan-500" />
      )}
      
      {/* Nodo de servicio externo */}
      <div className={`min-w-[120px] rounded-full border-2 ${getStatusStyle()} shadow-lg transition-all duration-300`}>
        <div className="px-5 py-3 text-center">
          <span className="text-white font-semibold text-sm">{label}</span>
          
          {messageCount !== undefined && (
            <div className="mt-1 text-xs text-green-300">
              📨 {messageCount} msgs
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ServiceNode);
