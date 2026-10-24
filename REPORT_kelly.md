# Las 13 familias de Jensen-Kelly-Pedersen combinadas en una cartera

Rama `analisis-13-familias-kelly`. Comparte datos con la rama de la estrategia de cortos (enlaces en `data/` y `external/`).

**Objetivo.** Combinar los 13 temas de Jensen, Kelly y Pedersen (2023, *Is There a Replication Crisis in Finance?*) en una sola cartera, sobre un universo parecido al de los CFD de Darwinex (grandes compañías de EE. UU.).

## Datos y construcción

* **CRSP / Chen-Pelger-Zhu, 1967-2016** (`src/kelly_cpz.py`): las 500 mayores por capitalización cada mes, sin sesgo de supervivencia. Cada tema es la media de sus características con signo:

| Tema | Características (CPZ) |
|---|---|
| Accruals | −AC, −OA |
| Debt Issuance | −Δ12m apalancamiento *(aproximación)* |
| Investment | −Investment, −DPI2A, −NOA, −NI |
| Low Leverage | −Lev |
| Low Risk | −Beta, −IdioVol, −Variance, −Resid_Var |
| Momentum | r12_2, r12_7 |
| Profit Growth | Δ12m ROE *(aproximación)* |
| Profitability | PROF, OP, ROE |
| Quality | ROA, ATO, PCM |
| Seasonality | retorno medio del mismo mes en los 5 años anteriores *(calculado)* |
| Short-Term Reversal | −ST_REV |
| Size | −LME |
| Value | BEME, E2P, CF2P, S2P |

* **SEC con composición histórica del S&P 500, 2012-2026** (`src/kelly_sec.py`): mismas definiciones con los datos de la SEC presentados en su fecha (companyfacts) y precios de ml4t-data/AlgoSeek, el mismo pipeline que la estrategia de cortos. La capitalización se toma del *public float*. Size y Value solo cubren un 55 % de las acciones-mes, porque muchas empresas no tienen el *float* en companyfacts.
* **Carteras.** Por tema: quintil alto menos bajo, equiponderado y rebalanceo mensual. Combinadas:
  * media de los 13 temas;
  * inversa de la volatilidad (en CPZ);
  * libro implementable: puntuación compuesta = media de los 13 percentiles, N largos / N cortos, neto de costes de Darwinex Zero (spread medido u 8 pb, comisión, retención del 15 % de los dividendos del lado largo).

## Resultados

![Temas](figures/kelly1_temas.png)

| Cartera | CRSP 1967-2016 %/mes (Sharpe) | 1967-89 | 1990-2006 | 2007-16 | SEC 2012-2026 %/mes (Sharpe) |
|---|---:|---:|---:|---:|---:|
| 13 temas, igual peso (bruto) | **0,30 (1,11)**, t 8,0 | 0,40 | 0,31 | 0,05 | 0,02 (0,10) |
| Libro 10/10, neto Zero | 1,46 (0,84) | 2,16 | 1,45 | −0,15 | −0,20 (−0,12) |
| Libro 25/25, neto Zero | 1,12 (0,84) | 1,76 | 0,93 | −0,04 | −0,43 (−0,35) |
| Libro 50/50, neto Zero | 0,93 (0,87) | 1,42 | 0,86 | −0,08 | −0,25 (−0,26) |

Rotación del libro: 45-63 % al mes (Short-Term Reversal y Seasonality cambian cada mes).

**Por tema.** En CRSP hasta 2006 destacan Investment, Momentum, Short-Term Reversal, Seasonality y Value (t > 3). Desde 2007, en las 500 mayores, casi ninguno funciona. En la muestra SEC solo Size (t = 2,4, con media cobertura) e Investment (t = 1,5) son positivos. Low Leverage, Low Risk y Debt Issuance salen negativos.

**Selección fuera de muestra.** Si se eligen con datos de 1967-2006 los temas con t > 2 (Accruals, Investment, Momentum, Seasonality, Short-Term Reversal, Size y Value), su combinación da 0,04 %/mes en CRSP 2007-2016 y 0,16 %/mes bruto (Sharpe 0,49, t 1,9) en SEC 2012-2026, casi todo por Size. Con una rotación de ~50 % mensual, los costes se comerían ese margen.

## Conclusión

1. **Históricamente, la combinación de las 13 familias es excelente en grandes compañías.** Sharpe de 1,1 bruto a nivel de factores y ~0,85 neto en un libro de 25/25, con beta de mercado ≈ −0,2.
2. **Pero el efecto desaparece a partir de ~2007 en este universo**, tanto en CRSP (2007-2016) como en los datos SEC actuales (2012-2026): Sharpe ≈ 0 bruto y negativo tras costes. Coincide con la literatura sobre el decaimiento de las anomalías tras su publicación y con que en *mega/large caps* los alfas son mucho menores (el propio estudio de JKP muestra rendimientos más débiles en las grandes).
3. **Tal como está, no es implementable con rentabilidad en Darwinex.** Antes de llevarlo a real habría que:
   * reducir la rotación (rebalanceo trimestral, quitar Short-Term Reversal y Seasonality o pasarlas a señales lentas);
   * usar los factores oficiales de JKP (jkpfactors.com) para confirmar que la ausencia de efecto reciente no se debe a nuestras aproximaciones;
   * buscar universos donde las anomalías sigan vivas, aunque Darwinex solo ofrece grandes compañías de EE. UU.

Reproducir: `cd src && python kelly_cpz.py && python kelly_sec.py && python kelly_figures.py`.
