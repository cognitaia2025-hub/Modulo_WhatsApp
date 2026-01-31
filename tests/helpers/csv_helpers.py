"""
Helpers para trabajar con fixtures CSV en tests.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def crear_resumen_dia_desde_csv(df: pd.DataFrame) -> str:
    """
    Crea resumen del día del doctor desde CSV.
    
    Simula la función obtener_resumen_dia_doctor() pero usando datos CSV
    en lugar de query SQL real.
    
    Args:
        df: DataFrame con columnas: id, doctor_id, paciente_nombre, 
            fecha_hora_inicio, estado, motivo_consulta
            
    Returns:
        String formateado igual que obtener_resumen_dia_doctor()
    """
    if len(df) == 0:
        return """📊 TUS ESTADÍSTICAS HOY:
• No tienes citas agendadas para hoy
• Día libre 🎉"""
    
    total = len(df)
    completadas = len(df[df['estado'] == 'completada'])
    pendientes = len(df[df['estado'] == 'agendada'])
    canceladas = len(df[df['estado'] == 'cancelada'])
    
    resumen = f"""📊 TUS ESTADÍSTICAS HOY:
• Citas agendadas: {total}
• Completadas: {completadas}
• Pendientes: {pendientes}"""
    
    if canceladas > 0:
        resumen += f"\n• Canceladas: {canceladas}"
    
    # Próxima cita
    df_pendientes = df[df['estado'] == 'agendada'].sort_values('fecha_hora_inicio')
    
    if len(df_pendientes) > 0:
        proxima = df_pendientes.iloc[0]
        hora = proxima['fecha_hora_inicio'].split()[1][:5]
        
        resumen += f"""

🕐 PRÓXIMA CITA:
• Paciente: {proxima['paciente_nombre']}
• Hora: {hora} (en X min)"""
        
        if proxima.get('motivo_consulta'):
            resumen += f"\n• Motivo: {proxima['motivo_consulta']}"
    else:
        resumen += "\n\n🕐 No hay más citas pendientes hoy"
    
    # Lista de pacientes
    resumen += "\n\n👥 PACIENTES DEL DÍA:"
    for numero, (idx, row) in enumerate(df.iterrows(), start=1):
        hora = row['fecha_hora_inicio'].split()[1][:5]
        emoji = "✓" if row['estado'] == "completada" else "⏳" if row['estado'] == "agendada" else "✗"
        resumen += f"\n{numero}. {row['paciente_nombre']} - {hora} {emoji}"
    
    return resumen


def load_fixture_csv(filename: str) -> pd.DataFrame:
    """
    Carga un fixture CSV desde tests/fixtures/.
    
    Args:
        filename: Nombre del archivo (ejemplo: "citas_doctor_1.csv")
        
    Returns:
        DataFrame con los datos
    """
    filepath = FIXTURES_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Fixture no encontrado: {filepath}")
    
    return pd.read_csv(filepath)
