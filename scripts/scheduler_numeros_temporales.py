"""
Scheduler integrado para limpieza de números temporales.
Se ejecuta como background service usando APScheduler.

Uso:
    python scripts/scheduler_numeros_temporales.py

Requiere:
    pip install apscheduler
"""

import sys
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cleanup_numeros_temporales import (
    limpiar_numeros_expirados, 
    verificar_proximos_a_expirar,
    generar_reporte_activos
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def job_limpieza():
    """Job programado para limpieza de números expirados."""
    try:
        logger.info("🔄 Ejecutando limpieza programada...")
        resultado = limpiar_numeros_expirados()
        eliminados = resultado.get('eliminados', 0)
        
        if eliminados > 0:
            logger.info(f"✅ Limpieza completada: {eliminados} número(s) eliminado(s)")
        else:
            logger.info("✅ Limpieza completada: No hay números expirados")
            
    except Exception as e:
        logger.error(f"❌ Error en job de limpieza: {e}")


def job_alertas():
    """Job programado para alertas de números próximos a expirar."""
    try:
        logger.info("🔍 Verificando números próximos a expirar...")
        proximos = verificar_proximos_a_expirar(horas_anticipacion=2)
        
        if proximos:
            logger.warning(f"⚠️  {len(proximos)} número(s) próximo(s) a expirar:")
            for num in proximos:
                logger.warning(f"   • {num['doctor']}: {num['numero_temporal']} (expira en {num['horas_restantes']:.1f}h)")
        else:
            logger.info("✅ No hay números próximos a expirar")
            
    except Exception as e:
        logger.error(f"❌ Error en job de alertas: {e}")


def job_reporte_diario():
    """Job programado para reporte diario de números activos."""
    try:
        logger.info("📊 Generando reporte diario...")
        reporte = generar_reporte_activos()
        
        logger.info("="*70)
        logger.info(f"📋 REPORTE DIARIO - Números Temporales")
        logger.info(f"   Total activos: {reporte.get('total', 0)}")
        logger.info(f"   Permanentes: {reporte.get('permanentes', 0)}")
        logger.info(f"   Temporales: {reporte.get('temporales', 0)}")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"❌ Error en job de reporte: {e}")


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    
    # Job 1: Limpieza cada hora en punto
    scheduler.add_job(
        job_limpieza,
        CronTrigger(minute=0),
        id='limpieza_numeros',
        name='Limpieza de números temporales expirados',
        replace_existing=True
    )
    
    # Job 2: Alertas cada 2 horas
    scheduler.add_job(
        job_alertas,
        CronTrigger(minute=30, hour='*/2'),
        id='alertas_expiracion',
        name='Alerta de números próximos a expirar',
        replace_existing=True
    )
    
    # Job 3: Reporte diario a las 8:00 AM
    scheduler.add_job(
        job_reporte_diario,
        CronTrigger(hour=8, minute=0),
        id='reporte_diario',
        name='Reporte diario de números activos',
        replace_existing=True
    )
    
    logger.info("="*70)
    logger.info("🚀 Scheduler de Números Temporales iniciado")
    logger.info("="*70)
    logger.info("📅 Jobs programados:")
    logger.info("   • Limpieza: Cada hora en punto")
    logger.info("   • Alertas: Cada 2 horas (XX:30)")
    logger.info("   • Reporte diario: 08:00 AM")
    logger.info("="*70)
    logger.info("Presione Ctrl+C para detener")
    logger.info("="*70)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("")
        logger.info("🛑 Scheduler detenido por el usuario")
        logger.info("="*70)
