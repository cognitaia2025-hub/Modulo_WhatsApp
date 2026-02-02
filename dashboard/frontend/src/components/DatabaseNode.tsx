import { memo } from 'react';
import { Handle, Position } from 'reactflow';

interface DatabaseNodeProps {
  data: {
    label: string;
    status?: 'idle' | 'active' | 'error';
    queryCount?: number;
  };
}

const DatabaseNode: React.FC<DatabaseNodeProps> = ({ data }) => {
  const { label, status = 'idle', queryCount } = data;

  const getStatusStyle = () => {
    switch (status) {
      case 'active': return 'border-emerald-500 bg-emerald-900/40 shadow-emerald-500/20';
      case 'error': return 'border-red-500 bg-red-900/40';
      default: return 'border-slate-500 bg-slate-800/60';
    }
  };

  return (
    <div className="relative">
      <Handle type="target" position={Position.Left} className="!bg-emerald-500" />
      <Handle type="source" position={Position.Right} className="!bg-emerald-500" />
      
      {/* Forma de cilindro para DB */}
      <div className={`min-w-[140px] rounded-lg border-2 ${getStatusStyle()} shadow-lg transition-all duration-300`}>
        {/* Tapa superior del cilindro */}
        <div className="h-3 bg-gradient-to-b from-slate-600 to-transparent rounded-t-lg" />
        
        <div className="px-4 py-2 text-center">
          <span className="text-white font-semibold text-sm">{label}</span>
        </div>
        
        {queryCount !== undefined && (
          <div className="px-4 pb-2 text-center text-xs text-emerald-400">
            📊 {queryCount} queries
          </div>
        )}
        
        {/* Tapa inferior del cilindro */}
        <div className="h-3 bg-gradient-to-t from-slate-600 to-transparent rounded-b-lg" />
      </div>
    </div>
  );
};

export default memo(DatabaseNode);
