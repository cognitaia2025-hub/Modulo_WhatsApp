"""
Tests para Dashboard Backend
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Test que el endpoint raíz responde correctamente"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["service"] == "WhatsApp Agent Dashboard"

def test_get_graph():
    """Test que el endpoint de grafo retorna estructura correcta"""
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 15  # 15 nodos del sistema
    assert len(data["edges"]) > 0

def test_get_executions():
    """Test que el endpoint de ejecuciones responde"""
    response = client.get("/api/executions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_execution_not_found():
    """Test que el endpoint de ejecución individual maneja ID inexistente"""
    response = client.get("/api/executions/nonexistent-id")
    assert response.status_code == 200
    data = response.json()
    assert "error" in data

def test_graph_node_structure():
    """Test que los nodos del grafo tienen la estructura correcta"""
    response = client.get("/api/graph")
    data = response.json()
    
    for node in data["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "position" in node
        assert "x" in node["position"]
        assert "y" in node["position"]

def test_graph_edge_structure():
    """Test que las conexiones del grafo tienen la estructura correcta"""
    response = client.get("/api/graph")
    data = response.json()
    
    for edge in data["edges"]:
        assert "source" in edge
        assert "target" in edge

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
