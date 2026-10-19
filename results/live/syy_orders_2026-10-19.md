# Órdenes SYY semana del 2026-10-19 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.5× ⇒ objetivo 45,000 USD por valor. Precios de cierre 2026-10-19; momentum hasta 2026-08-31.

Universo: 420 valores del S&P 500 disponibles en Darwinex, 419 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Abrir corto (vender) | KDP | 1000 | 34.47 | 34,470 |
| Abrir corto (vender) | NRG | 443 | 101.55 | 44,987 |
| Abrir corto (vender) | XEL | 591 | 76.14 | 44,999 |
| Abrir corto (vender) | WAT | 103 | 436.51 | 44,961 |
| Cobertura: comprar SPY | SPY | 221 | 766.91 | 169,488 |

Límite de 1000 acciones por valor: KDP quedan por debajo del objetivo de 45,000 USD (la cobertura con SPY se ajusta al total real).

Tras las órdenes: 4 cortos por 169,416 USD frente a 221 SPY (169,488 USD). Cartera en construcción: faltan 6 cortos, que entrarán en las próximas semanas con el ranking de cada semana.

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-10-19.csv` a `data/live/holdings.csv` (pon las acciones reales si difieren).

## Cartera tras las órdenes

| symbol   | mt5   | name               | sector           |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:-------------------|:-----------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper   | Consumer Staples | 0.837 |             8 |    34.47 |       1000 |             7.41 | 2026-08-10       |
| NRG      | NRG   | NRG Energy         | Utilities        | 0.835 |             6 |   101.55 |        443 |            30.51 | 2026-08-04       |
| XEL      | XEL   | Xcel Energy        | Utilities        | 0.834 |             7 |    76.14 |        591 |             5.32 | 2026-07-30       |
| WAT      | WAT   | Waters Corporation | Health Care      | 0.824 |             8 |   436.51 |        103 |            23.7  | 2026-08-11       |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                           | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:-------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| AXON     | AXON  | Axon Enterprise                | Industrials            | 0.812 |             8 |  387.815 |        116 |        44986.5 |            26.54 | 2026-08-06       |                |
| MLM      | MLM   | Martin Marietta Materials      | Materials              | 0.802 |             8 |  497.87  |         90 |        44808.3 |            23.39 | 2026-07-30       |                |
| GPN      | GPN   | Global Payments                | Financials             | 0.801 |             8 |   84.15  |        535 |        45020.3 |            31.13 | 2026-08-05       |                |
| CMS      | CMS   | CMS Energy                     | Utilities              | 0.798 |             7 |   68.43  |        658 |        45026.9 |             3.15 | 2026-07-28       |                |
| COHR     | COHR  | Coherent Corp.                 | Information Technology | 0.779 |             8 |  235.625 |        191 |        45004.4 |            19.05 | 2026-08-14       |                |
| BRO      | BRO   | Brown & Brown                  | Financials             | 0.752 |             7 |   68.62  |        656 |        45014.7 |            23.7  | 2026-07-27       |                |
| MRVL     | MRVL  | Marvell Technology             | Information Technology | 0.747 |             8 |  238.367 |        189 |        45051.5 |            10.87 | 2026-08-28       |                |
| BA       | BA    | Boeing                         | Industrials            | 0.746 |             8 |  189     |        238 |        44982   |             9.01 | 2026-07-28       |                |
| CVNA     | CVNA  | Carvana                        | Consumer Discretionary | 0.743 |             8 |   58.47  |        770 |        45021.9 |            17.2  | 2026-07-29       |                |
| NCLH     | NCLH  | Norwegian Cruise Line Holdings | Consumer Discretionary | 0.738 |             8 |   14.935 |       1000 |        14935   |             9.87 | 2026-08-03       |                |
