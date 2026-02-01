"""
Logger Interceptor

Captura logs del sistema y los envía al dashboard vía Socket.IO.
"""

import logging
import re
from typing import Dict, Any, Callable, Optional
from datetime import datetime

class DashboardHandler(logging.Handler):
    """
    Handler custom que intercepta logs y los emite al dashboard.
    """
    
    def __init__(self, emit_callback: Callable):
        super().__init__()
        self.emit_callback = emit_callback
        self.current_execution_id = None
        self.current_node = None
        self.node_start_time = {}
    
    def emit(self, record):
        """Procesa cada log y lo envía al dashboard."""
        try:
            log_message = self.format(record)
            
            # Parsear información del log
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': log_message,
                'execution_id': self.current_execution_id or 'unknown'
            }
            
            # Detectar inicio de nodo
            if "NODO_" in log_message and "INICIO" in log_message:
                node_match = re.search(r'NODO_(\w+)', log_message)
                if node_match:
                    self.current_node = node_match.group(1).lower()
                    self.node_start_time[self.current_node] = datetime.now()
                    log_data['node_id'] = self.current_node
                    log_data['status'] = 'running'
            
            # Detectar fin de nodo
            elif "NODO_" in log_message and "FIN" in log_message:
                node_match = re.search(r'NODO_(\w+)', log_message)
                if node_match:
                    node = node_match.group(1).lower()
                    if node in self.node_start_time:
                        duration = (datetime.now() - self.node_start_time[node]).total_seconds() * 1000
                        log_data['node_id'] = node
                        log_data['status'] = 'completed'
                        log_data['duration_ms'] = duration
            
            # Enviar al dashboard
            if self.emit_callback:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self.emit_callback(log_data))
                    else:
                        loop.run_until_complete(self.emit_callback(log_data))
                except RuntimeError:
                    # No hay loop activo, ignorar
                    pass
        
        except Exception as e:
            print(f"Error en DashboardHandler: {e}")

def setup_dashboard_logging(emit_callback: Callable):
    """
    Configura handler de dashboard en el logger principal.
    
    Llamar desde main.py al iniciar el sistema.
    """
    handler = DashboardHandler(emit_callback)
    handler.setLevel(logging.INFO)
    
    # Formato simple para parsing
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    
    # Agregar a logger raíz
    logging.getLogger().addHandler(handler)
    
    print("✅ Dashboard logging configurado")
