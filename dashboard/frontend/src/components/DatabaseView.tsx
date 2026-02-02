import React, { useState } from 'react';
import { Table, Users, Brain } from 'lucide-react';
import TableExplorer from './TableExplorer';
import VectorViewerProjector from './VectorViewerProjector';
import UserManager from './UserManager';

type DatabaseSubTab = 'tables' | 'projector' | 'users';

const DatabaseView: React.FC = () => {
  const [activeSubTab, setActiveSubTab] = useState<DatabaseSubTab>('tables');

  const subTabs: { id: DatabaseSubTab; label: string; icon: React.ReactNode }[] = [
    { id: 'tables', label: 'Tables', icon: <Table size={16} /> },
    { id: 'projector', label: 'Embedding Projector', icon: <Brain size={16} /> },
    { id: 'users', label: 'User Management', icon: <Users size={16} /> },
  ];

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Sub-tabs */}
      <div className="bg-gray-800 border-b border-gray-700 px-4">
        <div className="flex gap-1">
          {subTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors relative ${
                activeSubTab === tab.id
                  ? 'text-white'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab.icon}
              {tab.label}
              {activeSubTab === tab.id && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeSubTab === 'tables' && <TableExplorer />}
        {activeSubTab === 'projector' && <VectorViewerProjector />}
        {activeSubTab === 'users' && <UserManager />}
      </div>
    </div>
  );
};

export default DatabaseView;
