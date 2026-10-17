"""Panel construction, short-portfolio selection, hedges, costs and statistics."""
import numpy as np
import pandas as pd
import statsmodels.api as sm

from data import period_factor_returns, rebalance_dates, supplier_customers
from signals import (customer_signal, leader_laggard, residual_signals, sector_daily,
                     window_stats)

COST_BPS = 10.0       # one-way cost per unit of traded notional (spread + commission)
BORROW_ANN = 0.01     # annual cost of holding the short (borrow / CFD financing)


def build_panel(P, freq, L, skip):
    """Long (date, symbol) frame with every signal known at the rebalance close
    and the forward return over the next holding period."""
    ret = P.ret
    rebal = rebalance_dates(P.dates, freq)
    last_days = 21 if freq == "M" else 5
    lr = np.log1p(ret)
    st = window_stats(ret, L, skip)
    last = np.expm1(lr.rolling(last_days, min_periods=last_days - 1).sum())
    vol = ret.rolling(63, min_periods=40).std()
    sec_ret, mkt = sector_daily(ret, P.sectors)
    sec_st = window_stats(sec_ret, L, skip)
    sec_1m = np.expm1(np.log1p(sec_ret).rolling(21).sum())
    rp, rid = residual_signals(ret, P.sectors, sec_ret, mkt, rebal, L, skip)
    role, lead = leader_laggard(ret, P.dollar_vol, P.sectors, rebal, last_days)
    links = supplier_customers(ret.columns)
    cust = customer_signal(ret, rebal, links, days=21)
    C = np.log1p(ret.fillna(0.0)).cumsum()
    fwd = np.expm1(C.loc[rebal].diff().shift(-1))
    present = P.close.loc[rebal].notna()

    def stack(df, name):
        return df.loc[rebal].where(present).stack(future_stack=True).rename(name)

    cols = [stack(st["pret"], "pret"), stack(st["id"], "id"), stack(st["minret"], "minret"),
            stack(last, "last"), stack(vol, "vol"), stack(rp, "rpret"), stack(rid, "rid"),
            stack(fwd, "fwd"), stack(cust, "cust"),
            role.where(present).stack(future_stack=True).rename("role")]
    df = pd.concat(cols, axis=1)
    df.index.names = ["date", "symbol"]
    df = df.dropna(subset=["pret", "id", "fwd", "last"]).reset_index()
    df["sector"] = df.symbol.map(P.sectors)
    secv = pd.concat({"sec_pret": sec_st["pret"].loc[rebal], "sec_id": sec_st["id"].loc[rebal],
                      "sec_1m": sec_1m.loc[rebal], "lead": lead}, axis=1)
    secv = secv.stack(level=1, future_stack=True)
    secv.index.names = ["date", "sector"]
    df = df.merge(secv.reset_index(), on=["date", "sector"], how="left")
    return add_ranks(df), rebal


def _q(x, n):
    """Quantile bucket 1..n (1 = lowest)."""
    r = x.rank(method="first", pct=True)
    return np.ceil(r * n).clip(1, n)


def add_ranks(df):
    g = df.groupby("date")
    df["q_pret"] = g.pret.transform(lambda x: _q(x, 5))
    df["q_last"] = g["last"].transform(lambda x: _q(x, 10))
    df["q_rpret"] = g.rpret.transform(lambda x: _q(x, 5))
    los = df.q_pret == 1
    df["t_id_los"] = np.nan
    df.loc[los, "t_id_los"] = df[los].groupby("date").id.transform(lambda x: _q(x, 3))
    df.loc[los, "t_min_los"] = df[los].groupby("date").minret.transform(lambda x: _q(x, 3))
    rlos = df.q_rpret == 1
    df.loc[rlos, "t_rid_los"] = df[rlos].groupby("date").rid.transform(lambda x: _q(x, 3))
    # sector ranks (1 = weakest of the 11 sectors)
    s = df.drop_duplicates(["date", "sector"])[["date", "sector", "sec_pret", "sec_id",
                                                 "sec_1m", "lead"]].copy()
    gs = s.groupby("date")
    s["sr_pret"] = gs.sec_pret.rank()
    s["sr_1m"] = gs.sec_1m.rank()
    s["sr_lead"] = gs.lead.rank()
    s["sec_id_low"] = s.sec_id <= gs.sec_id.transform("median")
    df = df.merge(s[["date", "sector", "sr_pret", "sr_1m", "sr_lead", "sec_id_low"]],
                  on=["date", "sector"], how="left")
    sup = df.cust.notna()
    df.loc[sup, "t_cust"] = df[sup].groupby("date").cust.transform(lambda x: _q(x, 3))
    return df


