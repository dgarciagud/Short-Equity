//+------------------------------------------------------------------+
//| MarginCheck.mq5 - account leverage and margin per share           |
//| Drag onto any chart. Shows the account leverage and the margin    |
//| MT5 would block for 1 share of each symbol (as % of its price).   |
//+------------------------------------------------------------------+
#property script_show_inputs
input string Symbols = "KDP,NRG,XEL,WAT,AXON,MLM,GPN,CMS,COHR,BRO,SPY";

void OnStart()
{
   string cur = AccountInfoString(ACCOUNT_CURRENCY);
   string out = StringFormat("Cuenta %I64d (%s)  apalancamiento 1:%I64d\n\n",
                             AccountInfoInteger(ACCOUNT_LOGIN), cur, AccountInfoInteger(ACCOUNT_LEVERAGE));
   string s[];
   int n = StringSplit(Symbols, ',', s);
   for(int i = 0; i < n; i++)
   {
      SymbolSelect(s[i], true);
      double bid = SymbolInfoDouble(s[i], SYMBOL_BID);
      double ask = SymbolInfoDouble(s[i], SYMBOL_ASK);
      double ms = 0, mb = 0;
      bool okS = OrderCalcMargin(ORDER_TYPE_SELL, s[i], 1.0, bid, ms);
      bool okB = OrderCalcMargin(ORDER_TYPE_BUY, s[i], 1.0, ask, mb);
      if(!okS || !okB || bid <= 0)
      {
         out += StringFormat("%-6s  sin datos (¿mercado cerrado o símbolo no disponible?)\n", s[i]);
         continue;
      }
      out += StringFormat("%-6s  precio %9.2f   margen 1 acción: corto %9.2f  largo %9.2f %s  (%.0f%% del precio)\n",
                          s[i], bid, ms, mb, cur, 100.0 * ms / bid);
   }
   Print(out);
   MessageBox(out, "MarginCheck");
}
