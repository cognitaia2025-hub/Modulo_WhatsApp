"""
Modelos Pydantic para validación de datos de pacientes.
"""

from pydantic import BaseModel, Field, validator
import re


class TelefonoPaciente(BaseModel):
    """
    Número de teléfono en formato internacional.
    
    Reglas:
    - Formato: +52XXXXXXXXXX (México)
    - 10 dígitos después del +52
    """
    
    telefono: str = Field(
        ...,
        pattern=r'^\+52\d{10}$',
        description="Teléfono en formato internacional +52XXXXXXXXXX (ejemplo: +526641234567)",
        examples=["+526641234567", "+526642345678"]
    )
    
    @validator('telefono')
    def validar_formato_telefono(cls, v):
        """Validar formato de teléfono mexicano."""
        if not re.match(r'^\+52\d{10}$', v):
            raise ValueError(
                f"Teléfono '{v}' tiene formato inválido. "
                f"Use formato internacional: +52 seguido de 10 dígitos (ejemplo: +526641234567)"
            )
        return v


class DatosPaciente(BaseModel):
    """
    Datos básicos de un paciente para registro.
    
    Reglas:
    - Nombre completo (mínimo 3 caracteres)
    - Teléfono validado
    """
    
    nombre_completo: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Nombre completo del paciente (mínimo 3 caracteres)"
    )
    
    telefono: TelefonoPaciente = Field(
        ...,
        description="Número de teléfono del paciente"
    )
    
    @validator('nombre_completo')
    def validar_nombre(cls, v):
        """Validar que el nombre tenga formato válido."""
        v = v.strip()
        
        if len(v) < 3:
            raise ValueError("Nombre debe tener al menos 3 caracteres")
        
        # Solo letras, espacios y acentos
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', v):
            raise ValueError(
                "Nombre solo debe contener letras y espacios (sin números ni símbolos)"
            )
        
        return v
