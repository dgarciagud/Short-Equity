//+------------------------------------------------------------------+
//| ExportSymbols.mq5 - every symbol on the server (not only Market   |
//| Watch) with its category path, sector, industry and trading terms |
//| Drag onto any chart. Writes MQL5\Files\darwinex_symbols_all.csv   |
//+------------------------------------------------------------------+
#property script_show_inputs
input bool OnlyStocksAndETFs = false;   // true: skip FX, indices, commodities (contract size != 1)

string Clean(string s)
{
   StringReplace(s, ",", " ");
   StringReplace(s, "\"", "");
   return s;
}

void OnStart()
{
   int n = SymbolsTotal(false);
   int h = FileOpen("darwinex_symbols_all.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   FileWrite(h, "symbol", "path", "description", "exchange", "isin", "sector", "industry", "currency",
             "contract_size", "volume_min", "volume_max", "volume_step", "margin_initial", "swap_mode",
             "swap_long", "swap_short", "trade_mode", "bid", "ask");
   int written = 0;
   for(int i = 0; i < n; i++)
   {
      string s = SymbolName(i, false);
      double cs = SymbolInfoDouble(s, SYMBOL_TRADE_CONTRACT_SIZE);
      if(OnlyStocksAndETFs && cs != 1.0) continue;
      FileWrite(h, s, Clean(SymbolInfoString(s, SYMBOL_PATH)), Clean(SymbolInfoString(s, SYMBOL_DESCRIPTION)),
                Clean(SymbolInfoString(s, SYMBOL_EXCHANGE)), SymbolInfoString(s, SYMBOL_ISIN),
                EnumToString((ENUM_SYMBOL_SECTOR)SymbolInfoInteger(s, SYMBOL_SECTOR)),
                EnumToString((ENUM_SYMBOL_INDUSTRY)SymbolInfoInteger(s, SYMBOL_INDUSTRY)),
                SymbolInfoString(s, SYMBOL_CURRENCY_PROFIT), DoubleToString(cs, 2),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_VOLUME_MIN), 2),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_VOLUME_MAX), 2),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_VOLUME_STEP), 2),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_MARGIN_INITIAL), 2),
                IntegerToString(SymbolInfoInteger(s, SYMBOL_SWAP_MODE)),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_SWAP_LONG), 4),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_SWAP_SHORT), 4),
                IntegerToString(SymbolInfoInteger(s, SYMBOL_TRADE_MODE)),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_BID), 4),
                DoubleToString(SymbolInfoDouble(s, SYMBOL_ASK), 4));
      written++;
   }
   FileClose(h);
   MessageBox(StringFormat("Exportados %d símbolos (de %d en el servidor) a MQL5\\Files\\darwinex_symbols_all.csv",
                           written, n), "ExportSymbols");
}