# ---- short-leg definitions ------------------------------------------------------
MOM = lambda d: d.q_pret == 1
FIP = lambda d: MOM(d) & (d.t_id_los == 1)
SEL = {
    # momentum / frog-in-the-pan vs abrupt drops
    "MOM (quintil perdedor)": MOM,
    "FIP (perdedor continuo, ID bajo)": FIP,
    "DISC (perdedor brusco, ID alto)": lambda d: MOM(d) & (d.t_id_los == 3),
    "JUMP (perdedor con mayor caida de 1 dia)": lambda d: MOM(d) & (d.t_min_los == 1),
    "CRASH (decil mayor caida ultimo periodo)": lambda d: d.q_last == 1,
    # sector as signal
    "FIP + sector perdedor (misma ventana)": lambda d: FIP(d) & (d.sr_pret <= 3),
    "FIP + sector perdedor (1 mes)": lambda d: FIP(d) & (d.sr_1m <= 3),
    "FIP + sector FIP (sector cae gradual)": lambda d: FIP(d) & (d.sec_pret < 0) & d.sec_id_low.astype(bool),
    "DISC + sector perdedor (misma ventana)": lambda d: MOM(d) & (d.t_id_los == 3) & (d.sr_pret <= 3),
    # slow diffusion
    "Rezagados (todos)": lambda d: d.role == "laggard",
    "Rezagados con lideres debiles": lambda d: (d.role == "laggard") & (d.sr_lead <= 3),
    "FIP no-lider con lideres debiles": lambda d: FIP(d) & (d.role != "leader") & (d.sr_lead <= 3),
    "Proveedores (todos)": lambda d: d.cust.notna(),
    "Proveedores con clientes debiles": lambda d: d.t_cust == 1,
    # residual momentum
    "RMOM (perdedor residual)": lambda d: d.q_rpret == 1,
    "RFIP (perdedor residual continuo)": lambda d: (d.q_rpret == 1) & (d.t_rid_los == 1),
    "RDISC (perdedor residual brusco)": lambda d: (d.q_rpret == 1) & (d.t_rid_los == 3),
}
RESIDUAL = [k for k in SEL if "residual" in k]


def _wide(df, w):
    return pd.DataFrame({"date": df.date, "symbol": df.symbol, "w": w}).pivot_table(
        index="date", columns="symbol", values="w", aggfunc="sum", fill_value=0.0)


