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

## Comparación con los factores oficiales de jkpfactors.com (`src/jkp_download.py`, `src/kelly_jkp.py`)

**Series oficiales:**
* Los 13 temas de EE. UU. sobre todas las acciones, con pesos por capitalización acotados (la serie principal de JKP).
* Los temas reconstruidos a partir de los 153 factores dentro de los grupos *mega caps* (por encima del percentil 80 de NYSE) y *large caps* (percentiles 50-80), que es el universo de Darwinex. Los archivos por tamaño publican cada factor como "característica alta menos baja", sin orientar. Se multiplica por la dirección de `Factor Details.xlsx` antes de promediar por tema, como hace JKP. Sin ese paso, Low Risk, Investment o Reversal tenían correlación −0,9 con los temas oficiales.
* Las cifras son brutas, con datos hasta diciembre de 2025.

![Oficial vs nuestro](figures/kelly2_oficial_vs_nuestro.png)

**Combinación de los 13 temas (igual peso), Sharpe y %/mes:**

| Serie | 1967-89 | 1990-2006 | 2007-16 | 2017-25 | 2012-25 |
|---|---:|---:|---:|---:|---:|
| JKP todas las acciones | 1,91 (0,25 %) | 1,12 (0,26 %) | 0,82 (0,11 %) | 0,44 (0,07 %) | 0,58 (0,08 %) |
| **JKP mega caps** | 1,33 (0,17 %) | 0,93 (0,21 %) | 0,70 (0,10 %) | 0,49 (0,06 %) | **0,52 (0,06 %)** |
| JKP large caps | 1,48 (0,23 %) | 0,85 (0,22 %) | 0,71 (0,10 %) | 0,46 (0,08 %) | 0,62 (0,10 %) |
| Nuestro CRSP top 500 | 1,78 (0,40 %) | 0,95 (0,31 %) | 0,21 (0,05 %) | – | – |
| Nuestro SEC S&P 500 | – | – | – | 0,29 (0,07 %) | 0,16 (0,03 %) |

**Correlación mensual con los temas oficiales** (mega caps). La de la combinación de los 13 es 0,50 en CRSP y 0,64 en SEC. Por tema:
* Bien reproducidos (≥ 0,6): Low Risk, Value, Momentum, Short-Term Reversal, Investment y Quality.
* Mal reproducidos: Debt Issuance (0,04 y 0,49), Seasonality (≈ 0), Low Leverage (0,4-0,7) y Profit Growth (0,4-0,6).

**Mega caps, Sharpe por tema en 2012-2025:**
* Positivos: Debt Issuance 0,46, Profit Growth 0,41, Profitability 0,37, Quality 0,37, Low Leverage 0,30 y Momentum 0,26.
* Negativos: Low Risk −0,14, Seasonality −0,13 y Size −0,04.

**Lectura de la comparación.**
1. **El decaimiento es real, pero menor de lo que daba nuestra reconstrucción.** En los factores oficiales de mega caps el Sharpe de la combinación baja de 1,3 (1967-89) a ~0,5 (2012-25), pero **no llega a cero**. Nuestra versión cae más (0,16-0,21) porque aproxima mal precisamente los temas que mejor han funcionado en la última década en grandes compañías: Debt Issuance, Profit Growth y Low Leverage. Las tres eran aproximaciones con un solo indicador, frente a los 7-12 factores de cada tema en JKP.
2. **El rendimiento absoluto es muy pequeño.** La combinación oficial en mega caps rinde ~0,06 %/mes bruto (~0,7 %/año) con una volatilidad de ~1,4 %/año. El Sharpe sale de diversificar 153 factores, no de un margen grande. Cualquier implementación con CFD (spread de 8 pb por lado y rotación de decenas de valores) cuesta más que eso, y en Darwinex Zero no hay apalancamiento para escalarla.
3. **Para implementar habría que concentrarse en los temas vivos en grandes compañías** (Quality, Profitability, Profit Growth, Debt Issuance, Momentum y Low Leverage), reconstruirlos con más fidelidad (más indicadores por tema, datos trimestrales de la SEC) y con baja rotación. Habría que comprobar antes que, con un libro concentrado, el margen supere los costes.

