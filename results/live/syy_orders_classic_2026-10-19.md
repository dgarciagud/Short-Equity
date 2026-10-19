# Órdenes SYY semana del 2026-10-19 — Darwinex Classic

Capital 1,900 EUR (= 2,135 USD), corto bruto 1.0× ⇒ objetivo 214 USD por valor. Precios de cierre 2026-10-19; momentum hasta 2026-08-31.

Universo: 420 valores del S&P 500 disponibles en Darwinex, 419 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Abrir corto (vender) | KDP | 6 | 34.42 | 207 |
| Abrir corto (vender) | NRG | 2 | 100.13 | 200 |
| Abrir corto (vender) | XEL | 3 | 75.51 | 227 |
| Abrir corto (vender) | GPN | 3 | 83.75 | 251 |
| Cobertura: comprar SPY | SPY | 1 | 768.52 | 769 |

Tras las órdenes: 4 cortos por 885 USD frente a 1 SPY (769 USD). Cartera en construcción: faltan 6 cortos, que entrarán en las próximas semanas con el ranking de cada semana.

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_classic_2026-10-19.csv` a `data/live/holdings_classic.csv` (pon las acciones reales si difieren).

## Cartera tras las órdenes

| symbol   | mt5   | name             | sector           |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:-----------------|:-----------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper | Consumer Staples | 0.837 |             8 |   34.42  |          6 |             7.41 | 2026-08-10       |
| NRG      | NRG   | NRG Energy       | Utilities        | 0.835 |             6 |  100.13  |          2 |            30.51 | 2026-08-04       |
| XEL      | XEL   | Xcel Energy      | Utilities        | 0.834 |             7 |   75.51  |          3 |             5.32 | 2026-07-30       |
| GPN      | GPN   | Global Payments  | Financials       | 0.801 |             8 |   83.755 |          3 |            31.13 | 2026-08-05       |

## Descartados

Precio > 1,5× el objetivo por valor (1 acción pesa demasiado) o presentación de fusión/OPA ante la SEC en los últimos 180 días:

| symbol   | mt5   | name                      | sector      |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   |   fusiones_SEC |
|:---------|:------|:--------------------------|:------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|---------------:|
| WAT      | WAT   | Waters Corporation        | Health Care | 0.824 |             8 |  435.205 |          1 |        435.205 |            23.7  | 2026-08-11       |                |
| AXON     | AXON  | Axon Enterprise           | Industrials | 0.812 |             8 |  381.03  |          1 |        381.03  |            26.54 | 2026-08-06       |                |
| MLM      | MLM   | Martin Marietta Materials | Materials   | 0.802 |             8 |  500.85  |          1 |        500.85  |            23.39 | 2026-07-30       |                |
| ETN      | ETN   | Eaton Corporation         | Industrials | 0.744 |             8 |  392.88  |          1 |        392.88  |            17.8  | 2026-07-31       |            425 |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| CMS      | CMS   | CMS Energy                             | Utilities              | 0.798 |             7 |   67.87  |          3 |        203.61  |             3.15 | 2026-07-28       |                |
| COHR     | COHR  | Coherent Corp.                         | Information Technology | 0.779 |             8 |  238.042 |          1 |        238.042 |            19.05 | 2026-08-14       |                |
| BRO      | BRO   | Brown & Brown                          | Financials             | 0.752 |             7 |   68.265 |          3 |        204.795 |            23.7  | 2026-07-27       |                |
| MRVL     | MRVL  | Marvell Technology                     | Information Technology | 0.747 |             8 |  239.805 |          1 |        239.805 |            10.87 | 2026-08-28       |                |
| BA       | BA    | Boeing                                 | Industrials            | 0.746 |             8 |  189.12  |          1 |        189.12  |             9.01 | 2026-07-28       |                |
| CVNA     | CVNA  | Carvana                                | Consumer Discretionary | 0.743 |             8 |   58.85  |          4 |        235.4   |            17.2  | 2026-07-29       |                |
| NCLH     | NCLH  | Norwegian Cruise Line Holdings         | Consumer Discretionary | 0.738 |             8 |   15.115 |         14 |        211.61  |             9.87 | 2026-08-03       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.737 |             8 |   35.78  |          6 |        214.68  |            12.9  | 2026-08-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.718 |             6 |  203.49  |          1 |        203.49  |            16.57 | 2026-08-10       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.717 |             8 |  104.025 |          2 |        208.05  |             8.83 | 2026-04-29       |                |
