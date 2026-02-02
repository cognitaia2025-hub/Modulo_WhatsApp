import React, { useState, useEffect } from 'react';
import { Database, Table, RefreshCw, ExternalLink, Search, X, Loader2, Eye } from 'lucide-react';

interface TableInfo {
  table_name: string;
  table_type: string;
  row_count: number;
  description?: string;
}

interface ColumnInfo {
  column_name: string;
  data_type: string;
  is_nullable: string;
  column_default?: string;
  is_primary_key: boolean;
  foreign_key?: {
    table: string;
    column: string;
  };
}

interface TableSchema {
  table_name: string;
  columns: ColumnInfo[];
  primary_keys: string[];
  foreign_keys: { column_name: string; foreign_table_name: string; foreign_column_name: string }[];
}

interface TableData {
  data: Record<string, any>[];
  pagination: {
    page: number;
    page_size: number;
    total_rows: number;
    total_pages: number;
  };
}

interface DatabaseStats {
  database_size: string;
  table_count: number;
  index_count: number;
  active_connections: number;
}

// Modal para ver contenido de celda
interface CellModalData {
  column: string;
  dataType: string;
  value: any;
  tableName: string;
  rowIndex: number;
}

// Detectar URL del backend
const getBackendUrl = () => {
  if (window.location.hostname.includes('github.dev')) {
    return window.location.origin.replace('-3000.', '-8000.');
  }
  return 'http://localhost:8000';
};

