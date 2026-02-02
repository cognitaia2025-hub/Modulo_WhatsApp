import { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface ToolNodeProps {
  data: {
    label: string;
    status?: 'idle' | 'executing' | 'success' | 'error';
    callCount?: number;
  };
}

const ToolNode: React.FC<ToolNodeProps> = ({ data }) => {
  const { label, status = 'idle', callCount } = data;

  const getStatusStyle = () => {
    switch (status) {
      case 'executing': return 'border-amber-500 bg-amber-900/40 animate-pulse';
      case 'success': return 'border-green-500 bg-green-900/40';
      case 'error': return 'border-red-500 bg-red-900/40';
      default: return 'border-orange-600 bg-orange-900/40';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'executing': return '⚙️';
      case 'success': return '✅';
      case 'error': return '❌';
      default: return '🔧';
    }
  };

  return (
    <div className="relative">
      <Handle type="target" position={Position.Left} className="!bg-orange-500" />
      <Handle type="source" position={Position.Right} className="!bg-orange-500" />
      
      {/* Nodo Herramienta con forma hexagonal simulada */}
      <div className={`min-w-[130px] rounded-lg border-2 border-dashed ${getStatusStyle()} shadow-lg transition-all duration-300`}>
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-white font-semibold text-sm">{label}</span>
            <span className="text-lg">{getStatusIcon()}</span>
          </div>
          
          {callCount !== undefined && (
            <div className="mt-1 text-xs text-orange-300">
              📞 {callCount} calls
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ToolNode);
