"""
Extractores NLP para la Etapa 4 - Recepcionista Conversacional

Dos funciones específicas para extraer información de mensajes de pacientes:
1. extraer_nombre_con_llm - Usa DeepSeek API para extraer nombres
2. extraer_seleccion - Usa regex para extraer selecciones A/B/C/D/E
"""

import os
import re
import logging
from typing import Optional
import json
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-test-key")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# Logger
logger = logging.getLogger(__name__)


def extraer_nombre_con_llm(mensaje: str) -> str:
    """
    Extrae el nombre completo del mensaje usando DeepSeek API.
    
    Args:
        mensaje: Mensaje del paciente conteniendo su nombre
        
    Returns:
        Nombre completo limpio, sin prefijos como "me llamo" o "soy"
        
    Examples:
        - "Me llamo Juan Pérez" → "Juan Pérez"
        - "soy Maria Garcia Lopez" → "Maria Garcia Lopez"  
        - "Mi nombre es Carlos Alberto Ruiz" → "Carlos Alberto Ruiz"
        - "Juan" → "Juan"
    """
    try:
        # Prompt específico para extracción de nombres
        prompt = f"""Extrae únicamente el nombre completo de la siguiente frase. 
No incluyas prefijos como "me llamo", "soy", "mi nombre es", etc.
Solo devuelve el nombre limpio.

Frase: "{mensaje}"

Nombre:"""

        # Payload para DeepSeek API
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "Eres un asistente especializado en extraer nombres de personas de texto. Devuelve únicamente el nombre completo sin prefijos."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        # Hacer request a DeepSeek
        response = requests.post(
            DEEPSEEK_API_URL, 
            headers=headers, 
            json=payload, 
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            nombre_extraido = result["choices"][0]["message"]["content"].strip()
            
            # Limpiar respuesta adicional
            nombre_extraido = nombre_extraido.replace("Nombre:", "").strip()
            
            # Validar que no esté vacío
            if not nombre_extraido or len(nombre_extraido) < 2:
                logger.warning(f"Nombre extraído demasiado corto: '{nombre_extraido}'")
                return _extraer_nombre_fallback(mensaje)
            
            logger.info(f"Nombre extraído con DeepSeek: '{nombre_extraido}'")
            return nombre_extraido
            
        else:
            logger.error(f"Error en DeepSeek API: {response.status_code}")
            return _extraer_nombre_fallback(mensaje)
            
    except Exception as e:
        logger.error(f"Error al extraer nombre con LLM: {e}")
        return _extraer_nombre_fallback(mensaje)


def _extraer_nombre_fallback(mensaje: str) -> str:
    """
    Extracción de nombre usando regex como fallback cuando falla la API.
    
    Args:
        mensaje: Mensaje original
        
    Returns:
        Nombre extraído o mensaje original limpio
    """
    # Patrones para remover prefijos comunes
    prefijos_regex = [
        r'^(me llamo|soy|mi nombre es|yo soy)\s+',
        r'^(hola,?\s*)?(me llamo|soy)\s+',
        r'^(mi nombre es|yo me llamo)\s+'
    ]
    
    mensaje_limpio = mensaje.strip()
    
    # Intentar remover prefijos
    for patron in prefijos_regex:
        mensaje_limpio = re.sub(patron, '', mensaje_limpio, flags=re.IGNORECASE)
    
    # Limpiar caracteres especiales y multiple spaces
    mensaje_limpio = re.sub(r'\s+', ' ', mensaje_limpio).strip()
    
    # Si queda muy corto, usar mensaje original
    if len(mensaje_limpio) < 2:
        mensaje_limpio = mensaje.strip()
    
    logger.warning(f"Usando extracción fallback: '{mensaje_limpio}'")
    return mensaje_limpio


def extraer_seleccion(mensaje: str) -> Optional[int]:
    """
    Extrae la selección (A/B/C/D/E) del mensaje usando regex.
    
    Args:
        mensaje: Mensaje del paciente con su selección
        
    Returns:
        Índice 0-4 (A=0, B=1, C=2, D=3, E=4) o None si no se encuentra
        
    Examples:
        - "la opción B" → 1
        - "escojo A por favor" → 0  
        - "C" → 2
        - "quiero la primera" → None (no es A/B/C/D/E explícito)
        - "b por favor" → 1 (case insensitive)
    """
    if not mensaje:
        return None
        
    mensaje = mensaje.strip().upper()  # Convertir a mayúsculas para match
    
    # Patrones para detectar selecciones A/B/C/D/E
    patrones = [
        r'\b([A-E])\b',                    # Letra sola: "A", "B", etc.
        r'opción\s+([A-E])',               # "opción A", "opción B"
        r'letra\s+([A-E])',                # "letra A", "letra B" 
        r'escojo\s+([A-E])',               # "escojo A"
        r'quiero\s+([A-E])',               # "quiero B"
        r'prefiero\s+([A-E])',             # "prefiero C"
        r'elijo\s+([A-E])',                # "elijo D"
        r'selecciono\s+([A-E])',           # "selecciono E"
        r'^([A-E])$'                       # Solo la letra
    ]
    
    for patron in patrones:
        match = re.search(patron, mensaje)
        if match:
            letra = match.group(1)
            # Convertir letra a índice
            indices = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}
            resultado = indices[letra]
            logger.info(f"Selección extraída: '{letra}' → índice {resultado}")
            return resultado
    
    logger.info(f"No se encontró selección válida en: '{mensaje}'")
    return None


# Testing functions para desarrollo
if __name__ == "__main__":
    # Test extraer_nombre_con_llm
    print("=== Test extraer_nombre_con_llm ===")
    casos_nombre = [
        "Me llamo Juan Pérez",
        "soy Maria Garcia Lopez", 
        "Mi nombre es Carlos Alberto Ruiz",
        "Juan",
        "Hola, soy Ana María"
    ]
    
    for caso in casos_nombre:
        resultado = extraer_nombre_con_llm(caso)
        print(f"'{caso}' → '{resultado}'")
    
    print("\n=== Test extraer_seleccion ===")
    casos_seleccion = [
        "la opción B",
        "escojo A por favor",
        "C",
        "quiero la primera",  # Debe retornar None
        "b por favor",
        "SELECCIONO D",
        "xyz abc"  # Debe retornar None
    ]
    
    for caso in casos_seleccion:
        resultado = extraer_seleccion(caso)
        print(f"'{caso}' → {resultado}")