def run_strategy(df, mask_fn, hedge="mkt", pair_col="pret", ppy=12,
                 cost_bps=COST_BPS, borrow=BORROW_ANN):
    """Period returns of the short leg alone (-R_short) and of the hedged long-short.

    Hedges: 'mkt' = EW universe; 'sector' = EW members of the same sectors as the
    shorts (same sector weights); 'pair' = top quintile by `pair_col` inside each
    shorted sector (a sector pair trade)."""
    df = df.reset_index(drop=True)
    m = mask_fn(df).fillna(False).astype(bool).values
    n_short = pd.Series(m).groupby(df.date.values).transform("sum").values
    ws = np.where(m, 1.0 / np.maximum(n_short, 1), 0.0)
    if hedge == "mkt":
        wl = 1.0 / df.groupby("date").symbol.transform("size").values
    else:
        key = [df.date, df.sector]
        share = pd.Series(ws).groupby(key).transform("sum").values
        if hedge == "pair":
            pool = (df.groupby(key)[pair_col].rank(pct=True) > 0.8).values
        else:
            pool = np.ones(len(df), bool)
        n_pool = pd.Series(pool.astype(float)).groupby(key).transform("sum").values
        wl = np.where(pool, share / np.maximum(n_pool, 1), 0.0)
    f = df.fwd.values
    r_s = pd.Series(ws * f).groupby(df.date.values).sum()
    r_l = pd.Series(wl * f).groupby(df.date.values).sum()
    n = pd.Series(m.astype(int)).groupby(df.date.values).sum()
    Ws, Wl = _wide(df, ws), _wide(df, wl)
    to_s = Ws.diff().abs().sum(axis=1)
    to_s.iloc[0] = Ws.iloc[0].abs().sum()
    to_l = Wl.diff().abs().sum(axis=1)
    to_l.iloc[0] = Wl.iloc[0].abs().sum()
    c = cost_bps / 1e4
    out = pd.DataFrame({
        "short": -r_s - c * to_s - borrow / ppy,
        "ls": r_l - r_s - c * (to_s + to_l) - borrow / ppy,
        "n": n, "turnover": to_s / 2})
    out.loc[out.n == 0, ["short", "ls"]] = np.nan
    out.index.name = "date"
    return out


def max_dd(r):
    eq = (1 + r.fillna(0)).cumprod()
    return (eq / eq.cummax() - 1).min()


def nw_t(r, lags):
    r = r.dropna()
    if len(r) < 10:
        return np.nan
    res = sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return res.tvalues[0]


def stats(r, ppy, ff=None, mom_crash=None):
    r = r.dropna()
    out = {
        "ret_anual": r.mean() * ppy,
        "vol_anual": r.std() * np.sqrt(ppy),
        "sharpe": r.mean() / r.std() * np.sqrt(ppy) if r.std() > 0 else np.nan,
        "t_NW": nw_t(r, 3 if ppy == 12 else 4),
        "hit": (r > 0).mean(),
        "skew": r.skew(),
        "peor_periodo": r.min(),
        "max_dd": max_dd(r),
        "n_periodos": len(r),
    }
    if ff is not None:
        x = ff.reindex(r.index).dropna()
        y = r.reindex(x.index)
        if len(y) > 24:
            X = sm.add_constant(x[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]])
            res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3 if ppy == 12 else 4})
            out["alfa_FF6_anual"] = res.params["const"] * ppy
            out["t_alfa"] = res.tvalues["const"]
            out["beta_mkt"] = res.params["Mkt-RF"]
            out["beta_MOM"] = res.params["MOM"]
    if mom_crash is not None:
        out["ret_en_crashes_MOM"] = r.reindex(mom_crash).mean()
    return out


def sector_strategy(df, col, ppy, n=3, cost_bps=COST_BPS, borrow=BORROW_ANN):
    """Sector-level momentum on EW sector baskets: short the n weakest sectors by
    `col`, long the n strongest (ls), or short weakest only (short)."""
    s = df.groupby(["date", "sector"]).agg(sig=(col, "first"), fwd=("fwd", "mean")).reset_index()
    rows, prev = [], None
    for d, g in s.groupby("date"):
        g = g.dropna(subset=["sig"])
        if len(g) < 2 * n:
            continue
        g = g.sort_values("sig")
        lo, hi = g.head(n), g.tail(n)
        w = pd.concat([pd.Series(-1 / n, index=lo.sector), pd.Series(1 / n, index=hi.sector)])
        to = w.sub(prev, fill_value=0).abs().sum() if prev is not None else w.abs().sum()
        c = cost_bps / 1e4
        rows.append((d, -lo.fwd.mean() - c * to / 2 - borrow / ppy,
                     hi.fwd.mean() - lo.fwd.mean() - c * to - borrow / ppy))
        prev = w
    return pd.DataFrame(rows, columns=["date", "short", "ls"]).set_index("date")


def mom_crash_dates(ff_period, k=10):
    return ff_period.MOM.nsmallest(k).index


def factor_periods(ff_daily, rebal):
    return period_factor_returns(ff_daily, rebal)
