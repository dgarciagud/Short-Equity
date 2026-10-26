# Órdenes SYY semana del 2026-10-26 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.5× ⇒ objetivo 45,000 USD por valor. Precios de cierre 2026-10-23; momentum hasta 2026-08-31.

Universo: 420 valores del S&P 500 disponibles en Darwinex, 419 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Abrir corto (vender) | AXON | 107 | 420.37 | 44,980 |
| Abrir corto (vender) | MLM | 89 | 507.17 | 45,138 |
| Abrir corto (vender) | GPN | 543 | 82.82 | 44,971 |
| Cobertura: comprar SPY | SPY | 177 | 759.97 | 134,515 |

Tras las órdenes: 7 cortos por 302,609 USD frente a 398 SPY (302,468 USD). Cartera en construcción: faltan 3 cortos, que entrarán en las próximas semanas con el ranking de cada semana.

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-10-26.csv` a `data/live/holdings.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso    |
|:--------|---------:|-------------------:|-----------:|:---------------------|:---------|
| KDP     |     11.5 |               32   |        8.9 | XEL (0.42)           |          |
| NRG     |     13.2 |               48.7 |       11.3 | XEL (0.18)           |          |
| XEL     |     15.2 |               27   |        9.5 | KDP (0.42)           |          |
| WAT     |     15.4 |               34.9 |       12.6 | MLM (0.24)           |          |
| AXON    |     14.9 |               60.1 |       27.3 | GPN (0.22)           | ⚠ > 25 % |
| MLM     |     14.9 |               31.2 |       14.3 | KDP (0.32)           |          |
| GPN     |     14.9 |               37.4 |       16   | KDP (0.37)           |          |

Volatilidad estimada del libro cubierto: 17.7 % anual (por unidad de corto). **Aviso: AXON aporta(n) más del 25 % del riesgo.** Valora reducir su tamaño o esperar a que la cartera tenga más nombres.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector           |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples | 0.835 |             8 |    34.68 |       1000 |             7.41 | 2026-08-10       |
| NRG      | NRG   | NRG Energy                | Utilities        | 0.836 |             6 |    92.31 |        434 |            30.51 | 2026-08-04       |
| XEL      | XEL   | Xcel Energy               | Utilities        | 0.833 |             7 |    78.05 |        590 |             5.32 | 2026-07-30       |
| WAT      | WAT   | Waters Corporation        | Health Care      | 0.824 |             8 |   453.67 |        103 |            23.7  | 2026-08-11       |
| AXON     | AXON  | Axon Enterprise           | Industrials      | 0.811 |             8 |   420.37 |        107 |            26.54 | 2026-08-06       |
| MLM      | MLM   | Martin Marietta Materials | Materials        | 0.802 |             8 |   507.17 |         89 |            23.39 | 2026-07-30       |
| GPN      | GPN   | Global Payments           | Financials       | 0.8   |             8 |    82.82 |        543 |            31.13 | 2026-08-05       |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| CMS      | CMS   | CMS Energy                             | Utilities              | 0.798 |             7 |    69.58 |        647 |        45018.3 |             3.15 | 2026-07-28       |                |
| COHR     | COHR  | Coherent Corp.                         | Information Technology | 0.78  |             8 |   209.29 |        215 |        44997.3 |            19.05 | 2026-08-14       |                |
| BRO      | BRO   | Brown & Brown                          | Financials             | 0.75  |             7 |    72.97 |        617 |        45022.5 |            23.7  | 2026-07-27       |                |
| MRVL     | MRVL  | Marvell Technology                     | Information Technology | 0.747 |             8 |   228.51 |        197 |        45016.5 |            10.87 | 2026-08-28       |                |
| BA       | BA    | Boeing                                 | Industrials            | 0.745 |             8 |   188.35 |        239 |        45015.7 |             9.01 | 2026-07-28       |                |
| CVNA     | CVNA  | Carvana                                | Consumer Discretionary | 0.743 |             8 |    57.81 |        778 |        44976.2 |            17.2  | 2026-07-29       |                |
| NCLH     | NCLH  | Norwegian Cruise Line Holdings         | Consumer Discretionary | 0.738 |             8 |    15.1  |       1000 |        15100   |             9.87 | 2026-08-03       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.736 |             8 |    37.53 |       1000 |        37530   |            12.9  | 2026-08-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.718 |             6 |   211.63 |        213 |        45077.2 |            16.57 | 2026-08-10       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.718 |             8 |   103.7  |        434 |        45005.8 |             8.83 | 2026-04-29       |                |
