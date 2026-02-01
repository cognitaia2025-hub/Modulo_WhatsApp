"""
Tests para Dashboard Backend
"""

import pytest
import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_graph_structure():
    """Test que la estructura del grafo es correcta"""
    from main import graph_structure
    
    assert "nodes" in graph_structure
    assert "edges" in graph_structure
    assert len(graph_structure["nodes"]) == 15  # 15 nodos del sistema
    assert len(graph_structure["edges"]) > 0

def test_graph_node_structure():
    """Test que los nodos del grafo tienen la estructura correcta"""
    from main import graph_structure
    
    for node in graph_structure["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "position" in node
        assert "x" in node["position"]
        assert "y" in node["position"]

def test_graph_edge_structure():
    """Test que las conexiones del grafo tienen la estructura correcta"""
    from main import graph_structure
    
    for edge in graph_structure["edges"]:
        assert "source" in edge
        assert "target" in edge

def test_executions_storage():
    """Test que el almacenamiento de ejecuciones está inicializado"""
    from main import executions
    
    assert isinstance(executions, dict)

def test_socket_io_setup():
    """Test que Socket.IO está configurado correctamente"""
    from main import sio
    
    assert sio is not None
    assert hasattr(sio, 'emit')

def test_fastapi_app():
    """Test que la app FastAPI está configurada"""
    from main import app
    
    assert app is not None
    assert app.title == "WhatsApp Agent Dashboard API"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
