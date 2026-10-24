#!/usr/bin/env bash
# Rebuild every dataset that is NOT in git (≈490 MB) in a fresh container.
# Usage (from the repo root):  SEC_USER_AGENT="Nombre email@dominio" bash tools/setup_datos.sh
# Each step is skipped when its output already exists, so the script can be re-run safely.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$(pwd)
export SEC_USER_AGENT="${SEC_USER_AGENT:-ShortEquityResearch research@example.org}"

echo "== 1/6 Dependencias"
pip install -q pandas numpy pyarrow polars statsmodels scikit-learn lightgbm matplotlib yfinance \
    ml4t-data tabulate lxml requests gdown openpyxl

echo "== 2/6 Repositorio ML4T (librerías, descargador XBRL y barras AlgoSeek S&P 500 2017-2021)"
if [ ! -f external/machine-learning-for-trading/data/equities/market/sp500/daily_bars.parquet ]; then
    mkdir -p external
    git clone --depth 1 https://github.com/stefan-jansen/machine-learning-for-trading \
        external/machine-learning-for-trading
fi

echo "== 3/6 Chen-Pelger-Zhu (CRSP 1967-2016, 367 MB desde Google Drive)"
if [ ! -f data/cpz_panel.parquet ]; then
    mkdir -p external/cpz/dl
    if [ ! -f external/cpz/datasets/char/Char_train.npz ]; then
        gdown "https://drive.google.com/uc?id=1h9O7YwPLaRBbghtF50Cr-JmIq0aHHi4Y" -O external/cpz/dl/datasets.zip
        mkdir -p external/cpz/datasets/char
        unzip -q -j -o external/cpz/dl/datasets.zip '*Char_*.npz' -d external/cpz/datasets/char
        rm -f external/cpz/dl/datasets.zip
    fi
    (cd src && python cpz_build.py)
fi

echo "== 4/6 Precios Yahoo (ml4t-data / yfinance)"
[ -f data/yahoo_sp500_2005_2026.parquet ] || (cd src && python download_long_sample.py)
[ -f data/prices_darwinex_universe.parquet ] || (cd src && python repo_prices.py)
[ -f data/prices_sp500_pit.parquet ] || (cd src && python pit_prices.py)

echo "== 5/6 SEC companyfacts + SIC (~15 min, 10 peticiones/s)"
[ -f data/sec/sic.json ] || (cd src && python setup_sec.py)

echo "== 6/6 Paneles derivados del backtest point-in-time (opcional, ~10 min)"
[ -f results/recent/pit/panel.parquet ] || (cd src && python pit_backtest.py)

echo "Listo. Datos en $ROOT/data y $ROOT/external"