const TableExplorer: React.FC = () => {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableSchema, setTableSchema] = useState<TableSchema | null>(null);
  const [tableData, setTableData] = useState<TableData | null>(null);
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cellModal, setCellModal] = useState<CellModalData | null>(null);
  const [decodedContent, setDecodedContent] = useState<any>(null);
  const [decodingLoading, setDecodingLoading] = useState(false);

  const backendUrl = getBackendUrl();

  // Cargar lista de tablas
  const loadTables = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${backendUrl}/api/database/tables`);
      const data = await response.json();
      if (data.success) {
        setTables(data.tables);
      } else {
        setError(data.detail || 'Error loading tables');
      }
    } catch (err) {
      setError(`Connection error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  // Cargar estadísticas
  const loadStats = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/database/stats`);
      const data = await response.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  // Cargar esquema de tabla
  const loadTableSchema = async (tableName: string) => {
    try {
      const response = await fetch(`${backendUrl}/api/database/tables/${tableName}/schema`);
      const data = await response.json();
      if (data.success) {
        setTableSchema(data);
      }
    } catch (err) {
      console.error('Error loading schema:', err);
    }
  };

  // Cargar datos de tabla
  const loadTableData = async (tableName: string, page: number = 1) => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/database/tables/${tableName}/data?page=${page}&page_size=50`);
      const data = await response.json();
      if (data.success) {
        setTableData(data);
        setCurrentPage(page);
      }
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  // Seleccionar tabla
  const handleSelectTable = async (tableName: string) => {
    setSelectedTable(tableName);
    setCurrentPage(1);
    await Promise.all([
      loadTableSchema(tableName),
      loadTableData(tableName, 1)
    ]);
  };

  // Navegar a tabla relacionada
  const navigateToRelatedTable = async (tableName: string, _columnName?: string, _value?: unknown) => {
    setSelectedTable(tableName);
    setCurrentPage(1);
    await loadTableSchema(tableName);
    // Cargar todos los datos y luego podrías filtrar - por ahora solo carga la tabla
    await loadTableData(tableName, 1);
  };

  // Abrir modal para ver contenido de celda
  const openCellModal = async (column: ColumnInfo, value: any, rowIndex: number) => {
    setCellModal({
      column: column.column_name,
      dataType: column.data_type,
      value: value,
      tableName: selectedTable || '',
      rowIndex
    });
    setDecodedContent(null);

    // Si es un campo binario (bytea) o la tabla es checkpoint_blobs/checkpoint_writes, intentar decodificar
    if (column.data_type === 'bytea' || column.column_name === 'blob' || column.column_name === 'checkpoint') {
      try {
        setDecodingLoading(true);
        const row = tableData?.data[rowIndex];
        if (row && selectedTable) {
          const response = await fetch(`${backendUrl}/api/database/decode-blob`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              table_name: selectedTable,
              thread_id: row.thread_id,
              channel: row.channel,
              version: row.version,
              checkpoint_id: row.checkpoint_id
            })
          });
          const data = await response.json();
          if (data.success) {
            setDecodedContent(data.decoded);
          }
        }
      } catch (err) {
        console.error('Error decoding blob:', err);
      } finally {
        setDecodingLoading(false);
      }
    }
  };

  // Cargar datos iniciales
  useEffect(() => {
    loadTables();
    loadStats();
  }, []);

  // Filtrar tablas por búsqueda
  const filteredTables = tables.filter(t => 
    t.table_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Renderizar valor de celda con opción de clic para ver detalle
  const renderCellValue = (column: ColumnInfo, value: any, rowIndex: number) => {
    if (value === null || value === undefined) {
      return <span className="text-gray-500 italic">NULL</span>;
    }

    // Detectar si es un campo que puede expandirse
    const isExpandable = 
      typeof value === 'object' ||
      column.data_type === 'bytea' ||
      column.data_type === 'jsonb' ||
      column.data_type === 'json' ||
      column.column_name === 'blob' ||
      column.column_name === 'checkpoint' ||
      (typeof value === 'string' && value.length > 50);

    if (typeof value === 'object') {
      return (
        <button
          onClick={() => openCellModal(column, value, rowIndex)}
          className="text-xs font-mono bg-gray-700 px-1 rounded max-w-xs truncate block hover:bg-gray-600 transition-colors cursor-pointer flex items-center gap-1"
        >
          <Eye size={10} className="flex-shrink-0" />
          {JSON.stringify(value).substring(0, 40)}...
        </button>
      );
    }

    // Si tiene FK, mostrar como link
    if (column.foreign_key) {
      return (
        <button
          onClick={() => navigateToRelatedTable(column.foreign_key!.table, column.foreign_key!.column, value)}
          className="text-blue-400 hover:text-blue-300 flex items-center gap-1 group"
        >
          {String(value)}
          <ExternalLink size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>
      );
    }

    const strValue = String(value);
    
    // Campo binario o blob
    if (column.data_type === 'bytea' || column.column_name === 'blob') {
      return (
        <button
          onClick={() => openCellModal(column, value, rowIndex)}
          className="text-xs font-mono bg-purple-900/50 px-2 py-0.5 rounded hover:bg-purple-800/50 transition-colors cursor-pointer flex items-center gap-1 text-purple-300"
        >
          <Eye size={10} />
          🔐 Binary ({strValue.length > 20 ? strValue.substring(0, 20) + '...' : strValue})
        </button>
      );
    }

    if (isExpandable || strValue.length > 50) {
      return (
        <button
          onClick={() => openCellModal(column, value, rowIndex)}
          className="text-left hover:bg-gray-700/50 px-1 rounded transition-colors cursor-pointer flex items-center gap-1"
          title="Click to expand"
        >
          <span>{strValue.substring(0, 50)}...</span>
          <Eye size={10} className="text-gray-500 flex-shrink-0" />
        </button>
      );
    }
    
    return strValue;
  };

  return (
    <div className="h-full flex bg-gray-900">
      {/* Sidebar - Lista de tablas */}
      <div className="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
        {/* Stats Header */}
        {stats && (
          <div className="p-3 border-b border-gray-700 bg-gray-750">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-gray-700/50 rounded p-2">
                <div className="text-gray-400">Size</div>
                <div className="text-white font-medium">{stats.database_size}</div>
              </div>
              <div className="bg-gray-700/50 rounded p-2">
                <div className="text-gray-400">Tables</div>
                <div className="text-white font-medium">{stats.table_count}</div>
              </div>
            </div>
          </div>
        )}

        {/* Search */}
        <div className="p-2 border-b border-gray-700">
          <div className="relative">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search tables..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-gray-700 text-white text-sm pl-8 pr-8 py-1.5 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Refresh button */}
        <div className="p-2 border-b border-gray-700">
          <button
            onClick={loadTables}
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white text-sm py-1.5 rounded transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Tables List */}
        <div className="flex-1 overflow-y-auto">
          {error && (
            <div className="p-3 text-red-400 text-xs">{error}</div>
          )}
          {filteredTables.map((table) => (
            <button
              key={table.table_name}
              onClick={() => handleSelectTable(table.table_name)}
              className={`w-full flex items-center justify-between px-3 py-2 text-left text-sm transition-colors ${
                selectedTable === table.table_name
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <Table size={14} className="flex-shrink-0" />
                <span className="truncate">{table.table_name}</span>
              </div>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                selectedTable === table.table_name ? 'bg-blue-500' : 'bg-gray-600'
              }`}>
                {table.row_count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Content - Table Data */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {selectedTable && tableSchema ? (
          <>
            {/* Table Header */}
            <div className="bg-gray-800 border-b border-gray-700 px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                    <Database size={18} />
                    {selectedTable}
                  </h2>
                  <p className="text-xs text-gray-400 mt-1">
                    {tableSchema.columns.length} columns • {tableData?.pagination.total_rows || 0} rows
                    {tableSchema.foreign_keys.length > 0 && (
                      <span className="ml-2">
                        • {tableSchema.foreign_keys.length} foreign keys
                      </span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {/* FK Legend */}
                  {tableSchema.foreign_keys.length > 0 && (
                    <div className="flex items-center gap-1 text-xs text-gray-400 bg-gray-700/50 px-2 py-1 rounded">
                      <ExternalLink size={12} className="text-blue-400" />
                      <span>= clickable FK</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Schema Info (collapsible) */}
            <div className="bg-gray-850 border-b border-gray-700 px-4 py-2">
              <div className="flex flex-wrap gap-2">
                {tableSchema.columns.slice(0, 10).map((col) => (
                  <span
                    key={col.column_name}
                    className={`text-xs px-2 py-1 rounded flex items-center gap-1 ${
                      col.is_primary_key
                        ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                        : col.foreign_key
                        ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                        : 'bg-gray-700 text-gray-300'
                    }`}
                  >
                    {col.is_primary_key && <span>🔑</span>}
                    {col.foreign_key && <ExternalLink size={10} />}
                    {col.column_name}
                    <span className="text-gray-500">({col.data_type})</span>
                  </span>
                ))}
                {tableSchema.columns.length > 10 && (
                  <span className="text-xs text-gray-500">
                    +{tableSchema.columns.length - 10} more
                  </span>
                )}
              </div>
            </div>

            {/* Data Table */}
            <div className="flex-1 overflow-auto">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 size={32} className="animate-spin text-blue-500" />
                </div>
              ) : tableData && tableData.data.length > 0 ? (
                <table className="w-full text-sm">
                  <thead className="bg-gray-800 sticky top-0">
                    <tr>
                      {tableSchema.columns.map((col) => (
                        <th
                          key={col.column_name}
                          className={`px-3 py-2 text-left font-medium border-b border-gray-700 ${
                            col.is_primary_key
                              ? 'text-yellow-300'
                              : col.foreign_key
                              ? 'text-blue-300'
                              : 'text-gray-300'
                          }`}
                        >
                          <div className="flex items-center gap-1">
                            {col.is_primary_key && <span>🔑</span>}
                            {col.foreign_key && <ExternalLink size={10} />}
                            {col.column_name}
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.data.map((row, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors"
                      >
                        {tableSchema.columns.map((col) => (
                          <td key={col.column_name} className="px-3 py-2 text-gray-300">
                            {renderCellValue(col, row[col.column_name], idx)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  No data found
                </div>
              )}
            </div>

            {/* Pagination */}
            {tableData && tableData.pagination.total_pages > 1 && (
              <div className="bg-gray-800 border-t border-gray-700 px-4 py-2 flex items-center justify-between">
                <span className="text-sm text-gray-400">
                  Page {tableData.pagination.page} of {tableData.pagination.total_pages}
                  <span className="ml-2">({tableData.pagination.total_rows} total rows)</span>
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => loadTableData(selectedTable, currentPage - 1)}
                    disabled={currentPage <= 1}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => loadTableData(selectedTable, currentPage + 1)}
                    disabled={currentPage >= tableData.pagination.total_pages}
                    className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm rounded transition-colors"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <Database size={48} className="mx-auto mb-4 opacity-50" />
              <p>Select a table to view its data</p>
            </div>
          </div>
        )}
      </div>

      {/* Modal para ver contenido de celda */}
      {cellModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg border border-gray-600 shadow-2xl max-w-4xl w-full max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
              <div>
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Eye size={18} />
                  {cellModal.column}
                </h3>
                <p className="text-xs text-gray-400 mt-1">
                  Table: {cellModal.tableName} • Type: {cellModal.dataType} • Row: {cellModal.rowIndex + 1}
                </p>
              </div>
              <button
                onClick={() => {
                  setCellModal(null);
                  setDecodedContent(null);
                }}
                className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-4">
              {decodingLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 size={32} className="animate-spin text-blue-500" />
                  <span className="ml-3 text-gray-400">Decoding content...</span>
                </div>
              ) : decodedContent ? (
                <div className="space-y-4">
                  <div className="bg-green-900/30 border border-green-600/50 rounded p-3">
                    <p className="text-green-400 text-sm font-medium mb-2">✅ Decoded Content</p>
                  </div>
                  
                  {/* Si el contenido decodificado tiene mensajes */}
                  {Array.isArray(decodedContent) ? (
                    <div className="space-y-2">
                      {decodedContent.map((item: any, idx: number) => (
                        <div key={idx} className="bg-gray-700/50 rounded p-3 border border-gray-600">
                          {typeof item === 'object' ? (
                            <div>
                              {item.type && (
                                <span className={`text-xs px-2 py-0.5 rounded mb-2 inline-block ${
                                  item.type === 'human' ? 'bg-blue-500/30 text-blue-300' :
                                  item.type === 'ai' ? 'bg-purple-500/30 text-purple-300' :
                                  'bg-gray-500/30 text-gray-300'
                                }`}>
                                  {item.type}
                                </span>
                              )}
                              {item.content && (
                                <p className="text-white mt-2 whitespace-pre-wrap">{item.content}</p>
                              )}
                              {item.name && (
                                <p className="text-gray-400 text-xs mt-1">Name: {item.name}</p>
                              )}
                              {!item.content && !item.type && (
                                <pre className="text-xs text-gray-300 whitespace-pre-wrap overflow-x-auto">
                                  {JSON.stringify(item, null, 2)}
                                </pre>
                              )}
                            </div>
                          ) : (
                            <p className="text-gray-300">{String(item)}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : typeof decodedContent === 'object' ? (
                    <pre className="bg-gray-900 rounded p-4 text-sm text-gray-300 overflow-x-auto font-mono whitespace-pre-wrap">
                      {JSON.stringify(decodedContent, null, 2)}
                    </pre>
                  ) : (
                    <p className="text-gray-300 whitespace-pre-wrap">{String(decodedContent)}</p>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="bg-gray-700/30 border border-gray-600 rounded p-3">
                    <p className="text-gray-400 text-sm font-medium mb-2">📄 Raw Value</p>
                  </div>
                  
                  {typeof cellModal.value === 'object' ? (
                    <pre className="bg-gray-900 rounded p-4 text-sm text-gray-300 overflow-x-auto font-mono whitespace-pre-wrap">
                      {JSON.stringify(cellModal.value, null, 2)}
                    </pre>
                  ) : (
                    <div className="bg-gray-900 rounded p-4">
                      <p className="text-gray-300 whitespace-pre-wrap font-mono text-sm break-all">
                        {String(cellModal.value)}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 border-t border-gray-700 flex justify-end">
              <button
                onClick={() => {
                  setCellModal(null);
                  setDecodedContent(null);
                }}
                className="bg-gray-600 hover:bg-gray-500 text-white px-4 py-2 rounded transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TableExplorer;
