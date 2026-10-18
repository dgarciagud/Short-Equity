//+------------------------------------------------------------------+
//| SpreadLogger.mq5                                                 |
//| Samples bid/ask of every symbol in Market Watch (or a given list)|
//| during a fixed time window and writes the average spread to      |
//| MQL5/Files/spreads_<date>.csv                                     |
//|                                                                  |
//| Usage: MT5 > File > Open Data Folder > MQL5/Scripts, copy this   |
//| file, compile in MetaEditor (F7), add the stocks to Market Watch,|
//| then drag the script onto any chart DURING the US session.       |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    InpMinutes   = 60;   // sampling window (minutes)
input int    InpEverySec  = 15;   // seconds between samples
input string InpSymbols   = "";   // comma-separated list; empty = all Market Watch

struct Stat { string sym; double sum_abs; double sum_bps; double max_bps; int n; double last_mid; };

void OnStart()
{
   string syms[];
   int count = 0;
   if(StringLen(InpSymbols) > 0)
      count = StringSplit(InpSymbols, ',', syms);
   else
   {
      count = SymbolsTotal(true);
      ArrayResize(syms, count);
      for(int i = 0; i < count; i++) syms[i] = SymbolName(i, true);
   }
   Stat st[];
   ArrayResize(st, count);
   for(int i = 0; i < count; i++)
   {
      StringTrimLeft(syms[i]); StringTrimRight(syms[i]);
      SymbolSelect(syms[i], true);
      st[i].sym = syms[i]; st[i].sum_abs = 0; st[i].sum_bps = 0; st[i].max_bps = 0; st[i].n = 0;
   }

   datetime end = TimeCurrent() + InpMinutes * 60;
   while(TimeCurrent() < end && !IsStopped())
   {
      for(int i = 0; i < count; i++)
      {
         MqlTick t;
         if(!SymbolInfoTick(st[i].sym, t) || t.bid <= 0 || t.ask <= 0) continue;
         double mid = 0.5 * (t.bid + t.ask);
         double bps = 1e4 * (t.ask - t.bid) / mid;
         st[i].sum_abs += t.ask - t.bid;
         st[i].sum_bps += bps;
         if(bps > st[i].max_bps) st[i].max_bps = bps;
         st[i].n++;
         st[i].last_mid = mid;
      }
      Comment(StringFormat("SpreadLogger: %d symbols, %d s left", count, (int)(end - TimeCurrent())));
      Sleep(InpEverySec * 1000);
   }

   string fname = "spreads_" + TimeToString(TimeCurrent(), TIME_DATE) + ".csv";
   StringReplace(fname, ".", "-");
   StringReplace(fname, "-csv", ".csv");
   int h = FileOpen(fname, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("Cannot open ", fname); return; }
   FileWrite(h, "symbol", "samples", "price", "avg_spread", "avg_spread_bps", "max_spread_bps",
             "contract_size", "volume_min", "swap_long", "swap_short", "swap_mode", "margin_initial");
   for(int i = 0; i < count; i++)
   {
      if(st[i].n == 0) continue;
      FileWrite(h, st[i].sym, st[i].n, DoubleToString(st[i].last_mid, 4),
                DoubleToString(st[i].sum_abs / st[i].n, 4),
                DoubleToString(st[i].sum_bps / st[i].n, 2),
                DoubleToString(st[i].max_bps, 2),
                SymbolInfoDouble(st[i].sym, SYMBOL_TRADE_CONTRACT_SIZE),
                SymbolInfoDouble(st[i].sym, SYMBOL_VOLUME_MIN),
                SymbolInfoDouble(st[i].sym, SYMBOL_SWAP_LONG),
                SymbolInfoDouble(st[i].sym, SYMBOL_SWAP_SHORT),
                (int)SymbolInfoInteger(st[i].sym, SYMBOL_SWAP_MODE),
                SymbolInfoDouble(st[i].sym, SYMBOL_MARGIN_INITIAL));
   }
   FileClose(h);
   Comment("");
   Print("SpreadLogger: written MQL5/Files/", fname);
}
