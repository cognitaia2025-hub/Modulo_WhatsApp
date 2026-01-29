"""Tests de Envío WhatsApp"""
import pytest
from unittest.mock import patch, Mock
import requests

from src.background.recordatorios_scheduler import enviar_whatsapp


def test_envio_exitoso():
    """Test: Envío exitoso de WhatsApp"""
    with patch('requests.post') as mock_post:
        # Configurar respuesta exitosa
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Ejecutar
        resultado = enviar_whatsapp('+525512345678', 'Mensaje de prueba')
        
        # Verificar
        assert resultado['exito'] == True
        mock_post.assert_called_once()
        
        # Verificar llamada
        call_args = mock_post.call_args
        assert 'http://localhost:3000/api/send-reminder' in call_args[0][0]
        assert call_args[1]['json']['destinatario'] == '+525512345678'
        assert call_args[1]['json']['mensaje'] == 'Mensaje de prueba'


def test_maneja_error_api():
    """Test: Maneja error de API correctamente"""
    with patch('requests.post') as mock_post:
        # Configurar respuesta de error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Error interno del servidor'
        mock_post.return_value = mock_response
        
        # Ejecutar
        resultado = enviar_whatsapp('+525512345678', 'Mensaje de prueba')
        
        # Verificar
        assert resultado['exito'] == False
        assert 'error' in resultado
        assert 'Error interno del servidor' in resultado['error']


def test_timeout_api():
    """Test: Maneja timeout de API"""
    with patch('requests.post') as mock_post:
        # Configurar timeout
        mock_post.side_effect = requests.exceptions.Timeout('Timeout')
        
        # Ejecutar
        resultado = enviar_whatsapp('+525512345678', 'Mensaje de prueba')
        
        # Verificar
        assert resultado['exito'] == False
        assert 'error' in resultado
        assert 'Timeout' in resultado['error']


def test_formatea_telefono_correctamente():
    """Test: Formatea teléfono correctamente en la llamada"""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Diferentes formatos de teléfono
        telefonos = [
            '+525512345678',
            '5512345678',
            '+52 55 1234 5678'
        ]
        
        for telefono in telefonos:
            resultado = enviar_whatsapp(telefono, 'Test')
            assert resultado['exito'] == True
            
            # Verificar que se envió el teléfono tal cual
            call_args = mock_post.call_args
            assert call_args[1]['json']['destinatario'] == telefono
