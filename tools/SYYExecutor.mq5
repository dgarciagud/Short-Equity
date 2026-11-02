//+------------------------------------------------------------------+
//| SYYExecutor.mq5 - executes the weekly SYY order file at a fixed   |
//| server time (Darwinex server = New York + 7 h, so the US open is  |
//| 16:30 server time all year round; default 16:35 = open + 5 min).  |
//|                                                                   |
//| Order file (MQL5\Files\<OrdersFile>, written by src/live_syy.py): |
//|   date,symbol,action,value                                        |
//|   2026-11-02,XYZ,CLOSE_SHORT,0      close every short of XYZ      |
//|   2026-11-02,CMS,OPEN_SHORT,45000   open a short of ~45 000 USD   |
//|   2026-11-02,SPY,HEDGE,0.5          long SPY = 50 % of all shorts |
//|   2026-11-02,RSP,HEDGE,0.5          long RSP = 50 % of all shorts |
//| Steps: close shorts -> open shorts -> reduce hedges -> add hedges.|
//| Shares = USD / live price, capped at MaxShares per symbol; spread |
//| and free margin are checked before every order. Every action is   |
//| logged to MQL5\Files\syy_ejecucion_<date>.csv.                    |
//| DryRun=true (default) only logs what it WOULD do.                 |
//| Runs once per day (global variable SYY_DONE_<date>).              |
//+------------------------------------------------------------------+
#include <Trade\Trade.mqh>

input string OrdersFile         = "syy_orders.csv";
input int    ExecHour           = 16;      // server time
input int    ExecMinute         = 35;
input bool   DryRun             = true;    // set to false to send real orders
input long   AllowedLogin       = 0;       // your account number (0 = any)
input int    MaxShares          = 1000;    // broker limit per stock
input double MaxSpreadBps       = 40;      // wait while the spread is wider than this
input int    SpreadWaitMinutes  = 10;      // then skip that symbol
input int    SlippagePoints     = 50;

CTrade trade;
string g_dates[], g_syms[], g_acts[];
double g_vals[];
int    g_log = INVALID_HANDLE;

int OnInit()
{
   EventSetTimer(15);
   Print("SYYExecutor listo. Ejecutará a las ", ExecHour, ":", StringFormat("%02d", ExecMinute),
         " hora del servidor. DryRun=", DryRun);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

string Today()
{
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   return StringFormat("%04d-%02d-%02d", t.year, t.mon, t.day);
}

void OnTimer()
{
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   if(t.day_of_week == 0 || t.day_of_week == 6) return;
   int now = t.hour * 60 + t.min, start = ExecHour * 60 + ExecMinute;
   if(now < start || now > start + 120) return;              // only in a 2-hour window
   string key = "SYY_DONE_" + Today() + (DryRun ? "_DRY" : "");
   if(GlobalVariableCheck(key)) return;
   GlobalVariableSet(key, 1);
   Run();
}

void Log(string sym, string act, double vol, double price, string res)
{
   Print(act, " ", sym, " ", DoubleToString(vol, 0), " @ ", DoubleToString(price, 2), " -> ", res);
   if(g_log != INVALID_HANDLE)
      FileWrite(g_log, TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS), sym, act,
                DoubleToString(vol, 0), DoubleToString(price, 4), res);
}

bool LoadOrders()
{
   int h = FileOpen(OrdersFile, FILE_READ | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("No encuentro ", OrdersFile, " en MQL5\\Files"); return false; }
   for(int i = 0; i < 4 && !FileIsEnding(h); i++) FileReadString(h);     // header
   int n = 0;
   while(!FileIsEnding(h))
   {
      string d = FileReadString(h);
      if(d == "") continue;
      string s = FileReadString(h), a = FileReadString(h);
      double v = StringToDouble(FileReadString(h));
      ArrayResize(g_dates, n + 1); ArrayResize(g_syms, n + 1); ArrayResize(g_acts, n + 1); ArrayResize(g_vals, n + 1);
      g_dates[n] = d; g_syms[n] = s; g_acts[n] = a; g_vals[n] = v;
      n++;
   }
   FileClose(h);
   return n > 0;
}

double Bid(string s) { return SymbolInfoDouble(s, SYMBOL_BID); }
double Ask(string s) { return SymbolInfoDouble(s, SYMBOL_ASK); }

