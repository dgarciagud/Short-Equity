# Órdenes SYY semana del 2026-11-23 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.2× ⇒ objetivo 16,490 USD por valor. Precios de cierre 2026-11-23; momentum hasta 2026-09-30.

Universo: 421 valores del S&P 500 disponibles en Darwinex, 420 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Cobertura: comprar SPY | SPY | 231 | 723.45 | 167,117 |

Tras las órdenes: 10 cortos por 166,906 USD frente a 231 SPY (167,117 USD).

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-11-23.csv` a `results/live/_holdings_syy_2026-11-23.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso   |
|:--------|---------:|-------------------:|-----------:|:---------------------|:--------|
| AXON    |     10.3 |               65.5 |       14.9 | CVNA (0.16)          |         |
| CMS     |     10   |               30.4 |        6.7 | XEL (0.90)           |         |
| COHR    |     10.3 |               95.3 |       11.4 | NRG (0.31)           |         |
| CVNA    |      9.2 |               57   |       14.1 | MLM (0.31)           |         |
| GPN     |     10.6 |               50.9 |       13.3 | KDP (0.52)           |         |
| KDP     |      9.9 |               36.8 |        7.2 | CMS (0.58)           |         |
| MLM     |     10.2 |               32.8 |       10.1 | CMS (0.43)           |         |
| NRG     |     10   |               54   |       12   | COHR (0.31)          |         |
| WAT     |      9.8 |               30.2 |        4.4 | MLM (0.30)           |         |
| XEL     |      9.8 |               28.3 |        5.9 | CMS (0.90)           |         |

Volatilidad estimada del libro cubierto: 16.1 % anual (por unidad de corto). Ningún valor supera el 25 % del riesgo.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector                 |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| AXON     | AXON  | Axon Enterprise           | Industrials            | 0.819 |             8 |  306.255 |         56 |            26.54 | 2026-11-06       |
| CMS      | CMS   | CMS Energy                | Utilities              | 0.799 |             7 |   70.195 |        237 |             3.15 | 2026-07-28       |
| COHR     | COHR  | Coherent Corp.            | Information Technology | 0.768 |             8 |  220.042 |         78 |            19.05 | 2026-11-04       |
| CVNA     | CVNA  | Carvana                   | Consumer Discretionary | 0.785 |             8 |   67.65  |        226 |            17.2  | 2026-10-28       |
| GPN      | GPN   | Global Payments           | Financials             | 0.794 |             8 |   91.99  |        193 |            31.13 | 2026-11-05       |
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples       | 0.81  |             8 |   35.3   |        469 |             7.41 | 2026-11-09       |
| MLM      | MLM   | Martin Marietta Materials | Materials              | 0.873 |             8 |  515.785 |         33 |            23.39 | 2026-11-04       |
| NRG      | NRG   | NRG Energy                | Utilities              | 0.832 |             6 |   94.46  |        177 |            30.51 | 2026-11-09       |
| WAT      | WAT   | Waters Corporation        | Health Care            | 0.817 |             8 |  452.485 |         36 |            23.7  | 2026-11-10       |
| XEL      | XEL   | Xcel Energy               | Utilities              | 0.809 |             7 |   80.04  |        204 |             5.32 | 2026-10-29       |

## Descartados

Precio > 1,5× el objetivo por valor (1 acción pesa demasiado) o presentación de fusión/OPA ante la SEC en los últimos 180 días:

| symbol   | mt5   | name            | sector    |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:----------------|:----------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| D        | D     | Dominion Energy | Utilities | 0.8   |             7 |   66.545 |        248 |        16503.2 |             3.54 | 2026-05-01       | 425, DEFM14A   |
| NEE      | NEE   | NextEra Energy  | Utilities | 0.799 |             7 |   83.55  |        197 |        16459.4 |             3.25 | 2026-04-23       | 425            |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| BA       | BA    | Boeing                                 | Industrials            | 0.766 |             8 |  162.225 |        102 |        16547   |             9.01 | 2026-10-27       |                |
| BKR      | BKR   | Baker Hughes                           | Energy                 | 0.758 |             6 |   46.41  |        355 |        16475.5 |            10.04 | 2026-10-28       |                |
| TDG      | TDG   | TransDigm Group                        | Industrials            | 0.737 |             8 | 1143.25  |         14 |        16005.5 |            19.82 | 2026-11-10       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.733 |             8 |   26.435 |        624 |        16495.4 |            12.9  | 2026-11-04       |                |
| CLX      | CLX   | Clorox                                 | Consumer Staples       | 0.733 |             6 |  103.405 |        159 |        16441.4 |            13.28 | 2026-11-02       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.719 |             8 |  103.32  |        160 |        16531.2 |             8.83 | 2026-11-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.713 |             6 |  226.84  |         73 |        16559.3 |            16.57 | 2026-11-06       |                |
| HBAN     | HBAN  | Huntington Bancshares                  | Financials             | 0.709 |             7 |   14.71  |       1000 |        14710   |             9    | 2026-10-27       |                |
| DVN      | DVN   | Devon Energy                           | Energy                 | 0.694 |             7 |   41.295 |        399 |        16476.7 |             5.09 | 2026-11-06       |                |
| TSLA     | TSLA  | Tesla, Inc.                            | Consumer Discretionary | 0.691 |             8 |  389.615 |         42 |        16363.8 |             3.28 | 2026-10-22       |                |
