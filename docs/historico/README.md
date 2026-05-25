# Histórico de scripts del proyecto

Esta carpeta contiene scripts que ya no forman parte del codebase activo
pero se conservan por valor documental para la memoria del TFG.

---

## `seed_resultados.py`

Script de generación de datos simulados con **Geometric Brownian Motion** (semilla fija = 42)
usado en las fases iniciales del proyecto (Bloque 3.3 del TFG), antes de disponer de los
datos reales aportados por Alejandro Gil.

### Qué generaba

- 12 meses de series temporales diarias (días hábiles lun–vie) para las 3 primeras
  estrategias activas en BD.
- Tres perfiles de GBM diferenciados:
  - **Agresiva** — drift anual 18 %, volatilidad 25 %
  - **Equilibrada** — drift anual 10 %, volatilidad 15 %
  - **Conservadora** — drift anual 5 %, volatilidad 8 %
- Columnas generadas: `equity`, `retorno`, `drawdown`, `sharpe_ratio` (Sharpe rolling 30 días).

### Por qué se retiró

El refactor T1.1 (migración `48cbb404bf27`) rediseñó la tabla `resultado_estrategia`:
- Se eliminó la columna `sharpe_ratio` (movida a `metrica_estrategia`).
- Se añadió la columna `periodo` ('dev' | 'oos') como parte de la PK compuesta.
- El modelo GBM ya no refleja la estructura de datos reales (dev/oos split).

La BD fue truncada antes de aplicar T1.1. Los datos simulados ya no existen en producción.

### Valor documental

Se conserva para la sección de la memoria del TFG donde se comparan los datos simulados
iniciales con los datos reales finales de Alejandro Gil, como evidencia del enfoque
iterativo del desarrollo.

**Fecha de retirada del codebase activo:** 2026-05-23  
**Migración Alembic correspondiente:** `48cbb404bf27`  
**Última entrada en bitácora activa:** `docs/T3_bitacora.md` (Subtarea 3.3, Bloque 2)