bool WaitSpread(string s)
{
   SymbolSelect(s, true);
   datetime limit = TimeCurrent() + SpreadWaitMinutes * 60;
   while(true)
   {
      double b = Bid(s), a = Ask(s);
      if(b > 0 && a > 0 && (a - b) / ((a + b) / 2) * 1e4 <= MaxSpreadBps) return true;
      if(TimeCurrent() > limit) return false;
      Sleep(5000);
   }
}

double PosVolume(string s, ENUM_POSITION_TYPE type)
{
   double v = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == s && PositionGetInteger(POSITION_TYPE) == type)
         v += PositionGetDouble(POSITION_VOLUME);
   }
   return v;
}

bool IsHedge(string s)
{
   for(int i = 0; i < ArraySize(g_syms); i++)
      if(g_acts[i] == "HEDGE" && g_syms[i] == s) return true;
   return false;
}

double FitMargin(string s, ENUM_ORDER_TYPE type, double vol)
{
   double m = 0, price = (type == ORDER_TYPE_BUY ? Ask(s) : Bid(s));
   if(!OrderCalcMargin(type, s, 1.0, price, m) || m <= 0) return vol;
   double maxv = MathFloor(AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.98 / m);
   return MathMax(0, MathMin(vol, maxv));
}

void Send(string s, ENUM_ORDER_TYPE type, double vol, string act)
{
   if(vol < 1) { Log(s, act, vol, 0, "volumen 0, nada que hacer"); return; }
   if(!WaitSpread(s)) { Log(s, act, vol, 0, "OMITIDA: spread > " + DoubleToString(MaxSpreadBps, 0) + " pb"); return; }
   double v = FitMargin(s, type, vol);
   if(v < vol) Log(s, act, vol, 0, "reducida por margen a " + DoubleToString(v, 0));
   if(v < 1) return;
   double px = (type == ORDER_TYPE_BUY ? Ask(s) : Bid(s));
   if(DryRun) { Log(s, act, v, px, "SIMULADA (DryRun)"); return; }
   trade.SetTypeFillingBySymbol(s);
   bool ok = (type == ORDER_TYPE_BUY) ? trade.Buy(v, s, 0, 0, 0, "SYY " + act) : trade.Sell(v, s, 0, 0, 0, "SYY " + act);
   Log(s, act, v, trade.ResultPrice(), ok ? "OK" : "ERROR " + IntegerToString(trade.ResultRetcode()) + " " + trade.ResultRetcodeDescription());
}

void ClosePositions(string s, ENUM_POSITION_TYPE type, double vol, string act)
{
   // closes up to `vol` shares of `s` positions of `type`, oldest first (hedging account)
   if(!WaitSpread(s)) { Log(s, act, vol, 0, "OMITIDA: spread > " + DoubleToString(MaxSpreadBps, 0) + " pb"); return; }
   double left = vol;
   for(int i = 0; i < PositionsTotal() && left >= 1; i++)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != s || PositionGetInteger(POSITION_TYPE) != type) continue;
      double pv = PositionGetDouble(POSITION_VOLUME), c = MathMin(pv, left);
      double px = (type == POSITION_TYPE_BUY ? Bid(s) : Ask(s));
      if(DryRun) { Log(s, act, c, px, "SIMULADA (DryRun)"); left -= c; continue; }
      bool ok = (c >= pv) ? trade.PositionClose(tk, SlippagePoints) : trade.PositionClosePartial(tk, c, SlippagePoints);
      Log(s, act, c, trade.ResultPrice(), ok ? "OK" : "ERROR " + IntegerToString(trade.ResultRetcode()) + " " + trade.ResultRetcodeDescription());
      if(ok) { left -= c; if(c >= pv) i--; }
   }
}

