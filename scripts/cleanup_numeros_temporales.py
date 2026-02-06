"""
Script de Limpieza de Números Temporales Expirados

Ejecuta limpieza automática de registros en numeros_temporales_doctores
que hayan sobrepasado su tiempo de expiración.

Uso:
    python scripts/cleanup_numeros_temporales.py

Cron (cada hora):
    0 * * * * cd /path/to/project && venv/bin/python scripts/cleanup_numeros_temporales.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg
from dotenv import load_dotenv

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_config import setup_colored_logging

# Cargar variables de entorno
load_dotenv()

logger = setup_colored_logging()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/agente_whatsapp")


def limpiar_numeros_expirados() -> dict:
    """
    Elimina números temporales que ya expiraron.
    
    Returns:
        dict con estadísticas de limpieza
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Obtener registros a eliminar (para logging)
                cur.execute("""
                    SELECT 
                        nt.id, 
                        nt.numero_temporal, 
                        d.nombre_completo,
                        nt.expira_en
                    FROM numeros_temporales_doctores nt
                    JOIN doctores d ON d.id = nt.doctor_id
                    WHERE nt.expira_en IS NOT NULL 
                    AND nt.expira_en < NOW()
                """)
                
                registros_expirados = cur.fetchall()
                
                if not registros_expirados:
                    logger.info("✅ No hay números temporales expirados")
                    return {
                        'eliminados': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                
                # Eliminar registros expirados
                cur.execute("""
                    DELETE FROM numeros_temporales_doctores
                    WHERE expira_en IS NOT NULL 
                    AND expira_en < NOW()
                    RETURNING id
                """)
                
                deleted_ids = [row[0] for row in cur.fetchall()]
                conn.commit()
                
                # Logging detallado
                logger.info(f"🧹 Limpieza de números temporales expirados")
                logger.info(f"   📊 Total eliminados: {len(deleted_ids)}")
                
                for reg in registros_expirados:
                    reg_id, numero, doctor, expiracion = reg
                    logger.info(f"   • {doctor}: {numero} (expiró: {expiracion})")
                
                return {
                    'eliminados': len(deleted_ids),
                    'registros': [
                        {
                            'id': reg[0],
                            'numero': reg[1],
                            'doctor': reg[2],
                            'expiracion': reg[3].isoformat()
                        }
                        for reg in registros_expirados
                    ],
                    'timestamp': datetime.now().isoformat()
                }
    
    except psycopg.Error as e:
        logger.error(f"❌ Error de base de datos: {e}")
        return {
            'error': str(e),
            'eliminados': 0,
            'timestamp': datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return {
            'error': str(e),
            'eliminados': 0,
            'timestamp': datetime.now().isoformat()
        }


def verificar_proximos_a_expirar(horas_anticipacion: int = 2) -> list:
    """
    Verifica números que están próximos a expirar para notificaciones.
    
    Args:
        horas_anticipacion: Horas antes de expiración para alertar
    
    Returns:
        Lista de números próximos a expirar
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        nt.id,
                        nt.numero_temporal,
                        nt.numero_original,
                        d.nombre_completo,
                        nt.expira_en,
                        EXTRACT(EPOCH FROM (nt.expira_en - NOW())) / 3600 as horas_restantes
                    FROM numeros_temporales_doctores nt
                    JOIN doctores d ON d.id = nt.doctor_id
                    WHERE nt.expira_en IS NOT NULL
                    AND nt.expira_en > NOW()
                    AND nt.expira_en < NOW() + INTERVAL '%s hours'
                    ORDER BY nt.expira_en ASC
                """, (horas_anticipacion,))
                
                proximos = cur.fetchall()
                
                if proximos:
                    logger.warning(f"⚠️  {len(proximos)} número(s) temporal(es) próximo(s) a expirar:")
                    for reg in proximos:
                        reg_id, num_temp, num_orig, doctor, expira, horas = reg
                        logger.warning(f"   • {doctor}: {num_temp} (expira en {horas:.1f}h)")
                
                return [
                    {
                        'id': reg[0],
                        'numero_temporal': reg[1],
                        'numero_original': reg[2],
                        'doctor': reg[3],
                        'expira_en': reg[4].isoformat(),
                        'horas_restantes': float(reg[5])
                    }
                    for reg in proximos
                ]
    
    except Exception as e:
        logger.error(f"❌ Error verificando próximos a expirar: {e}")
        return []


def generar_reporte_activos() -> dict:
    """
    Genera reporte de números temporales actualmente activos.
    
    Returns:
        dict con estadísticas
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Contar activos
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE expira_en IS NULL) as permanentes,
                        COUNT(*) FILTER (WHERE expira_en IS NOT NULL) as temporales
                    FROM numeros_temporales_doctores
                    WHERE expira_en IS NULL OR expira_en > NOW()
                """)
                
                stats = cur.fetchone()
                
                # Detalles
                cur.execute("""
                    SELECT 
                        d.nombre_completo,
                        nt.numero_original,
                        nt.numero_temporal,
                        nt.expira_en,
                        nt.created_at
                    FROM numeros_temporales_doctores nt
                    JOIN doctores d ON d.id = nt.doctor_id
                    WHERE nt.expira_en IS NULL OR nt.expira_en > NOW()
                    ORDER BY nt.created_at DESC
                """)
                
                activos = cur.fetchall()
                
                logger.info(f"📊 Reporte de números temporales activos")
                logger.info(f"   Total: {stats[0]}")
                logger.info(f"   Permanentes: {stats[1]}")
                logger.info(f"   Temporales: {stats[2]}")
                
                return {
                    'total': stats[0],
                    'permanentes': stats[1],
                    'temporales': stats[2],
                    'detalles': [
                        {
                            'doctor': reg[0],
                            'numero_original': reg[1],
                            'numero_temporal': reg[2],
                            'expira_en': reg[3].isoformat() if reg[3] else 'Permanente',
                            'activado_en': reg[4].isoformat()
                        }
                        for reg in activos
                    ],
                    'timestamp': datetime.now().isoformat()
                }
    
    except Exception as e:
        logger.error(f"❌ Error generando reporte: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


if __name__ == "__main__":
    logger.info("="*70)
    logger.info("🧹 LIMPIEZA DE NÚMEROS TEMPORALES")
    logger.info("="*70)
    
    # 1. Limpiar expirados
    resultado_limpieza = limpiar_numeros_expirados()
    
    # 2. Verificar próximos a expirar (2 horas antes)
    proximos = verificar_proximos_a_expirar(horas_anticipacion=2)
    
    # 3. Generar reporte de activos
    reporte = generar_reporte_activos()
    
    logger.info("="*70)
    logger.info(f"✅ Limpieza completada: {resultado_limpieza.get('eliminados', 0)} eliminados")
    logger.info(f"⚠️  Próximos a expirar: {len(proximos)}")
    logger.info(f"📊 Activos totales: {reporte.get('total', 0)}")
    logger.info("="*70)
