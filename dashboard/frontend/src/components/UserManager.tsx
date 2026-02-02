import React, { useState, useEffect, useCallback } from 'react';
import { 
  Search, Users, UserCheck, User, Trash2, AlertTriangle, 
  X, Loader2, CheckSquare, Square, RefreshCw, Phone, Mail,
  Stethoscope, Database, Shield
} from 'lucide-react';

interface PatientUser {
  id: number;
  nombre_completo: string;
  telefono: string | null;
  email: string | null;
  doctor_id: number | null;
  doctor_nombre: string | null;
  created_at: string;
  total_citas: number;
  total_historiales: number;
}

interface DoctorUser {
  id: number;
  nombre_completo: string;
  telefono: string | null;
  especialidad: string;
  created_at: string;
  total_pacientes: number;
  total_citas: number;
}

type UserType = 'pacientes' | 'doctores';
type SearchType = 'all' | 'name' | 'id' | 'phone';

// Detectar URL del backend
const getBackendUrl = () => {
  if (window.location.hostname.includes('github.dev')) {
    return window.location.origin.replace('-3000.', '-8000.');
  }
  return 'http://localhost:8000';
};

const UserManager: React.FC = () => {
  // Estado principal
  const [userType, setUserType] = useState<UserType>('pacientes');
  const [searchTerm, setSearchTerm] = useState('');
  const [searchType, setSearchType] = useState<SearchType>('all');
  const [users, setUsers] = useState<(PatientUser | DoctorUser)[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Selección
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  
  // Modales
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showSelectAllModal, setShowSelectAllModal] = useState<'pacientes' | 'doctores' | null>(null);
  const [deleteIncludeRelated, setDeleteIncludeRelated] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState<{ success: boolean; message: string } | null>(null);

  const backendUrl = getBackendUrl();

  // Cargar todos los usuarios
  const loadAllUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${backendUrl}/api/database/users/all/${userType}`);
      const data = await response.json();
      
      if (data.success) {
        setUsers(data.users);
        setSelectedIds(new Set());
      } else {
        setError(data.detail || 'Error loading users');
      }
    } catch (err) {
      setError(`Connection error: ${err}`);
    } finally {
      setLoading(false);
    }
  }, [backendUrl, userType]);

  // Buscar usuarios
  const searchUsers = async () => {
    if (!searchTerm.trim()) {
      loadAllUsers();
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${backendUrl}/api/database/users/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          search_term: searchTerm,
          search_type: searchType,
          user_type: userType
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setUsers(data.users);
        setSelectedIds(new Set());
      } else {
        setError(data.detail || 'Error searching users');
      }
    } catch (err) {
      setError(`Connection error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  // Eliminar usuarios seleccionados
  const deleteSelectedUsers = async () => {
    if (selectedIds.size === 0) return;
    
    try {
      setDeleting(true);
      
      const response = await fetch(`${backendUrl}/api/database/users/delete`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_ids: Array.from(selectedIds),
          user_type: userType,
          include_related: deleteIncludeRelated
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        setDeleteResult({
          success: true,
          message: `✅ ${data.message}. ${
            deleteIncludeRelated 
              ? `Datos relacionados eliminados: ${JSON.stringify(data.related_deleted)}`
              : ''
          }`
        });
        
        // Recargar lista
        setTimeout(() => {
          setShowDeleteModal(false);
          setDeleteResult(null);
          loadAllUsers();
        }, 2000);
      } else {
        setDeleteResult({
          success: false,
          message: `❌ Error: ${data.detail}`
        });
      }
    } catch (err) {
      setDeleteResult({
        success: false,
        message: `❌ Error de conexión: ${err}`
      });
    } finally {
      setDeleting(false);
    }
  };

  // Toggle selección individual
  const toggleSelection = (id: number) => {
    const newSelection = new Set(selectedIds);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedIds(newSelection);
  };

  // Seleccionar/Deseleccionar todos los mostrados
  const toggleSelectAll = () => {
    if (selectedIds.size === users.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(users.map(u => u.id)));
    }
  };

  // Seleccionar todos de un tipo (abre modal de confirmación)
  const handleSelectAllOfType = async (type: 'pacientes' | 'doctores') => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/api/database/users/all/${type}`);
      const data = await response.json();
      
      if (data.success) {
        setUserType(type);
        setUsers(data.users);
        setSelectedIds(new Set(data.users.map((u: PatientUser | DoctorUser) => u.id)));
        setShowSelectAllModal(null);
      }
    } catch (err) {
      setError(`Error loading ${type}: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  // Cargar usuarios al cambiar tipo
  useEffect(() => {
    loadAllUsers();
  }, [loadAllUsers]);

  // Manejar Enter en búsqueda
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      searchUsers();
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header con controles */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Users size={24} />
            Gestión de Usuarios
          </h2>
          
          {/* Botones de selección masiva */}
          <div className="flex gap-2">
            <button
              onClick={() => setShowSelectAllModal('pacientes')}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors text-sm"
            >
              <UserCheck size={16} />
              Todos los Pacientes
            </button>
            <button
              onClick={() => setShowSelectAllModal('doctores')}
              className="flex items-center gap-2 px-3 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded transition-colors text-sm"
            >
              <Stethoscope size={16} />
              Todos los Doctores
            </button>
          </div>
        </div>

        {/* Tabs de tipo de usuario */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setUserType('pacientes')}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              userType === 'pacientes'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <User size={16} />
            Pacientes
          </button>
          <button
            onClick={() => setUserType('doctores')}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center gap-2 ${
              userType === 'doctores'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <Stethoscope size={16} />
            Doctores
          </button>
        </div>

        {/* Barra de búsqueda */}
        <div className="flex gap-2">
          <div className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder={`Buscar ${userType} por nombre, ID o teléfono...`}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-gray-700 text-white pl-10 pr-4 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            
            {/* Selector de tipo de búsqueda */}
            <select
              value={searchType}
              onChange={(e) => setSearchType(e.target.value as SearchType)}
              className="bg-gray-700 text-white px-3 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none"
            >
              <option value="all">Todo</option>
              <option value="name">Nombre</option>
              <option value="id">ID</option>
              <option value="phone">Teléfono</option>
            </select>
            
            <button
              onClick={searchUsers}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors flex items-center gap-2"
            >
              <Search size={16} />
              Buscar
            </button>
            
            <button
              onClick={loadAllUsers}
              className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
              title="Refrescar"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Acciones de selección */}
        {selectedIds.size > 0 && (
          <div className="mt-4 flex items-center gap-4 bg-gray-700/50 rounded-lg p-3">
            <span className="text-white">
              <strong>{selectedIds.size}</strong> {userType} seleccionados
            </span>
            <button
              onClick={() => setShowDeleteModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors"
            >
              <Trash2 size={16} />
              Eliminar Seleccionados
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="text-gray-400 hover:text-white transition-colors"
            >
              Deseleccionar todo
            </button>
          </div>
        )}
      </div>

      {/* Lista de usuarios */}
      <div className="flex-1 overflow-auto p-4">
        {error && (
          <div className="bg-red-900/50 border border-red-600 rounded-lg p-4 mb-4 text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 size={32} className="animate-spin text-blue-500" />
          </div>
        ) : users.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <Users size={48} className="mb-4 opacity-50" />
            <p>No se encontraron {userType}</p>
          </div>
        ) : (
          <>
            {/* Header de tabla */}
            <div className="bg-gray-800 rounded-t-lg border border-gray-700 p-3 flex items-center gap-4 font-medium text-gray-300 text-sm">
              <button
                onClick={toggleSelectAll}
                className="text-gray-400 hover:text-white transition-colors"
              >
                {selectedIds.size === users.length ? (
                  <CheckSquare size={20} className="text-blue-400" />
                ) : (
                  <Square size={20} />
                )}
              </button>
              <span className="w-16">ID</span>
              <span className="flex-1">Nombre</span>
              <span className="w-40">Teléfono</span>
              {userType === 'pacientes' ? (
                <>
                  <span className="w-40">Doctor</span>
                  <span className="w-24 text-center">Citas</span>
                  <span className="w-24 text-center">Historiales</span>
                </>
              ) : (
                <>
                  <span className="w-40">Especialidad</span>
                  <span className="w-24 text-center">Pacientes</span>
                  <span className="w-24 text-center">Citas</span>
                </>
              )}
            </div>

            {/* Filas */}
            <div className="border-x border-b border-gray-700 rounded-b-lg divide-y divide-gray-700">
              {users.map((user) => {
                const isSelected = selectedIds.has(user.id);
                
                return (
                  <div
                    key={user.id}
                    className={`p-3 flex items-center gap-4 hover:bg-gray-800/50 transition-colors cursor-pointer ${
                      isSelected ? 'bg-blue-900/30' : ''
                    }`}
                    onClick={() => toggleSelection(user.id)}
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelection(user.id);
                      }}
                      className="text-gray-400 hover:text-white transition-colors"
                    >
                      {isSelected ? (
                        <CheckSquare size={20} className="text-blue-400" />
                      ) : (
                        <Square size={20} />
                      )}
                    </button>
                    
                    <span className="w-16 text-gray-400 font-mono text-sm">{user.id}</span>
                    
                    <div className="flex-1">
                      <span className="text-white">{user.nombre_completo}</span>
                      {'email' in user && user.email && (
                        <div className="text-xs text-gray-500 flex items-center gap-1 mt-1">
                          <Mail size={10} />
                          {user.email}
                        </div>
                      )}
                    </div>
                    
                    <span className="w-40 text-gray-400 flex items-center gap-1">
                      {user.telefono ? (
                        <>
                          <Phone size={12} />
                          {user.telefono}
                        </>
                      ) : (
                        <span className="text-gray-600 italic">Sin teléfono</span>
                      )}
                    </span>
                    
                    {userType === 'pacientes' && 'doctor_nombre' in user ? (
                      <>
                        <span className="w-40 text-gray-400">
                          {user.doctor_nombre || <span className="text-gray-600 italic">Sin doctor</span>}
                        </span>
                        <span className="w-24 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            user.total_citas > 0 ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-500'
                          }`}>
                            {user.total_citas}
                          </span>
                        </span>
                        <span className="w-24 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            user.total_historiales > 0 ? 'bg-purple-900/50 text-purple-300' : 'bg-gray-700 text-gray-500'
                          }`}>
                            {user.total_historiales}
                          </span>
                        </span>
                      </>
                    ) : 'especialidad' in user ? (
                      <>
                        <span className="w-40 text-cyan-400">{user.especialidad}</span>
                        <span className="w-24 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            user.total_pacientes > 0 ? 'bg-blue-900/50 text-blue-300' : 'bg-gray-700 text-gray-500'
                          }`}>
                            {user.total_pacientes}
                          </span>
                        </span>
                        <span className="w-24 text-center">
                          <span className={`px-2 py-1 rounded text-xs ${
                            user.total_citas > 0 ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-500'
                          }`}>
                            {user.total_citas}
                          </span>
                        </span>
                      </>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Modal de confirmación de eliminación */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg border border-gray-600 shadow-2xl max-w-lg w-full">
            {/* Header */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700 bg-red-900/30">
              <AlertTriangle size={24} className="text-red-400" />
              <div>
                <h3 className="text-lg font-semibold text-white">Confirmar Eliminación</h3>
                <p className="text-sm text-gray-400">Esta acción no se puede deshacer</p>
              </div>
              <button
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeleteResult(null);
                }}
                className="ml-auto text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {deleteResult ? (
                <div className={`p-4 rounded-lg ${
                  deleteResult.success ? 'bg-green-900/50 border border-green-600' : 'bg-red-900/50 border border-red-600'
                }`}>
                  <p className={deleteResult.success ? 'text-green-300' : 'text-red-300'}>
                    {deleteResult.message}
                  </p>
                </div>
              ) : (
                <>
                  <div className="bg-gray-700/50 rounded-lg p-4">
                    <p className="text-white mb-2">
                      ¿Estás seguro de que deseas eliminar <strong>{selectedIds.size}</strong> {userType}?
                    </p>
                    <div className="text-sm text-gray-400">
                      IDs a eliminar: {Array.from(selectedIds).slice(0, 10).join(', ')}
                      {selectedIds.size > 10 && ` y ${selectedIds.size - 10} más...`}
                    </div>
                  </div>

                  {/* Opción de eliminar datos relacionados */}
                  <label className="flex items-start gap-3 bg-yellow-900/30 border border-yellow-600/50 rounded-lg p-4 cursor-pointer hover:bg-yellow-900/40 transition-colors">
                    <input
                      type="checkbox"
                      checked={deleteIncludeRelated}
                      onChange={(e) => setDeleteIncludeRelated(e.target.checked)}
                      className="mt-1"
                    />
                    <div>
                      <div className="flex items-center gap-2 text-yellow-300 font-medium">
                        <Database size={16} />
                        Incluir datos relacionados
                      </div>
                      <p className="text-sm text-yellow-200/70 mt-1">
                        {userType === 'pacientes'
                          ? 'Esto eliminará también: citas médicas, historiales médicos y vectores asociados.'
                          : 'Esto eliminará también: citas, disponibilidad, métricas y reportes. Los pacientes serán desasociados pero no eliminados.'
                        }
                      </p>
                    </div>
                  </label>

                  {/* Advertencia adicional */}
                  <div className="bg-red-900/30 border border-red-600/50 rounded-lg p-4 flex items-start gap-3">
                    <Shield size={20} className="text-red-400 mt-0.5" />
                    <div className="text-sm text-red-300">
                      <strong>Advertencia:</strong> Esta operación eliminará permanentemente los datos seleccionados de la base de datos estructurada
                      {deleteIncludeRelated && ' incluyendo todos los datos vectoriales y registros relacionados'}.
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            {!deleteResult && (
              <div className="px-4 py-3 border-t border-gray-700 flex justify-end gap-3">
                <button
                  onClick={() => {
                    setShowDeleteModal(false);
                    setDeleteIncludeRelated(false);
                  }}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={deleteSelectedUsers}
                  disabled={deleting}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {deleting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      Eliminando...
                    </>
                  ) : (
                    <>
                      <Trash2 size={16} />
                      Eliminar {selectedIds.size} {userType}
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal de seleccionar todos */}
      {showSelectAllModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg border border-gray-600 shadow-2xl max-w-md w-full">
            <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-700">
              <AlertTriangle size={24} className="text-yellow-400" />
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Seleccionar todos los {showSelectAllModal}
                </h3>
              </div>
              <button
                onClick={() => setShowSelectAllModal(null)}
                className="ml-auto text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700"
              >
                <X size={20} />
              </button>
            </div>

            <div className="p-4">
              <p className="text-gray-300 mb-4">
                ¿Estás seguro de que deseas seleccionar <strong>todos</strong> los {showSelectAllModal} de la base de datos?
              </p>
              <p className="text-sm text-yellow-400">
                Esta acción cargará y seleccionará todos los registros, lo cual puede tardar si hay muchos datos.
              </p>
            </div>

            <div className="px-4 py-3 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowSelectAllModal(null)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-500 text-white rounded-lg transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleSelectAllOfType(showSelectAllModal)}
                className={`px-4 py-2 text-white rounded-lg transition-colors flex items-center gap-2 ${
                  showSelectAllModal === 'pacientes' 
                    ? 'bg-blue-600 hover:bg-blue-500' 
                    : 'bg-purple-600 hover:bg-purple-500'
                }`}
              >
                <CheckSquare size={16} />
                Seleccionar Todos
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManager;