void Run()
{
   if(AllowedLogin != 0 && AccountInfoInteger(ACCOUNT_LOGIN) != AllowedLogin)
   { Alert("SYYExecutor: cuenta ", AccountInfoInteger(ACCOUNT_LOGIN), " no autorizada"); return; }
   if(!LoadOrders()) return;
   string today = Today();
   if(g_dates[0] != today)
   { Alert("SYYExecutor: el fichero es del ", g_dates[0], " y hoy es ", today, ". No ejecuto nada."); return; }
   g_log = FileOpen("syy_ejecucion_" + today + (DryRun ? "_dry" : "") + ".csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   FileWrite(g_log, "time", "symbol", "action", "volume", "price", "result");
   trade.SetDeviationInPoints(SlippagePoints);
   int n = ArraySize(g_syms);

   // 1. close shorts that left the ranking
   for(int i = 0; i < n; i++)
      if(g_acts[i] == "CLOSE_SHORT")
         ClosePositions(g_syms[i], POSITION_TYPE_SELL, PosVolume(g_syms[i], POSITION_TYPE_SELL), "CERRAR_CORTO");

   // 2. open new shorts (skips a symbol already held short)
   for(int i = 0; i < n; i++)
   {
      if(g_acts[i] != "OPEN_SHORT") continue;
      string s = g_syms[i];
      SymbolSelect(s, true);
      if(PosVolume(s, POSITION_TYPE_SELL) > 0) { Log(s, "ABRIR_CORTO", 0, 0, "ya existe corto: omitida"); continue; }
      double b = Bid(s);
      if(b <= 0) { Log(s, "ABRIR_CORTO", 0, 0, "sin precio"); continue; }
      Send(s, ORDER_TYPE_SELL, MathMin(MathFloor(g_vals[i] / b + 0.5), MaxShares), "ABRIR_CORTO");
   }

   // 3. hedge targets from the live value of ALL shorts (non-hedge symbols)
   double shortUsd = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetInteger(POSITION_TYPE) != POSITION_TYPE_SELL) continue;
      string s = PositionGetString(POSITION_SYMBOL);
      if(IsHedge(s)) continue;
      shortUsd += PositionGetDouble(POSITION_VOLUME) * Ask(s);
   }
   if(DryRun)        // in a dry run the new shorts were not opened: add them to the total
      for(int i = 0; i < n; i++)
         if(g_acts[i] == "OPEN_SHORT" && PosVolume(g_syms[i], POSITION_TYPE_SELL) == 0 && Bid(g_syms[i]) > 0)
            shortUsd += MathMin(MathFloor(g_vals[i] / Bid(g_syms[i]) + 0.5), MaxShares) * Bid(g_syms[i]);
   Log("TOTAL", "VALOR_CORTOS", 0, shortUsd, "USD");

   string hs[]; double hw[], tgt[]; bool capped[];
   int m = 0;
   for(int i = 0; i < n; i++)
      if(g_acts[i] == "HEDGE")
      { ArrayResize(hs, m + 1); ArrayResize(hw, m + 1); hs[m] = g_syms[i]; hw[m] = g_vals[i]; SymbolSelect(hs[m], true); m++; }
   ArrayResize(tgt, m); ArrayResize(capped, m);
   double excess = 0, free_w = 0;
   for(int k = 0; k < m; k++)
   {
      double a = Ask(hs[k]);
      tgt[k] = a > 0 ? MathFloor(hw[k] * shortUsd / a + 0.5) : 0;
      capped[k] = tgt[k] > MaxShares;
      if(capped[k]) { excess += (tgt[k] - MaxShares) * a; tgt[k] = MaxShares; }
      else free_w += hw[k];
   }
   for(int k = 0; k < m && excess > 0 && free_w > 0; k++)        // what a capped hedge cannot take
      if(!capped[k]) tgt[k] = MathMin(MaxShares, tgt[k] + MathFloor(excess * hw[k] / free_w / Ask(hs[k]) + 0.5));

   // 4. reduce hedges first (frees margin), then 5. add
   for(int k = 0; k < m; k++)
   {
      double cur = PosVolume(hs[k], POSITION_TYPE_BUY);
      Log(hs[k], "OBJETIVO_COBERTURA", tgt[k], Ask(hs[k]), "actual " + DoubleToString(cur, 0));
      if(cur > tgt[k]) ClosePositions(hs[k], POSITION_TYPE_BUY, cur - tgt[k], "REDUCIR_COBERTURA");
   }
   for(int k = 0; k < m; k++)
   {
      double cur = PosVolume(hs[k], POSITION_TYPE_BUY);
      if(DryRun && cur > tgt[k]) continue;
      if(tgt[k] > cur) Send(hs[k], ORDER_TYPE_BUY, tgt[k] - cur, "AMPLIAR_COBERTURA");
   }
   FileClose(g_log);
   g_log = INVALID_HANDLE;
   Alert("SYYExecutor: terminado", DryRun ? " (simulación)" : "", ". Registro en MQL5\\Files\\syy_ejecucion_", today, ".csv");
}
