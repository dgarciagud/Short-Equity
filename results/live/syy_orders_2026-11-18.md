# Órdenes SYY semana del 2026-11-18 — Darwinex Zero

Capital 1,000,000 USD (= 1,000,000 USD), corto bruto 0.2× ⇒ objetivo 16,490 USD por valor. Precios de cierre 2026-11-18; momentum hasta 2026-09-30.

Universo: 421 valores del S&P 500 disponibles en Darwinex, 420 con puntuación.

## Órdenes

| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |
|---|---|---:|---:|---:|
| Cobertura: comprar SPY | SPY | 586 | 732.40 | 429,186 |

Tras las órdenes: 10 cortos por 429,073 USD frente a 586 SPY (429,186 USD).

Si ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_2026-11-18.csv` a `results/live/_holdings_syy_2026-11-18.csv` (pon las acciones reales si difieren).

## Riesgo por valor (aviso, no modifica las órdenes)

| valor   |   peso_% |   vol_vs_mercado_% |   riesgo_% | más correlacionado   | aviso   |
|:--------|---------:|-------------------:|-----------:|:---------------------|:--------|
| KDP     |      8.1 |               35.9 |        5.1 | CMS (0.55)           |         |
| NRG     |      9.4 |               53.6 |       12.2 | COHR (0.30)          |         |
| XEL     |     11.1 |               27.5 |        6.7 | CMS (0.89)           |         |
| WAT     |     10.9 |               29.8 |        4.9 | MLM (0.25)           |         |
| AXON    |      7.5 |               65.2 |        7.6 | CVNA (0.16)          |         |
| MLM     |     10.4 |               32.7 |       10.1 | CMS (0.39)           |         |
| GPN     |     10.9 |               47.1 |       12.1 | KDP (0.48)           |         |
| CMS     |     10.4 |               29.1 |        6.6 | XEL (0.89)           |         |
| CVNA    |     10.7 |               57.2 |       19.2 | MLM (0.32)           |         |
| COHR    |     10.6 |               92.9 |       15.6 | NRG (0.30)           |         |

Volatilidad estimada del libro cubierto: 15.8 % anual (por unidad de corto). Ningún valor supera el 25 % del riesgo.

## Cartera tras las órdenes

| symbol   | mt5   | name                      | sector                 |     M |   n_anomalias |   precio |   acciones |   avg_spread_bps | ultimo_informe   |
|:---------|:------|:--------------------------|:-----------------------|------:|--------------:|---------:|-----------:|-----------------:|:-----------------|
| KDP      | KDP   | Keurig Dr Pepper          | Consumer Staples       | 0.81  |             8 |   34.935 |       1000 |             7.41 | 2026-11-09       |
| NRG      | NRG   | NRG Energy                | Utilities              | 0.832 |             6 |   93.14  |        434 |            30.51 | 2026-11-09       |
| XEL      | XEL   | Xcel Energy               | Utilities              | 0.809 |             7 |   80.95  |        590 |             5.32 | 2026-10-29       |
| WAT      | WAT   | Waters Corporation        | Health Care            | 0.816 |             8 |  452.825 |        103 |            23.7  | 2026-11-10       |
| AXON     | AXON  | Axon Enterprise           | Industrials            | 0.819 |             8 |  296.79  |        108 |            26.54 | 2026-11-06       |
| MLM      | MLM   | Martin Marietta Materials | Materials              | 0.873 |             8 |  506.215 |         88 |            23.39 | 2026-11-04       |
| GPN      | GPN   | Global Payments           | Financials             | 0.794 |             8 |   85.59  |        545 |            31.13 | 2026-11-05       |
| CMS      | CMS   | CMS Energy                | Utilities              | 0.798 |             7 |   69.64  |        642 |             3.15 | 2026-07-28       |
| CVNA     | CVNA  | Carvana                   | Consumer Discretionary | 0.785 |             8 |   72.79  |        629 |            17.2  | 2026-10-28       |
| COHR     | COHR  | Coherent Corp.            | Information Technology | 0.768 |             8 |  211.97  |        215 |            19.05 | 2026-11-04       |

## Descartados

Precio > 1,5× el objetivo por valor (1 acción pesa demasiado) o presentación de fusión/OPA ante la SEC en los últimos 180 días:

| symbol   | mt5   | name            | sector    |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:----------------|:----------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| D        | D     | Dominion Energy | Utilities | 0.799 |             7 |   67.08  |        246 |        16501.7 |             3.54 | 2026-05-01       | 425, DEFM14A   |
| NEE      | NEE   | NextEra Energy  | Utilities | 0.799 |             7 |   84.265 |        196 |        16515.9 |             3.25 | 2026-04-23       | 425            |

## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)

| symbol   | mt5   | name                                   | sector                 |     M |   n_anomalias |   precio |   acciones |   nocional_usd |   avg_spread_bps | ultimo_informe   | fusiones_SEC   |
|:---------|:------|:---------------------------------------|:-----------------------|------:|--------------:|---------:|-----------:|---------------:|-----------------:|:-----------------|:---------------|
| BA       | BA    | Boeing                                 | Industrials            | 0.766 |             8 |  162.67  |        101 |        16429.7 |             9.01 | 2026-10-27       |                |
| BKR      | BKR   | Baker Hughes                           | Energy                 | 0.757 |             6 |   47.806 |        345 |        16493.1 |            10.04 | 2026-10-28       |                |
| TDG      | TDG   | TransDigm Group                        | Industrials            | 0.738 |             8 | 1186.88  |         14 |        16616.3 |            19.82 | 2026-11-10       |                |
| CLX      | CLX   | Clorox                                 | Consumer Staples       | 0.733 |             6 |  107.57  |        153 |        16458.2 |            13.28 | 2026-11-02       |                |
| FIS      | FIS   | Fidelity National Information Services | Financials             | 0.733 |             8 |   26.94  |        612 |        16487.3 |            12.9  | 2026-11-04       |                |
| ABT      | ABT   | Abbott Laboratories                    | Health Care            | 0.719 |             8 |  104.78  |        157 |        16450.5 |             8.83 | 2026-11-04       |                |
| SPG      | SPG   | Simon Property Group                   | Real Estate            | 0.713 |             6 |  229.8   |         72 |        16545.6 |            16.57 | 2026-11-06       |                |
| HBAN     | HBAN  | Huntington Bancshares                  | Financials             | 0.709 |             7 |   15.125 |       1000 |        15125   |             9    | 2026-10-27       |                |
| DVN      | DVN   | Devon Energy                           | Energy                 | 0.694 |             7 |   43.32  |        381 |        16504.9 |             5.09 | 2026-11-06       |                |
| TSLA     | TSLA  | Tesla, Inc.                            | Consumer Discretionary | 0.691 |             8 |  384.881 |         43 |        16549.9 |             3.28 | 2026-10-22       |                |
