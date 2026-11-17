"""Execute a target portfolio in MetaTrader 5 (Darwinex, hedging account) from Python.

Runs on the Windows computer where MT5 is open and logged in:
    pip install MetaTrader5 pandas
    python mt5_executor.py cartera_objetivo_2026-11-17.csv            # simulation (default)
    python mt5_executor.py cartera_objetivo_2026-11-17.csv --ejecutar # sends the orders

Target file (written every week by src/live_portfolio.py): columns ticker, shares, lado
(largo|corto) and estrategia. The book is netted by symbol and compared with the open positions:
  1. close the positions that must disappear or change side (whole tickets);
  2. reduce positions that are too big by closing PART of the existing tickets, oldest first
     (in a hedging account an opposite order would open a new position instead);
  3. open or enlarge what is missing with market orders.
WARNING: any open position whose symbol is not in the target file is CLOSED (the account is
dedicated to these strategies). Resizes smaller than --tolerancia (5 % of the target) are skipped. Before every order the spread
is checked (waits up to --espera-spread seconds while it is wider than --max-spread-pb basis
points) and the order is validated with order_check (margin). Every action is logged to
ejecucion_<date>.csv and the resulting book is exported to cartera_mt5_<date>.csv, the holdings
file for next week's run.
"""
import argparse
import datetime as dt
import sys
import time

import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    sys.exit("Falta la librería: pip install MetaTrader5 (solo Windows, con MT5 instalado).")

MAGIC = 26111701
LOG = []


def log(sym, action, vol, price, result):
    LOG.append({"hora": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "símbolo": sym, "acción": action,
                "volumen": vol, "precio": price, "resultado": result})
    print(f"{action:28s} {sym:6s} {vol:>7.0f} @ {price:>10.2f}  {result}")


def mt5_symbol(ticker):
    """Darwinex names: tickers without dots, class shares as BRKb."""
    cands = [ticker.replace(".", ""), ticker]
    if "." in ticker:
        base, cls = ticker.split(".", 1)
        cands.insert(1, base + cls.lower())
    for s in cands:
        if mt5.symbol_info(s) is not None:
            return s
    return None


def filling(info):
    if info.filling_mode & 2:
        return mt5.ORDER_FILLING_IOC
    if info.filling_mode & 1:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def wait_spread(sym, max_bps, max_wait):
    t0 = time.time()
    while True:
        tick = mt5.symbol_info_tick(sym)
        if tick and tick.bid > 0 and tick.ask > 0:
            bps = (tick.ask - tick.bid) / ((tick.ask + tick.bid) / 2) * 1e4
            if bps <= max_bps:
                return tick
        if time.time() - t0 > max_wait:
            return None
        time.sleep(5)


def send(sym, side, volume, args, position=None, label=""):
    """Market order; with `position` it closes (part of) that ticket."""
    info = mt5.symbol_info(sym)
    tick = wait_spread(sym, args.max_spread_pb, args.espera_spread)
    if tick is None:
        log(sym, label, volume, 0, f"OMITIDA: spread > {args.max_spread_pb} pb")
        return False
    price = tick.ask if side == "buy" else tick.bid
    req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": sym, "volume": float(volume),
           "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL, "price": price,
           "deviation": 50, "magic": MAGIC, "comment": label[:25], "type_time": mt5.ORDER_TIME_GTC,
           "type_filling": filling(info)}
    if position is not None:
        req["position"] = position
    chk = mt5.order_check(req)
    if chk is None or chk.retcode != 0:
        log(sym, label, volume, price, f"RECHAZADA en la comprobación: {getattr(chk, 'comment', mt5.last_error())}")
        return False
    if not args.ejecutar:
        log(sym, label, volume, price, "SIMULADA")
        return True
    res = mt5.order_send(req)
    ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
    log(sym, label, volume, res.price if ok else price,
        "OK" if ok else f"ERROR {getattr(res, 'retcode', '')} {getattr(res, 'comment', mt5.last_error())}")
    return ok


def positions():
    rows = [{"ticket": p.ticket, "symbol": p.symbol, "signed": p.volume * (1 if p.type == 0 else -1),
             "volume": p.volume, "type": p.type, "time": p.time, "price_open": p.price_open}
            for p in (mt5.positions_get() or [])]
    return pd.DataFrame(rows, columns=["ticket", "symbol", "signed", "volume", "type", "time", "price_open"])


