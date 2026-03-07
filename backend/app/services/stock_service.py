from datetime import datetime

import yfinance as yf

from app.core.config import settings

DEFAULT_SYMBOL_MAP = {
    # Global indices
    "^GSPC": "S&P 500",
    "^IXIC": "NASDAQ",
    "^DJI": "Dow Jones",
    "^RUT": "Russell 2000",
    "^NSEI": "NIFTY 50",
    "^BSESN": "BSE Sensex",
    "^FTSE": "FTSE 100",
    "^GDAXI": "DAX",
    "^FCHI": "CAC 40",
    "^N225": "Nikkei 225",
    "^HSI": "Hang Seng",
    # Broad/global ETFs
    "SPY": "SPDR S&P 500 ETF",
    "QQQ": "Invesco QQQ",
    "DIA": "SPDR Dow Jones ETF",
    "IWM": "iShares Russell 2000 ETF",
    "EFA": "iShares MSCI EAFE ETF",
    "EEM": "iShares MSCI Emerging Markets ETF",
    "EWJ": "iShares MSCI Japan ETF",
    "EWG": "iShares MSCI Germany ETF",
    "EWU": "iShares MSCI UK ETF",
    "FXI": "iShares China Large-Cap ETF",
    "INDA": "iShares India 50 ETF",
    # US large caps
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "BRK-B": "Berkshire Hathaway",
    "JPM": "JPMorgan",
    "V": "Visa",
    "MA": "Mastercard",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "LLY": "Eli Lilly",
    "JNJ": "Johnson & Johnson",
    "PG": "Procter & Gamble",
    "HD": "Home Depot",
    "AVGO": "Broadcom",
    # Europe
    "ASML.AS": "ASML",
    "SHEL.L": "Shell",
    "HSBA.L": "HSBC",
    "BP.L": "BP",
    "SAP.DE": "SAP",
    # Asia
    "7203.T": "Toyota",
    "6758.T": "Sony",
    "9984.T": "SoftBank",
    "005930.KS": "Samsung Electronics",
    "000660.KS": "SK Hynix",
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFC Bank",
    "INFY.NS": "Infosys",
    "BABA": "Alibaba",
    "TSM": "TSMC",
    # Crypto
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "SOL-USD": "Solana",
    "BNB-USD": "BNB",
    "XRP-USD": "XRP",
    "DOGE-USD": "Dogecoin",
}

ETF_SYMBOLS = {
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "EFA",
    "EEM",
    "EWJ",
    "EWG",
    "EWU",
    "FXI",
    "INDA",
}


class StockService:
    def _asset_type(self, symbol: str) -> str:
        if symbol.endswith("-USD"):
            return "crypto"
        if symbol.startswith("^"):
            return "index"
        if symbol in ETF_SYMBOLS:
            return "etf"
        return "stock"

    def _symbol_map(self) -> dict[str, str]:
        raw = (settings.stock_symbols or "").strip()
        if not raw or raw.upper() == "DEFAULT":
            return dict(DEFAULT_SYMBOL_MAP)

        symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
        if "DEFAULT" in symbols:
            custom = dict(DEFAULT_SYMBOL_MAP)
            for symbol in symbols:
                if symbol == "DEFAULT":
                    continue
                custom[symbol] = DEFAULT_SYMBOL_MAP.get(symbol, symbol)
            return custom

        return {symbol: DEFAULT_SYMBOL_MAP.get(symbol, symbol) for symbol in symbols}

    def fetch_vix_proxy(self) -> float:
        try:
            vix = yf.Ticker("^VIX")
            hist = vix.history(period="5d")
            if hist.empty:
                return 20.0
            return float(hist["Close"].iloc[-1])
        except Exception:
            return 20.0

    def fetch_snapshots(self) -> list[dict]:
        vix_value = self.fetch_vix_proxy()
        snapshots: list[dict] = []
        symbols = self._symbol_map()
        min_points = max(30, int(settings.stock_min_points))
        period = settings.stock_history_period or "6mo"
        max_symbols = max(5, int(settings.stock_max_symbols))

        for symbol, name in list(symbols.items())[:max_symbols]:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
            except Exception:
                continue

            if hist.empty or len(hist) < min_points:
                continue

            close = hist["Close"]
            volume = hist["Volume"]

            latest_price = float(close.iloc[-1])
            momentum_7d = float((close.iloc[-1] - close.iloc[-8]) / close.iloc[-8] * 100)
            recent_vol = float(volume.iloc[-1])
            avg_prev_vol = float(volume.iloc[-21:-1].mean()) if float(volume.iloc[-21:-1].mean()) else 1.0
            volume_spike_pct = ((recent_vol - avg_prev_vol) / avg_prev_vol) * 100
            ma20 = float(close.iloc[-20:].mean())
            ma50 = float(close.iloc[-50:].mean())

            snapshots.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "asset_type": self._asset_type(symbol),
                    "price": latest_price,
                    "momentum_7d": round(momentum_7d, 4),
                    "volume_spike_pct": round(volume_spike_pct, 4),
                    "ma20": round(ma20, 4),
                    "ma50": round(ma50, 4),
                    "vix_proxy": round(vix_value, 4),
                    "as_of": datetime.utcnow(),
                }
            )

        return snapshots


stock_service = StockService()