## Reconstrucción ampliada (≈55 indicadores) y ponderación por momentum de factores (Gupta y Kelly, 2019)

`src/factor_momentum.py` (factores oficiales de JKP) y `src/kelly_sec2.py` (SEC, S&P 500 histórico 2012-2026).

**Esquemas de ponderación entre factores**, con información disponible en *t* y Σ|w| = 1:
* **estático**: 1/σ;
* **TSFM 12m**: signo del retorno de los 12 meses anteriores / σ (especificación principal de Gupta y Kelly);
* **TSFM 1m**: signo del retorno del último mes / σ;
* **solo ganadores**: factores con retorno positivo a 12 meses, sin ponerse nunca corto en un factor;
* **XSFM**: por encima o por debajo de la mediana de los factores.

**1. Factores oficiales JKP, mega caps (153 factores), Sharpe bruto:**

| Esquema | 1967-89 | 1990-2006 | 2007-16 | 2017-25 | 1967-2025 | %/mes 1967-2025 |
|---|---:|---:|---:|---:|---:|---:|
| Estático | 1,38 | 0,84 | 0,78 | 0,35 | **0,91** | 0,15 |
| TSFM 12m | 0,59 | 0,50 | 0,38 | 0,30 | 0,47 | 0,14 |
| TSFM 1m | 1,07 | 0,32 | 0,42 | 0,31 | 0,52 | 0,16 |
| Solo ganadores 12m | 1,10 | 0,93 | 0,73 | 0,36 | 0,86 | **0,24** |
| XSFM 12m | 0,47 | 0,37 | 0,32 | 0,34 | 0,38 | 0,11 |

El momentum de factores **no mejora el Sharpe** de la combinación estática. Ponerse corto en los factores perdedores resta diversificación, porque casi todos tienen prima positiva a largo plazo. La variante **"solo ganadores"** mantiene el Sharpe y **sube la rentabilidad por unidad de exposición ~60 %**. En large caps es la mejor: 0,94 frente a 0,89, y 0,60 frente a 0,53 en 2012-2025.

**2. Reconstrucción SEC con 2-9 indicadores por tema:**
* Accruals: AC, AC/NI, ΔWC.
* Debt Issuance: Δdeuda, crecimiento de la deuda a 3 años, Δpasivo no corriente.
* Investment: AG, NOA, DPI2A, emisión de acciones a 1 y 3 años, crecimiento de inventario, PP&E, ventas y activo corriente.
* Low Leverage: L/A, A/BE, deuda/ME, deuda neta/ME, caja/A.
* Low Risk: beta a 252 días y a 60 meses, vol. idiosincrática, vol. total, máximo diario.
* Momentum: 12-1, 6-1, 9-1 y residual.
* Profit Growth: SUE, ΔROA, ΔROE, Δmargen, ΔCFO/A, trimestres seguidos de crecimiento del beneficio.
* Profitability: GP/A, ROE, beneficio operativo/BE, beneficio operativo/A, CFO/A.
* Quality: ROA, rotación del activo, margen bruto, F-score de Piotroski, O-score, variabilidad del beneficio.
* Seasonality: mismo mes del año anterior y de los años 2-5, ahora alineado con el mes de tenencia (la versión anterior tenía un mes de desfase).
* Short-Term Reversal: mes, semana, media de los 5 máximos diarios.
* Size: ME, log activos.
* Value: B/M, E/P, CF/P, S/P, A/ME, EBIT/EV.

La capitalización se calcula como acciones diluidas (cifra re-expresada en la última presentación) × cierre ajustado solo por *splits* (`src/prices_close.py`, yfinance `auto_adjust=False`). Cubre ~93 % de los casos, frente al 55 % con el *public float*.

**La fidelidad mejora mucho.** Correlación mensual con los temas oficiales de mega caps (v1 → v2): Investment 0,53 → 0,75, Low Leverage 0,43 → 0,75, Momentum 0,69 → 0,86, Profit Growth 0,57 → 0,71, Value 0,76 → 0,82, Quality 0,90 → 0,83. La de la combinación de los 13 es 0,64 → 0,66.

**Pero el rendimiento en el S&P 500 equiponderado no aparece** (2013-2026, quintiles, bruto salvo los libros):

