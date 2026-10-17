"""Signals: momentum (PRET), information discreteness (ID, Da-Gurun-Warachka 2014),
abrupt-drop measures, sector momentum/ID, residual momentum (Blitz-Huij-Martens 2011),
leader->laggard (Hou 2007) and customer->supplier (Cohen-Frazzini 2008)."""
import numpy as np
import pandas as pd

# formation windows in trading days: (lookback L, skip S)
MONTHLY_WINDOWS = {"12-1m": (231, 21), "6-1m": (105, 21), "3-0m": (63, 0), "1-0m": (21, 0)}
WEEKLY_WINDOWS = {"52-1w": (255, 5), "26-1w": (125, 5), "13-1w": (60, 5), "4-1w": (15, 5)}


def window_stats(ret, L, skip):
    """Rolling formation stats ending `skip` days before each date.

    PRET = cumulative return; ID = sign(PRET) * (%neg days - %pos days).
    A low ID means the move came through many small same-signed days (the
    'frog in the pan'); a high ID means few large jumps (discrete information).
    MINRET = worst single-day return inside the window."""
    minp = int(0.9 * L)
    valid = ret.notna()
    n = valid.rolling(L, min_periods=minp).sum()
    pret = np.expm1(np.log1p(ret).rolling(L, min_periods=minp).sum())
    pos = (ret > 0).where(valid).astype(float).rolling(L, min_periods=minp).sum() / n
    neg = (ret < 0).where(valid).astype(float).rolling(L, min_periods=minp).sum() / n
    idd = np.sign(pret) * (neg - pos)
    minret = ret.rolling(L, min_periods=minp).min()
    out = {"pret": pret, "id": idd, "minret": minret}
    return {k: v.shift(skip) for k, v in out.items()}


def sector_daily(ret, sectors):
    """Equal-weighted daily sector index returns and EW market return."""
    sec = ret.T.groupby(sectors).mean().T
    mkt = ret.mean(axis=1)
    return sec, mkt


def residual_signals(ret, sectors, sec_ret, mkt, rebal, L, skip, beta_window=252):
    """Residual momentum at each rebalance date.

    Betas to [market, sector-minus-market] are estimated without intercept over
    `beta_window` days ending at the formation end; residuals over the formation
    window give rPRET = sum(e)/std(e) and rID = sign(sum e)*(%neg-%pos)."""
    pos_of = {d: i for i, d in enumerate(ret.index)}
    cols_ix = {c: j for j, c in enumerate(ret.columns)}
    R = ret.values
    M = mkt.values
    S = sec_ret
    rp = np.full((len(rebal), R.shape[1]), np.nan)
    rid = rp.copy()
    W = max(beta_window, L)
    for k, d in enumerate(rebal):
        e = pos_of[d] - skip
        s = e - W + 1
        if s < 0:
            continue
        Y = R[s : e + 1]
        ok = np.isfinite(Y).mean(0) >= 0.9
        m = np.nan_to_num(M[s : e + 1])
        for sec, cols in sectors[ret.columns[ok]].groupby(sectors[ret.columns[ok]]).groups.items():
            j = np.array([cols_ix[c] for c in cols])
            y = np.nan_to_num(Y[:, j])
            X = np.column_stack([m, np.nan_to_num(S[sec].values[s : e + 1]) - m])
            try:
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            except np.linalg.LinAlgError:
                continue
            res = (y - X @ beta)[-L:]
            tot = res.sum(0)
            sd = res.std(0, ddof=1)
            rp[k, j] = tot / np.where(sd > 0, sd, np.nan)
            rid[k, j] = np.sign(tot) * ((res < 0).mean(0) - (res > 0).mean(0))
    rp = pd.DataFrame(rp, index=rebal, columns=ret.columns)
    rid = pd.DataFrame(rid, index=rebal, columns=ret.columns)
    return rp, rid


def leader_laggard(ret, dollar_vol, sectors, rebal, lead_days, top=0.3):
    """Within each sector, split stocks by trailing 63d dollar volume (size proxy).

    Returns (role, leader_ret): role[d, sym] in {'leader','laggard','mid'} and the
    EW leaders' cumulative return over the last `lead_days` per sector."""
    adv = dollar_vol.rolling(63, min_periods=40).mean()
    role = pd.DataFrame("mid", index=rebal, columns=ret.columns)
    lead = pd.DataFrame(np.nan, index=rebal, columns=sorted(sectors.unique()))
    lr = np.log1p(ret)
    pos_of = {d: i for i, d in enumerate(ret.index)}
    for d in rebal:
        i = pos_of[d]
        if i < lead_days:
            continue
        a = adv.loc[d].dropna()
        a = a[ret.loc[d, a.index].notna()]
        cum = np.expm1(lr.iloc[i - lead_days + 1 : i + 1].sum(min_count=1))
        for sec, cols in a.groupby(sectors[a.index]).groups.items():
            pct = a[cols].rank(pct=True)
            ldr = pct[pct > 1 - top].index
            lag = pct[pct <= top].index
            role.loc[d, ldr] = "leader"
            role.loc[d, lag] = "laggard"
            lead.loc[d, sec] = cum[ldr].mean()
    return role, lead


def customer_signal(ret, rebal, links, days=21):
    """Supplier-level signal: EW cumulative return of its customers over `days`."""
    lr = np.log1p(ret)
    cum = np.expm1(lr.rolling(days, min_periods=int(0.8 * days)).sum()).loc[rebal]
    out = pd.DataFrame(np.nan, index=rebal, columns=ret.columns)
    for sup, custs in links.items():
        out[sup] = cum[custs].mean(axis=1)
    return out
