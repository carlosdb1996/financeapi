import http.client
import json
import os
from flask import Flask, jsonify
from dotenv import load_dotenv

# ✅ AÑADIDO
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)

# ✅ AÑADIDO: permite peticiones desde Angular (4200) solo en /api/*
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:4200"]}})

yahoo_finance_key = os.getenv("API_KEY_YHFINANCE")
number_api = os.getenv("NUMBER_API")

RAPIDAPI_HOST = "yh-finance.p.rapidapi.com"
RAPIDAPI_KEY = yahoo_finance_key

SYMBOLS = [
    "AMD", "IBM", "AAPL", "MSFT", "GOOGL",
    "SPY", "QQQ", "VTI", "IVV", "IWM",
    "VTSAX", "VFIAX", "VWELX", "FBGRX", "SWPPX",
    "DIA", "VOO", "SCHX", "ARKK", "XLK",
    "XLF", "XLE", "XLV", "EFA", "EEM",
    "VEA", "VWO", "TLT", "IEF", "LQD",
    "HYG", "GLD", "SLV", "VNQ", "BND",
    "FXAIX", "FSMAX", "FZROX", "FZILX", "SWTSX",
    "SWISX", "SWAGX", "VBTLX", "VTIAX", "VGTSX",
    "VIGAX", "VIMAX", "VSMAX", "PRGFX", "TRBCX",
    "AMCPX", "ANCFX", "FCNTX", "FSKAX", "FSGGX"
]
REGION = "US"

prices_cache_all = []
prices_cache_stocks = []
prices_cache_etfs = []
prices_cache_funds = []
prices_cache_others = []

def load_prices_on_startup():
    global prices_cache_all, prices_cache_stocks, prices_cache_etfs, prices_cache_funds, prices_cache_others
    print("➡️  Cargando precios al arrancar (yh-finance get-quotes)...")

    try:
        conn = http.client.HTTPSConnection(RAPIDAPI_HOST, timeout=20)
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST,
            "accept": "application/json",
        }

        path = "/market/v2/get-quotes?region=" + REGION + "&symbols=" + ",".join(SYMBOLS)

        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        raw = res.read().decode("utf-8", errors="replace")

        print(f"✅ RapidAPI status: {res.status}")

        if res.status != 200:
            print("❌ Error/Preview:", raw[:800])
            prices_cache_all = []
            prices_cache_stocks = []
            prices_cache_etfs = []
            prices_cache_funds = []
            prices_cache_others = []
            return

        payload = json.loads(raw)
        quotes = payload.get("quoteResponse", {}).get("result", [])

        if not isinstance(quotes, list):
            print("⚠️ Estructura inesperada. Preview:", raw[:800])
            prices_cache_all = []
            prices_cache_stocks = []
            prices_cache_etfs = []
            prices_cache_funds = []
            prices_cache_others = []
            return

        extracted = []
        for q in quotes:
            if not isinstance(q, dict):
                continue
            extracted.append({
                "symbol": q.get("symbol"),
                "name": q.get("shortName") or q.get("longName") or q.get("symbol"),
                "price": q.get("regularMarketPrice"),
                "currency": q.get("currency"),
                "type": q.get("quoteType"),
            })

        order = {s: i for i, s in enumerate(SYMBOLS)}
        extracted.sort(key=lambda x: order.get(x.get("symbol"), 9999))

        assets_stocks, assets_etfs, assets_funds, assets_others = [], [], [], []
        for asset in extracted:
            t = asset.get("type")
            if t == "EQUITY":
                assets_stocks.append(asset)
            elif t == "ETF":
                assets_etfs.append(asset)
            elif t == "MUTUALFUND":
                assets_funds.append(asset)
            else:
                assets_others.append(asset)

        prices_cache_all = extracted
        prices_cache_stocks = assets_stocks
        prices_cache_etfs = assets_etfs
        prices_cache_funds = assets_funds
        prices_cache_others = assets_others

        print(f"✅ TOTAL: {len(prices_cache_all)}")
        print(f"   ACCIONES (EQUITY): {len(prices_cache_stocks)}")
        print(f"   ETFs: {len(prices_cache_etfs)}")
        print(f"   FONDOS (MUTUALFUND): {len(prices_cache_funds)}")

        if prices_cache_others:
            print("   Otros types:", sorted({a.get("type") for a in prices_cache_others}))

    except Exception as e:
        print("💥 Error cargando precios:", repr(e))
        prices_cache_all = []
        prices_cache_stocks = []
        prices_cache_etfs = []
        prices_cache_funds = []
        prices_cache_others = []

load_prices_on_startup()

@app.route("/api/moneymate/assets", methods=["GET"])
def assets_all():
    return jsonify(prices_cache_all)

@app.route("/api/moneymate/stocks", methods=["GET"])
def assets_stocks():
    return jsonify(prices_cache_stocks)

@app.route("/api/moneymate/etfs", methods=["GET"])
def assets_etfs():
    return jsonify(prices_cache_etfs)

@app.route("/api/moneymate/funds", methods=["GET"])
def assets_funds():
    return jsonify(prices_cache_funds)

if __name__ == "__main__":
    print("🚀 Arrancando Flask...")
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)