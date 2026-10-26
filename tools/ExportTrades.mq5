//+------------------------------------------------------------------+
//| ExportTrades.mq5 - deals history and open positions to CSV        |
//| Drag onto any chart. Writes to MQL5\Files (File > Open Data      |
//| Folder > MQL5 > Files):                                           |
//|   trades_deals.csv      every deal since DaysBack                 |
//|   trades_positions.csv  open positions with open/current price    |
//+------------------------------------------------------------------+
#property script_show_inputs
input int DaysBack = 30;

void OnStart()
{
   datetime from = TimeCurrent() - DaysBack * 86400;
   if(!HistorySelect(from, TimeCurrent()))
   {
      Print("HistorySelect failed");
      return;
   }
   int h = FileOpen("trades_deals.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   FileWrite(h, "time", "deal", "position", "symbol", "type", "entry", "volume", "price",
             "commission", "swap", "profit", "fee", "comment");
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
   {
      ulong d = HistoryDealGetTicket(i);
      long type = HistoryDealGetInteger(d, DEAL_TYPE);
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      FileWrite(h, TimeToString((datetime)HistoryDealGetInteger(d, DEAL_TIME), TIME_DATE | TIME_SECONDS),
                d, HistoryDealGetInteger(d, DEAL_POSITION_ID), HistoryDealGetString(d, DEAL_SYMBOL),
                type == DEAL_TYPE_BUY ? "buy" : type == DEAL_TYPE_SELL ? "sell" : IntegerToString(type),
                entry == DEAL_ENTRY_IN ? "in" : entry == DEAL_ENTRY_OUT ? "out" : IntegerToString(entry),
                DoubleToString(HistoryDealGetDouble(d, DEAL_VOLUME), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_PRICE), 5),
                DoubleToString(HistoryDealGetDouble(d, DEAL_COMMISSION), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_SWAP), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_PROFIT), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_FEE), 2),
                HistoryDealGetString(d, DEAL_COMMENT));
   }
   FileClose(h);

   h = FileOpen("trades_positions.csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   FileWrite(h, "time_open", "position", "symbol", "type", "volume", "price_open", "price_current",
             "swap", "profit", "balance", "equity", "margin");
   int p = PositionsTotal();
   for(int i = 0; i < p; i++)
   {
      ulong t = PositionGetTicket(i);
      FileWrite(h, TimeToString((datetime)PositionGetInteger(POSITION_TIME), TIME_DATE | TIME_SECONDS), t,
                PositionGetString(POSITION_SYMBOL),
                PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "buy" : "sell",
                DoubleToString(PositionGetDouble(POSITION_VOLUME), 2),
                DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), 5),
                DoubleToString(PositionGetDouble(POSITION_PRICE_CURRENT), 5),
                DoubleToString(PositionGetDouble(POSITION_SWAP), 2),
                DoubleToString(PositionGetDouble(POSITION_PROFIT), 2),
                DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
                DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2),
                DoubleToString(AccountInfoDouble(ACCOUNT_MARGIN), 2));
   }
   FileClose(h);
   MessageBox(StringFormat("Exportadas %d operaciones y %d posiciones en MQL5\\Files", n, p), "ExportTrades");
}
