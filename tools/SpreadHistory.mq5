//+------------------------------------------------------------------+
//| SpreadHistory.mq5                                                |
//| Average bid/ask spread of each symbol over the last N sessions,  |
//| computed from HISTORICAL data (no need to wait in real time).    |
//|                                                                  |
//| Source 1: tick history (CopyTicksRange, bid & ask of every tick).|
//| Source 2 (fallback): M1 bars, MqlRates.spread (points, the       |
//|           spread recorded for each bar).                         |
//| Only the regular US session is used (server-time window inputs). |
//| Darwinex server time is New York + 7 h: 09:30-16:00 NY =          |
//| 16:30-23:00 server. Skip the first/last minutes (auction noise). |
//|                                                                  |
//| Output: MQL5/Files/spread_history.csv                            |
//| Usage: copy to MQL5/Scripts, compile (F7), put the stocks in     |
//| Market Watch, run on any chart (any time, markets can be closed).|
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    InpDays        = 5;        // trading days to look back
input string InpSessStart   = "16:40";  // server time (NY 09:40)
input string InpSessEnd     = "22:50";  // server time (NY 15:50)
input string InpSymbols     = "";       // comma-separated; empty = all Market Watch
input bool   InpUseTicks    = true;     // try tick history first

int MinutesOf(string hhmm)
{
   string p[];
   if(StringSplit(hhmm, ':', p) != 2) return 0;
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
}

bool InSession(datetime t, int m0, int m1)
{
   MqlDateTime d; TimeToStruct(t, d);
   if(d.day_of_week == 0 || d.day_of_week == 6) return false;
   int m = d.hour * 60 + d.min;
   return m >= m0 && m <= m1;
}

void OnStart()
{
   string syms[];
   int count = 0;
   if(StringLen(InpSymbols) > 0) count = StringSplit(InpSymbols, ',', syms);
   else
   {
      count = SymbolsTotal(true);
      ArrayResize(syms, count);
      for(int i = 0; i < count; i++) syms[i] = SymbolName(i, true);
   }
   int m0 = MinutesOf(InpSessStart), m1 = MinutesOf(InpSessEnd);
   datetime to   = TimeCurrent();
   datetime from = to - (datetime)(InpDays + 4) * 86400;   // + weekend/holiday slack

   int h = FileOpen("spread_history.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("Cannot open output file"); return; }
   FileWrite(h, "symbol", "source", "obs", "avg_spread_bps", "median_spread_bps", "p90_spread_bps",
             "avg_spread_price", "last_price", "swap_long", "swap_short", "swap_mode",
             "contract_size", "volume_min", "first_obs", "last_obs");

   for(int i = 0; i < count; i++)
   {
      string s = syms[i]; StringTrimLeft(s); StringTrimRight(s);
      SymbolSelect(s, true);
      double bps[]; double absd[]; int n = 0; string src = "";
      datetime first = 0, last = 0;

      if(InpUseTicks)
      {
         MqlTick ticks[];
         int got = -1;
         for(int k = 0; k < 5 && got <= 0; k++)        // history may need to sync first
         {
            got = CopyTicksRange(s, ticks, COPY_TICKS_INFO, (ulong)from * 1000, (ulong)to * 1000);
            if(got <= 0) Sleep(1500);
         }
         if(got > 0)
         {
            ArrayResize(bps, got); ArrayResize(absd, got);
            for(int j = 0; j < got; j++)
            {
               if(ticks[j].bid <= 0 || ticks[j].ask <= 0) continue;
               if(!InSession(ticks[j].time, m0, m1)) continue;
               double mid = 0.5 * (ticks[j].bid + ticks[j].ask);
               bps[n] = 1e4 * (ticks[j].ask - ticks[j].bid) / mid;
               absd[n] = ticks[j].ask - ticks[j].bid;
               if(first == 0) first = ticks[j].time;
               last = ticks[j].time;
               n++;
            }
            src = "ticks";
         }
      }
      if(n == 0)   // fallback: M1 bars
      {
         MqlRates r[];
         int got = CopyRates(s, PERIOD_M1, from, to, r);
         double pt = SymbolInfoDouble(s, SYMBOL_POINT);
         if(got > 0)
         {
            ArrayResize(bps, got); ArrayResize(absd, got);
            for(int j = 0; j < got; j++)
            {
               if(!InSession(r[j].time, m0, m1) || r[j].close <= 0) continue;
               absd[n] = r[j].spread * pt;
               bps[n] = 1e4 * absd[n] / r[j].close;
               if(first == 0) first = r[j].time;
               last = r[j].time;
               n++;
            }
            src = "M1_bars";
         }
      }
      if(n == 0) { Print(s, ": no data"); continue; }
      ArrayResize(bps, n); ArrayResize(absd, n);
      double sum = 0, sumabs = 0;
      for(int j = 0; j < n; j++) { sum += bps[j]; sumabs += absd[j]; }
      ArraySort(bps);
      double med = bps[n / 2], p90 = bps[(int)MathMin(n - 1, (int)(0.9 * n))];
      FileWrite(h, s, src, n, DoubleToString(sum / n, 2), DoubleToString(med, 2), DoubleToString(p90, 2),
                DoubleToString(sumabs / n, 4), DoubleToString(SymbolInfoDouble(s, SYMBOL_BID), 4),
                SymbolInfoDouble(s, SYMBOL_SWAP_LONG), SymbolInfoDouble(s, SYMBOL_SWAP_SHORT),
                (int)SymbolInfoInteger(s, SYMBOL_SWAP_MODE),
                SymbolInfoDouble(s, SYMBOL_TRADE_CONTRACT_SIZE), SymbolInfoDouble(s, SYMBOL_VOLUME_MIN),
                TimeToString(first), TimeToString(last));
      Comment(StringFormat("SpreadHistory: %d/%d %s", i + 1, count, s));
   }
   FileClose(h);
   Comment("");
   Print("SpreadHistory: written MQL5/Files/spread_history.csv");
}