def close_volume(sym, side_type, volume, args, label):
    """Close `volume` shares of `sym` positions of type side_type (0 buy, 1 sell), oldest first."""
    left = volume
    pos = positions()
    for _, p in pos[(pos.symbol == sym) & (pos.type == side_type)].sort_values("time").iterrows():
        if left <= 0:
            break
        v = min(p.volume, left)
        if send(sym, "sell" if side_type == 0 else "buy", v, args, position=int(p.ticket), label=label):
            left -= v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("objetivo", help="cartera_objetivo_<fecha>.csv")
    ap.add_argument("--ejecutar", action="store_true", help="send real orders (default: simulation)")
    ap.add_argument("--cuenta", type=int, default=4000101021)
    ap.add_argument("--tolerancia", type=float, default=0.05)
    ap.add_argument("--max-spread-pb", type=float, default=40)
    ap.add_argument("--espera-spread", type=int, default=120, help="seconds")
    args = ap.parse_args()

    if not mt5.initialize():
        sys.exit(f"No conecta con MT5: {mt5.last_error()}. ¿Está abierto y con sesión iniciada?")
    acc = mt5.account_info()
    if acc.login != args.cuenta:
        sys.exit(f"Cuenta {acc.login} distinta de la autorizada {args.cuenta}.")
    print(f"Cuenta {acc.login}  patrimonio {acc.equity:,.2f}  margen libre {acc.margin_free:,.2f}  "
          f"{'EJECUCIÓN REAL' if args.ejecutar else 'SIMULACIÓN'}\n")

    t = pd.read_csv(args.objetivo)
    t["signed"] = t.shares * t.lado.map({"largo": 1, "corto": -1})
    t["symbol"] = t.ticker.map(mt5_symbol)
    if t.symbol.isna().any():
        print("Sin símbolo en MT5 (se ignoran):", t.loc[t.symbol.isna(), "ticker"].tolist())
        t = t.dropna(subset=["symbol"])
    for s in t.symbol:
        mt5.symbol_select(s, True)
    target = t.groupby("symbol").signed.sum()
    strategy = t.groupby("symbol").estrategia.first()

    cur = positions().groupby("symbol").signed.sum()
    syms = sorted(set(target.index) | set(cur.index))
    planned = {}
    # 1-2. close and reduce
    for s in syms:
        a, b = cur.get(s, 0), target.get(s, 0)
        planned[s] = a
        if a == 0 or a == b:
            continue
        if b == 0 or (a > 0) != (b > 0):
            close_volume(s, 0 if a > 0 else 1, abs(a), args, "CERRAR")
            planned[s] = 0
        elif abs(b) < abs(a) and abs(a) - abs(b) >= args.tolerancia * abs(b):
            close_volume(s, 0 if a > 0 else 1, abs(a) - abs(b), args, "REDUCIR")
            planned[s] = b
    # 3. open / enlarge (after real closes, re-read the account; in a simulation use the plan)
    if args.ejecutar:
        now = positions().groupby("symbol").signed.sum()
        planned = {s: now.get(s, 0) for s in syms}
    for s in syms:
        a, b = planned[s], target.get(s, 0)
        if b == 0:
            continue
        same = a != 0 and (a > 0) == (b > 0)
        if same and abs(b) <= abs(a):
            continue
        d = abs(b) - abs(a) if same else abs(b)
        if same and d < args.tolerancia * abs(b):
            continue
        send(s, "buy" if b > 0 else "sell", d, args, label="AMPLIAR" if same else "ABRIR")

    day = dt.date.today().isoformat()
    pd.DataFrame(LOG).to_csv(f"ejecucion_{day}{'' if args.ejecutar else '_simulada'}.csv", index=False)
    if args.ejecutar:
        p = positions()
        out = p.groupby("symbol").agg(signed=("signed", "sum"), precio_entrada=("price_open", "mean"),
                                      fecha=("time", "min")).reset_index()
        out["shares"] = out.signed.abs()
        out["lado"] = out.signed.gt(0).map({True: "largo", False: "corto"})
        out["estrategia"] = out.symbol.map(strategy).fillna("desconocida")
        out["fecha_entrada"] = pd.to_datetime(out.fecha, unit="s").dt.date
        out = out.rename(columns={"symbol": "ticker"})
        out[["ticker", "shares", "lado", "estrategia", "precio_entrada", "fecha_entrada"]].to_csv(
            f"cartera_mt5_{day}.csv", index=False)
        acc = mt5.account_info()
        print(f"\nPatrimonio {acc.equity:,.2f}  margen {acc.margin:,.2f}  libre {acc.margin_free:,.2f}. "
              f"Cartera exportada a cartera_mt5_{day}.csv")
    mt5.shutdown()


if __name__ == "__main__":
    main()
