"""Script para iniciar el scheduler de recordatorios"""
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.background.recordatorios_scheduler import run_scheduler

if __name__ == '__main__':
    run_scheduler()
