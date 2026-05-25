"""Configuración raíz de pytest para el paquete backend.

Añade el directorio ``backend/`` al sys.path para que los imports
``from app...`` funcionen sin necesidad de instalar el paquete.
"""

import sys
from pathlib import Path

# Insertar la raíz del backend al frente del path
sys.path.insert(0, str(Path(__file__).parent))
