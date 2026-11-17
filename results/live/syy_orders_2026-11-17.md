# Órdenes SYY semana del 2026-11-17 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.2× ⇒ objetivo 16,490 USD por valor. Precios de cierre 2026-11-16; momentum hasta 2026-09-30.

Universo: 421 valores del S&P 500 disponibles en Darwinex, 420 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Cobertura: comprar SPY | SPY | 583 | 739.95 | 431,391 |

Tras las órdenes: 10 cortos por 431,630 USD frente a 583 SPY (431,391 USD).

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-11-17.csv` a `results/live/_holdings_syy_2026-11-17.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso   |
|:--------|---------:|-------------------:|-----------:|:---------------------|:--------|
| KDP     |      8.2 |               36   |        5.4 | CMS (0.53)           |         |
| NRG     |      9.5 |               54.5 |       12.4 | COHR (0.30)          |         |
| XEL     |     11.1 |               27.8 |        6.7 | CMS (0.89)           |         |
| WAT     |     10.8 |               29.9 |        4.9 | MLM (0.24)           |         |
| AXON    |      7.7 |               65.2 |        8.3 | CVNA (0.16)          |         |
| MLM     |     10.4 |               33.1 |       10.5 | CMS (0.35)           |         |
| GPN     |     11.3 |               47   |       13.7 | KDP (0.47)           |         |
| CMS     |     10.5 |               29.4 |        6.7 | XEL (0.89)           |         |
| CVNA    |     10.3 |               57.4 |       18.4 | MLM (0.33)           |         |
| COHR    |     10.1 |               92.6 |       12.9 | NRG (0.30)           |         |

Volatilidad estimada del libro cubierto: 15.8 % anual (por unidad de corto). Ningún valor supera el 25 % del riesgo.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector                 |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples       | 0.81  |             8 |    35.58 |       1000 |             7.41 | 2026-11-09       |
| NRG      | NRG   | NRG Energy                | Utilities              | 0.832 |             6 |    93.99 |        434 |            30.51 | 2026-11-09       |
| XEL      | XEL   | Xcel Energy               | Utilities              | 0.809 |             7 |    81.21 |        590 |             5.32 | 2026-10-29       |
| WAT      | WAT   | Waters Corporation        | Health Care            | 0.816 |             8 |   453.42 |        103 |            23.7  | 2026-11-10       |
| AXON     | AXON  | Axon Enterprise           | Industrials            | 0.819 |             8 |   306.44 |        108 |            26.54 | 2026-11-06       |
| MLM      | MLM   | Martin Marietta Materials | Materials              | 0.873 |             8 |   510.39 |         88 |            23.39 | 2026-11-04       |
| GPN      | GPN   | Global Payments           | Financials             | 0.794 |             8 |    89.82 |        545 |            31.13 | 2026-11-05       |
| CMS      | CMS   | CMS Energy                | Utilities              | 0.798 |             7 |    70.79 |        642 |             3.15 | 2026-07-28       |
| CVNA     | CVNA  | Carvana                   | Consumer Discretionary | 0.785 |             8 |    70.74 |        629 |            17.2  | 2026-10-28       |
| COHR     | COHR  | Coherent Corp.            | Information Technology | 0.768 |             8 |   203.43 |        215 |            19.05 | 2026-11-04       |

## Descartados

Precio > 1,5× el objetivo por valor (1 acción pesa demasiado) o presentación de fusión/OPA ante la SEC en los últimos 180 días:

| symbol   | mt5   | name            | sector    |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:----------------|:----------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| D        | D     | Dominion Energy | Utilities | 0.799 |             7 |    67.8  |        243 |        16475.4 |             3.54 | 2026-05-01       | 425, DEFM14A   |
| NEE      | NEE   | NextEra Energy  | Utilities | 0.799 |             7 |    85.34 |        193 |        16470.6 |             3.25 | 2026-04-23       | 425            |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| BA       | BA    | Boeing                                 | Industrials            | 0.766 |             8 |   165.22 |        100 |        16522   |             9.01 | 2026-10-27       |                |
| BKR      | BKR   | Baker Hughes                           | Energy                 | 0.757 |             6 |    47.94 |        344 |        16491.4 |            10.04 | 2026-10-28       |                |
| TDG      | TDG   | TransDigm Group                        | Industrials            | 0.738 |             8 |  1203.21 |         14 |        16844.9 |            19.82 | 2026-11-10       |                |
| CLX      | CLX   | Clorox                                 | Consumer Staples       | 0.733 |             6 |   110.17 |        150 |        16525.5 |            13.28 | 2026-11-02       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.733 |             8 |    28.3  |        583 |        16498.9 |            12.9  | 2026-11-04       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.719 |             8 |   107.45 |        153 |        16439.8 |             8.83 | 2026-11-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.713 |             6 |   232.78 |         71 |        16527.4 |            16.57 | 2026-11-06       |                |
| HBAN     | HBAN  | Huntington Bancshares                  | Financials             | 0.709 |             7 |    15.63 |       1000 |        15630   |             9    | 2026-10-27       |                |
| DVN      | DVN   | Devon Energy                           | Energy                 | 0.694 |             7 |    44.27 |        372 |        16468.4 |             5.09 | 2026-11-06       |                |
| TSLA     | TSLA  | Tesla, Inc.                            | Consumer Discretionary | 0.691 |             8 |   379.74 |         43 |        16328.8 |             3.28 | 2026-10-22       |                |
