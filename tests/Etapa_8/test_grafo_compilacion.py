"""
Tests de Compilación del Grafo - ETAPA 8

Valida que el grafo se compile correctamente y tenga todos los nodos configurados.
"""

import pytest
import sys
import os
from pathlib import Path

# Añadir path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph_whatsapp import crear_grafo_whatsapp, app
from src.state.agent_state import WhatsAppAgentState


class TestGrafoCompilacion:
    """Tests de compilación y estructura del grafo"""
    
    def test_grafo_compila_correctamente(self):
        """Test que el grafo se compila sin errores"""
        grafo = crear_grafo_whatsapp()
        assert grafo is not None
        
        # Verificar que es un CompiledGraph
        assert hasattr(grafo, 'invoke')
        assert hasattr(grafo, 'get_graph')
    
    def test_todos_los_nodos_agregados(self):
        """Test que todos los 12 nodos están presentes"""
        grafo = crear_grafo_whatsapp()
        graph_def = grafo.get_graph()
        
        nodos_esperados = {
            'identificacion_usuario',
            'cache_sesion',
            'filtrado_inteligente', 
            'recuperacion_episodica',
            'recuperacion_medica',
            'seleccion_herramientas',
            'ejecucion_herramientas',
            'ejecucion_medica',
            'recepcionista',
            'generacion_resumen',
            'persistencia_episodica',
            'sincronizador_hibrido'
        }
        
        nodos_actuales = set(graph_def.nodes.keys())
        
        # Verificar que todos los nodos esperados están presentes
        assert nodos_esperados.issubset(nodos_actuales), f"Nodos faltantes: {nodos_esperados - nodos_actuales}"
        assert len(nodos_actuales) >= 12, f"Se esperan al menos 12 nodos, encontrados: {len(nodos_actuales)}"
    
    def test_punto_entrada_es_identificacion(self):
        """Test que el punto de entrada es identificacion_usuario"""
        grafo = crear_grafo_whatsapp()
        graph_def = grafo.get_graph()
        
        # Buscar edges desde START
        edges_desde_start = []
        for edge in graph_def.edges:
            if edge.source == '__start__':
                edges_desde_start.append(edge.target)
        
        assert len(edges_desde_start) == 1, f"Debe haber exactamente 1 edge desde START, encontrados: {len(edges_desde_start)}"
        assert edges_desde_start[0] == 'identificacion_usuario', f"START debe apuntar a identificacion_usuario, apunta a: {edges_desde_start[0]}"
    
    def test_rutas_fijas_correctas(self):
        """Test que las rutas fijas están configuradas correctamente"""
        grafo = crear_grafo_whatsapp()
        graph_def = grafo.get_graph()
        
        # Rutas fijas esperadas (source -> target)
        rutas_fijas_esperadas = {
            ('identificacion_usuario', 'cache_sesion'),
            ('cache_sesion', 'filtrado_inteligente'),
            ('recuperacion_medica', 'seleccion_herramientas'),
            ('recuperacion_episodica', 'seleccion_herramientas'),
            ('ejecucion_herramientas', 'generacion_resumen'),
            ('ejecucion_medica', 'generacion_resumen'),
            ('sincronizador_hibrido', 'generacion_resumen'),
            ('generacion_resumen', 'persistencia_episodica'),
            ('persistencia_episodica', '__end__')
        }
        
        # Obtener rutas fijas reales (no condicionales)
        rutas_fijas_reales = set()
        for edge in graph_def.edges:
            # Solo edges normales, no condicionales
            if not hasattr(edge, 'condition'):
                rutas_fijas_reales.add((edge.source, edge.target))
        
        # Verificar que las rutas esperadas existen
        for ruta in rutas_fijas_esperadas:
            assert ruta in rutas_fijas_reales, f"Ruta fija faltante: {ruta[0]} -> {ruta[1]}"
    
    def test_rutas_condicionales_configuradas(self):
        """Test que las 3 rutas condicionales están configuradas"""
        grafo = crear_grafo_whatsapp()
        graph_def = grafo.get_graph()
        
        # Buscar edges condicionales
        edges_condicionales = []
        for edge in graph_def.edges:
            if hasattr(edge, 'condition') and edge.condition is not None:
                edges_condicionales.append(edge.source)
        
        # Debe haber exactamente 3 nodos con edges condicionales
        nodos_con_condicionales = set(edges_condicionales)
        nodos_esperados_condicionales = {
            'filtrado_inteligente',      # Decisión 1
            'seleccion_herramientas',    # Decisión 2  
            'recepcionista'              # Decisión 3
        }
        
        assert nodos_esperados_condicionales == nodos_con_condicionales, \
            f"Nodos con condicionales esperados: {nodos_esperados_condicionales}, encontrados: {nodos_con_condicionales}"


class TestGrafoInstanciaGlobal:
    """Tests de la instancia global del grafo"""
    
    def test_instancia_global_existe(self):
        """Test que la instancia global 'app' existe y es válida"""
        assert app is not None
        assert hasattr(app, 'invoke')
        assert hasattr(app, 'get_graph')
    
    def test_instancia_global_es_compilada(self):
        """Test que la instancia global está compilada"""
        # Debe poder obtener el grafo sin errores
        graph_def = app.get_graph()
        assert graph_def is not None
        assert len(graph_def.nodes) >= 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])