| Cartera | %/mes | Sharpe |
|---|---:|---:|
| Factores: 55 indicadores, estático | 0,03 | 0,20 |
| Factores: TSFM 12m | −0,04 | −0,15 |
| Factores: solo ganadores 12m | 0,01 | 0,02 |
| Libro 25/25 (puntuación estática), neto Zero | 0,11 | 0,11 |
| Libro 50/50 (puntuación estática), neto Zero | −0,02 | −0,03 |
| Libro 25/25 solo ganadores, neto Zero | −0,35 | −0,25 |
| Libro 25/25 TSFM 12m, neto Zero | −0,66 | −0,40 |

En esta muestra el momentum de factores **empeora** el resultado: los factores que venían de un buen año (por ejemplo baja volatilidad en 2020-21, o *value* en 2022) se dieron la vuelta.

**Indicadores individuales con mejor Sharpe, equiponderados:** NOA 0,64, S/P 0,53, CF/P 0,43, caja/A 0,42, ΔWC 0,37, emisión de acciones 0,36, A/ME 0,36. Con ~55 pruebas, alguno saldrá por azar.

**Por qué JKP ve más que nosotros: la ponderación por capitalización.** Con terciles ponderados por capitalización, nuestra reconstrucción da un Sharpe de 0,68 en Profitability, 0,63 en Quality y 0,31 en Profit Growth, cerca de lo que publica JKP. Equiponderados dan 0,09, −0,09 y −0,02. Combinando los 13 temas, la versión por capitalización llega a 0,30 frente a 0,01. Esa prima viene de las compañías más grandes (las tecnológicas rentables de 2012-2025). Una cartera de 25-50 valores con el mismo peso no la captura.

## Todo ponderado por capitalización (`src/kelly_vw.py tope|puro`, `src/syy_vw.py`)

Darwinex solo ofrece grandes compañías, así que se rehacen los estudios SEC 2012-2026 ponderando por capitalización. La base CRSP/Chen-Pelger-Zhu no trae la capitalización en dólares (LME es un rango), así que para la historia larga la versión ponderada son los factores oficiales de JKP (ya ponderados con tope; ver arriba). Dos variantes:
* **con tope**: capitalización limitada al percentil 80 del S&P 500 cada mes, como JKP;
* **pura**: capitalización sin límite.

Terciles, como JKP.

**Temas, Sharpe 2012-2026 (bruto):**

| Tema | Iguales (v2, quintiles) | Cap. con tope | Cap. pura | JKP mega, mismo periodo |
|---|---:|---:|---:|---:|
| Accruals | 0,42* | 0,28 | −0,23 | 0,04 |
| Debt Issuance | −0,28* | −0,18 | −0,55 | 0,45 |
| Investment | 0,25* | 0,18 | 0,03 | 0,07 |
| Low Leverage | −0,05* | 0,08 | 0,21 | 0,27 |
| Low Risk | −0,27* | −0,23 | −0,07 | −0,10 |
| Momentum | 0,13* | 0,08 | 0,23 | 0,32 |
| Profit Growth | −0,02* | 0,07 | 0,31 | 0,40 |
| Profitability | 0,09* | 0,11 | **0,68** | 0,35 |
| Quality | −0,09* | 0,06 | **0,63** | 0,37 |
| Seasonality | −0,26* | −0,16 | 0,04 | −0,13 |
| Short-Term Reversal | −0,05* | −0,03 | −0,16 | −0,02 |
| Size | 0,06* | −0,03 | 0,13 | −0,06 |
| Value | 0,34* | 0,12 | 0,21 | 0,01 |

\* Equiponderado con terciles.

Correlación con los temas oficiales de mega caps: 0,6-0,9 con tope en 10 de 13 temas; menor en la versión pura.

**Combinaciones y libros (neto Darwinex Zero):**

