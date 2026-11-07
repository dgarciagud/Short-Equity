# Órdenes SYY semana del 2026-11-09 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.5× ⇒ objetivo 45,000 USD por valor. Precios de cierre 2026-11-06; momentum hasta 2026-09-30.

Universo: 421 valores del S&P 500 disponibles en Darwinex, 420 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Cobertura: vender SPY | SPY | 10 | 735.29 | 7,353 |

Tras las órdenes: 10 cortos por 433,713 USD frente a 590 SPY (433,821 USD).

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-11-09.csv` a `data/live/holdings.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso   |
|:--------|---------:|-------------------:|-----------:|:---------------------|:--------|
| KDP     |      8.4 |               34.5 |        4.9 | CMS (0.55)           |         |
| NRG     |      8.8 |               54   |       11.3 | COHR (0.25)          |         |
| XEL     |     10.8 |               27.8 |        7.4 | CMS (0.90)           |         |
| WAT     |     10.9 |               30.7 |        5.6 | MLM (0.24)           |         |
| AXON    |      7.8 |               65   |        9.5 | CVNA (0.17)          |         |
| MLM     |     10.5 |               33   |       11.6 | GPN (0.36)           |         |
| GPN     |     12.2 |               43.4 |       14   | KDP (0.39)           |         |
| CMS     |     10.2 |               28.9 |        7.1 | XEL (0.90)           |         |
| CVNA    |     10.7 |               57.7 |       20.5 | MLM (0.35)           |         |
| COHR    |      9.6 |               91.8 |        8.1 | NRG (0.25)           |         |

Volatilidad estimada del libro cubierto: 15.6 % anual (por unidad de corto). Ningún valor supera el 25 % del riesgo.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector                 |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples       | 0.833 |             8 |    36.63 |       1000 |             7.41 | 2026-08-10       |
| NRG      | NRG   | NRG Energy                | Utilities              | 0.836 |             6 |    88.29 |        434 |            30.51 | 2026-08-04       |
| XEL      | XEL   | Xcel Energy               | Utilities              | 0.807 |             7 |    79.67 |        590 |             5.32 | 2026-10-29       |
| WAT      | WAT   | Waters Corporation        | Health Care            | 0.826 |             8 |   457.6  |        103 |            23.7  | 2026-08-11       |
| AXON     | AXON  | Axon Enterprise           | Industrials            | 0.801 |             8 |   313    |        108 |            26.54 | 2026-08-06       |
| MLM      | MLM   | Martin Marietta Materials | Materials              | 0.802 |             8 |   518.15 |         88 |            23.39 | 2026-07-30       |
| GPN      | GPN   | Global Payments           | Financials             | 0.798 |             8 |    97.4  |        545 |            31.13 | 2026-08-05       |
| CMS      | CMS   | CMS Energy                | Utilities              | 0.798 |             7 |    69.18 |        642 |             3.15 | 2026-07-28       |
| CVNA     | CVNA  | Carvana                   | Consumer Discretionary | 0.785 |             8 |    73.57 |        629 |            17.2  | 2026-10-28       |
| COHR     | COHR  | Coherent Corp.            | Information Technology | 0.783 |             8 |   192.81 |        215 |            19.05 | 2026-08-14       |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| BA       | BA    | Boeing                                 | Industrials            | 0.768 |             8 |   173.4  |        260 |        45084   |             9.01 | 2026-10-27       |                |
| BKR      | BKR   | Baker Hughes                           | Energy                 | 0.756 |             6 |    47.87 |        940 |        44997.8 |            10.04 | 2026-10-28       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.737 |             8 |    28.73 |       1000 |        28730   |            12.9  | 2026-08-04       |                |
| TDG      | TDG   | TransDigm Group                        | Industrials            | 0.729 |             8 |  1197.01 |         38 |        45486.4 |            19.82 | 2026-08-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.724 |             6 |   228.42 |        197 |        44998.7 |            16.57 | 2026-08-10       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.72  |             8 |   109.93 |        409 |        44961.4 |             8.83 | 2026-04-29       |                |
| HBAN     | HBAN  | Huntington Bancshares                  | Financials             | 0.708 |             7 |    15.47 |       1000 |        15470   |             9    | 2026-10-27       |                |
| MOS      | MOS   | Mosaic Company (The)                   | Materials              | 0.698 |             8 |    22.36 |       1000 |        22360   |            11.45 | 2026-08-05       |                |
| TSLA     | TSLA  | Tesla, Inc.                            | Consumer Discretionary | 0.693 |             8 |   358.22 |        126 |        45135.7 |             3.28 | 2026-10-22       |                |
| AMZN     | AMZN  | Amazon                                 | Consumer Discretionary | 0.684 |             8 |   259.3  |        174 |        45118.2 |             3.91 | 2026-10-30       |                |
