"""Reglas de negocio para calcular precio y comisión de estrategias al ingerir un paquete.

Estas funciones son puras (sin efectos secundarios) y deterministas dado el tipo
y nivel de riesgo de la estrategia.  Se usan en ``persistencia.py`` durante el
INSERT masivo de estrategias.
"""

from decimal import Decimal


def calcular_precio_subscripcion(tipo: str, nivel_riesgo: int) -> Decimal:
    """Devuelve el precio mensual de suscripción de la estrategia.

    Reglas:
    - tipo='benchmark'          → 0.00 € (gratis, solo comparador)
    - nivel_riesgo ∈ [1, 2]     → 9.99 €
    - nivel_riesgo ∈ [3, 4]     → 19.99 €
    - nivel_riesgo ∈ [5, 6]     → 39.99 €
    - nivel_riesgo == 7         → 59.99 €
    """
    if tipo == "benchmark":
        return Decimal("0.00")

    if nivel_riesgo <= 2:
        return Decimal("9.99")
    elif nivel_riesgo <= 4:
        return Decimal("19.99")
    elif nivel_riesgo <= 6:
        return Decimal("39.99")
    else:                          # nivel_riesgo == 7
        return Decimal("59.99")


def calcular_comision_ganancias(tipo: str) -> Decimal:
    """Devuelve el porcentaje de comisión sobre ganancias de la estrategia.

    Reglas:
    - tipo='benchmark'          → 0.00 %
    - tipo='estrategia_activa'  → 15.00 %
    """
    if tipo == "benchmark":
        return Decimal("0.00")
    return Decimal("15.00")