| Cartera | Cap. con tope %/mes (Sharpe) | Cap. pura %/mes (Sharpe) | Peso máx. de un valor (pura) |
|---|---:|---:|---:|
| Factores, 55 indicadores, estático (bruto) | 0,02 (0,20) | 0,12 (0,46) | – |
| Factores, solo ganadores 12m (bruto) | −0,01 (−0,05) | 0,13 (0,24) | – |
| Factores, TSFM 12m (bruto) | −0,03 (−0,13) | 0,11 (0,23) | – |
| Libro 50/50, indicadores estático | 0,01 (0,02) | **0,70 (0,46)** | 36 % |
| Libro tercil, indicadores estático | 0,01 (0,01) | **0,50 (0,50)** | 23 % |
| Libro tercil, solo ganadores | −0,11 (−0,14) | 0,12 (0,10) | 19 % |
| Libro tercil, TSFM 12m | −0,28 (−0,31) | −0,07 (−0,05) | 18 % |

Libro tercil de cap. pura por subperiodo: +1,17 %/mes (2013-16), +0,84 (2017-21), **−0,29 (2022-26)**.

**Estrategia de cortos SYY ponderada por capitalización** (`syy_vw.py`, misma regla que la §12.b del informe principal):

| Estrategia | Iguales | Cap. con tope | Cap. pura |
|---|---:|---:|---:|
| Quintil sobrevalorado vs mercado (bruto) | 0,25 %/mes, Sharpe **0,74** | 0,23, 0,63 | 0,24, 0,34 |
| 10 cortos (máx. 3/sector) / SPY, neto Zero | 0,47 %/mes, Sharpe **0,48** | 0,34, 0,37 | 0,35, 0,32 |

**Lectura.**
1. **Con tope (lo que hace JKP), nada cambia:** los temas y libros siguen en ~0.
2. **Sin tope aparece rentabilidad** (libro tercil +0,5 %/mes neto, Sharpe 0,5), pero viene casi entera de Profitability y Quality en las mayores compañías. Un solo valor llega a pesar 20-36 % de una pata, funciona en 2013-2021 (la subida de las grandes tecnológicas rentables) y **pierde en 2022-2026**. Es una apuesta concentrada en unas pocas mega caps, no una cartera de factores diversificada.
3. **El momentum de factores tampoco ayuda ponderando por capitalización.**
4. **En la estrategia de cortos SYY, ponderar por capitalización empeora el resultado** (Sharpe 0,48 → 0,32-0,37) y concentra el riesgo: un solo corto pesa de media un 23-33 % del libro. El efecto de sobrevaloración vive en las acciones medianas del índice, no en las gigantes. **Se mantiene la ponderación igual.**

## Conclusión

1. **Históricamente, la combinación de las 13 familias es excelente en grandes compañías.** Sharpe de 1,1 bruto a nivel de factores y ~0,85 neto en un libro de 25/25, con beta de mercado ≈ −0,2.
2. **Con nuestra reconstrucción, el efecto desaparece a partir de ~2007** (CRSP 2007-2016 y SEC 2012-2026): Sharpe ≈ 0 bruto y negativo tras costes. **Con los factores oficiales de JKP no desaparece del todo:** en mega caps, Sharpe ~0,5 en 2012-2025, pero con solo ~0,06 %/mes bruto. Parte de la diferencia viene de nuestras aproximaciones de Debt Issuance, Profit Growth y Low Leverage.
3. **Ni con ~55 indicadores ni ponderando por momentum de factores aparece un margen implementable** en el S&P 500 con libros equiponderados (§ anterior). Lo único que sobrevive en grandes compañías es Profitability/Quality **ponderados por capitalización**, una apuesta muy concentrada en las mayores empresas. Opciones si se quiere seguir:
   * reducir la rotación (rebalanceo trimestral, quitar Short-Term Reversal y Seasonality o pasarlas a señales lentas);
   * reconstruir mejor los temas vivos en grandes compañías (Quality, Profitability, Profit Growth, Debt Issuance, Momentum, Low Leverage) y comprobar que su margen supera los costes;
   * buscar universos donde las anomalías sigan vivas, aunque Darwinex solo ofrece grandes compañías de EE. UU.

Reproducir: `cd src && python kelly_cpz.py && python kelly_sec.py && python kelly_figures.py && python jkp_download.py && python kelly_jkp.py && python factor_momentum.py && python prices_close.py && python kelly_sec2.py && python kelly_vw.py tope && python kelly_vw.py puro && python syy_vw.py`.
