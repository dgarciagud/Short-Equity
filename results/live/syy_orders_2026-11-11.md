# Órdenes SYY semana del 2026-11-11 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.5× ⇒ objetivo 45,000 USD por valor. Precios de cierre 2026-11-10; momentum hasta 2026-09-30.

Universo: 421 valores del S&P 500 disponibles en Darwinex, 420 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Cobertura: vender SPY | SPY | 3 | 749.92 | 2,250 |

Tras las órdenes: 10 cortos por 447,389 USD frente a 597 SPY (447,702 USD).

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-11-11.csv` a `data/live/holdings.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso   |
|:--------|---------:|-------------------:|-----------:|:---------------------|:--------|
| KDP     |      8.4 |               34.6 |        4.3 | CMS (0.56)           |         |
| NRG     |      9.4 |               55.2 |       13.8 | COHR (0.29)          |         |
| XEL     |     10.6 |               27.8 |        6.6 | CMS (0.90)           |         |
| WAT     |     10.9 |               30.6 |        5.6 | MLM (0.24)           |         |
| AXON    |      7.3 |               65.3 |        7.4 | CVNA (0.16)          |         |
| MLM     |     10.4 |               33   |       10.9 | GPN (0.35)           |         |
| GPN     |     12.4 |               43.8 |       13   | KDP (0.40)           |         |
| CMS     |     10   |               29   |        6.4 | XEL (0.90)           |         |
| CVNA    |     10.3 |               57.7 |       18.8 | MLM (0.34)           |         |
| COHR    |     10.3 |               92.4 |       13.1 | NRG (0.29)           |         |

Volatilidad estimada del libro cubierto: 15.7 % anual (por unidad de corto). Ningún valor supera el 25 % del riesgo.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector                 |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples       | 0.809 |             8 |    37.59 |       1000 |             7.41 | 2026-11-09       |
| NRG      | NRG   | NRG Energy                | Utilities              | 0.832 |             6 |    97.11 |        434 |            30.51 | 2026-11-09       |
| XEL      | XEL   | Xcel Energy               | Utilities              | 0.809 |             7 |    80.12 |        590 |             5.32 | 2026-10-29       |
| WAT      | WAT   | Waters Corporation        | Health Care            | 0.815 |             8 |   475.52 |        103 |            23.7  | 2026-11-10       |
| AXON     | AXON  | Axon Enterprise           | Industrials            | 0.818 |             8 |   302.54 |        108 |            26.54 | 2026-11-06       |
| MLM      | MLM   | Martin Marietta Materials | Materials              | 0.873 |             8 |   528.21 |         88 |            23.39 | 2026-11-04       |
| GPN      | GPN   | Global Payments           | Financials             | 0.794 |             8 |   101.59 |        545 |            31.13 | 2026-11-05       |
| CMS      | CMS   | CMS Energy                | Utilities              | 0.798 |             7 |    69.78 |        642 |             3.15 | 2026-07-28       |
| CVNA     | CVNA  | Carvana                   | Consumer Discretionary | 0.785 |             8 |    73.02 |        629 |            17.2  | 2026-10-28       |
| COHR     | COHR  | Coherent Corp.            | Information Technology | 0.768 |             8 |   214.66 |        215 |            19.05 | 2026-11-04       |

## Descartados

Precio > 1,5× el objetivo por valor (1 acción pesa demasiado) o presentación de fusión/OPA ante la SEC en los últimos 180 días:

| symbol   | mt5   | name            | sector    |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:----------------|:----------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| D        | D     | Dominion Energy | Utilities | 0.799 |             7 |    68.37 |        658 |        44987.5 |             3.54 | 2026-05-01       | 425, DEFM14A   |
| NEE      | NEE   | NextEra Energy  | Utilities | 0.799 |             7 |    86.27 |        522 |        45032.9 |             3.25 | 2026-04-23       | 425            |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| BA       | BA    | Boeing                                 | Industrials            | 0.766 |             8 |   173.38 |        260 |        45078.8 |             9.01 | 2026-10-27       |                |
| BKR      | BKR   | Baker Hughes                           | Energy                 | 0.757 |             6 |    47.77 |        942 |        44999.3 |            10.04 | 2026-10-28       |                |
| TDG      | TDG   | TransDigm Group                        | Industrials            | 0.738 |             8 |  1225.54 |         37 |        45345   |            19.82 | 2026-11-10       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.733 |             8 |    28.31 |       1000 |        28310   |            12.9  | 2026-11-04       |                |
| CLX      | CLX   | Clorox                                 | Consumer Staples       | 0.733 |             6 |   106.6  |        422 |        44985.2 |            13.28 | 2026-11-02       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.719 |             8 |   110.46 |        407 |        44957.2 |             8.83 | 2026-11-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.713 |             6 |   234.48 |        192 |        45020.2 |            16.57 | 2026-11-06       |                |
| HBAN     | HBAN  | Huntington Bancshares                  | Financials             | 0.709 |             7 |    15.84 |       1000 |        15840   |             9    | 2026-10-27       |                |
| DVN      | DVN   | Devon Energy                           | Energy                 | 0.694 |             7 |    43.41 |       1000 |        43410   |             5.09 | 2026-11-06       |                |
| TSLA     | TSLA  | Tesla, Inc.                            | Consumer Discretionary | 0.691 |             8 |   379.78 |        118 |        44814   |             3.28 | 2026-10-22       |                |
