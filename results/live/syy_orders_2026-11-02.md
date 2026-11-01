# Órdenes SYY semana del 2026-11-02 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.5× ⇒ objetivo 45,000 USD por valor. Precios de cierre 2026-10-30; momentum hasta 2026-09-30.

Universo: 420 valores del S&P 500 disponibles en Darwinex, 419 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Abrir corto (vender) | CMS | 642 | 70.10 | 45,004 |
| Abrir corto (vender) | CVNA | 659 | 68.29 | 45,003 |
| Abrir corto (vender) | COHR | 214 | 210.32 | 45,008 |
| Cobertura: comprar SPY | SPY | 204 | 755.72 | 154,167 |

Tras las órdenes: 10 cortos por 453,833 USD frente a 601 SPY (454,188 USD).

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-11-02.csv` a `data/live/holdings.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso   |
|:--------|---------:|-------------------:|-----------:|:---------------------|:--------|
| KDP     |      7.9 |               32.1 |        3.9 | CMS (0.54)           |         |
| NRG     |      9.2 |               49.6 |       10.6 | COHR (0.18)          |         |
| XEL     |     10.4 |               27   |        6.8 | CMS (0.89)           |         |
| WAT     |     10.5 |               34.5 |        5.7 | MLM (0.23)           |         |
| AXON    |     10.2 |               62.1 |       16.9 | CVNA (0.22)          |         |
| MLM     |     10.5 |               32.6 |       11   | GPN (0.37)           |         |
| GPN     |     11.6 |               42.9 |       11.6 | KDP (0.41)           |         |
| CMS     |      9.9 |               28.1 |        6.4 | XEL (0.89)           |         |
| CVNA    |      9.9 |               56.4 |       18.7 | MLM (0.33)           |         |
| COHR    |      9.9 |               89.3 |        8.4 | NRG (0.18)           |         |

Volatilidad estimada del libro cubierto: 15.8 % anual (por unidad de corto). Ningún valor supera el 25 % del riesgo.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector                 |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples       | 0.832 |             8 |    35.84 |       1000 |             7.41 | 2026-08-10       |
| NRG      | NRG   | NRG Energy                | Utilities              | 0.836 |             6 |    96.06 |        434 |            30.51 | 2026-08-04       |
| XEL      | XEL   | Xcel Energy               | Utilities              | 0.806 |             7 |    79.82 |        590 |             5.32 | 2026-10-29       |
| WAT      | WAT   | Waters Corporation        | Health Care            | 0.826 |             8 |   462.72 |        103 |            23.7  | 2026-08-11       |
| AXON     | AXON  | Axon Enterprise           | Industrials            | 0.801 |             8 |   427.77 |        108 |            26.54 | 2026-08-06       |
| MLM      | MLM   | Martin Marietta Materials | Materials              | 0.801 |             8 |   540.41 |         88 |            23.39 | 2026-07-30       |
| GPN      | GPN   | Global Payments           | Financials             | 0.798 |             8 |    96.84 |        545 |            31.13 | 2026-08-05       |
| CMS      | CMS   | CMS Energy                | Utilities              | 0.798 |             7 |    70.1  |        642 |             3.15 | 2026-07-28       |
| CVNA     | CVNA  | Carvana                   | Consumer Discretionary | 0.785 |             8 |    68.29 |        659 |            17.2  | 2026-10-28       |
| COHR     | COHR  | Coherent Corp.            | Information Technology | 0.782 |             8 |   210.32 |        214 |            19.05 | 2026-08-14       |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| BA       | BA    | Boeing                                 | Industrials            | 0.768 |             8 |   171.55 |        262 |        44946.1 |             9.01 | 2026-10-27       |                |
| BKR      | BKR   | Baker Hughes                           | Energy                 | 0.756 |             6 |    55.23 |        815 |        45012.4 |            10.04 | 2026-10-28       |                |
| MRVL     | MRVL  | Marvell Technology                     | Information Technology | 0.746 |             8 |   196.4  |        229 |        44975.6 |            10.87 | 2026-08-28       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.736 |             8 |    38.55 |       1000 |        38550   |            12.9  | 2026-08-04       |                |
| TDG      | TDG   | TransDigm Group                        | Industrials            | 0.729 |             8 |  1146.81 |         39 |        44725.6 |            19.82 | 2026-08-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.723 |             6 |   217.75 |        207 |        45074.2 |            16.57 | 2026-08-10       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.72  |             8 |   106.2  |        424 |        45028.8 |             8.83 | 2026-04-29       |                |
| HBAN     | HBAN  | Huntington Bancshares                  | Financials             | 0.708 |             7 |    15.78 |       1000 |        15780   |             9    | 2026-10-27       |                |
| MOS      | MOS   | Mosaic Company (The)                   | Materials              | 0.697 |             8 |    18.39 |       1000 |        18390   |            11.45 | 2026-08-05       |                |
| TSLA     | TSLA  | Tesla, Inc.                            | Consumer Discretionary | 0.693 |             8 |   399.81 |        113 |        45178.5 |             3.28 | 2026-10-22       |                |
