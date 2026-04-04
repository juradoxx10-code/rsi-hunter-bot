import os, time, requests, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "PON_TU_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "PON_TU_CHAT_ID_AQUI")
RSI_OVERBOUGHT   = int(os.getenv("RSI_OB", "80"))
RSI_OVERSOLD     = int(os.getenv("RSI_OS", "20"))
CHECK_INTERVAL   = int(os.getenv("CHECK_INTERVAL", "60"))
RSI_PERIOD       = 14

# Pares disponibles en Futuros de Bybit (USDT Perpetual)
PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "SHIBUSDT", "DOTUSDT",
    "LINKUSDT", "TRXUSDT", "MATICUSDT", "LTCUSDT", "BCHUSDT",
    "UNIUSDT", "ATOMUSDT", "XLMUSDT", "ETCUSDT", "FILUSDT",
    "APTUSDT", "ARBUSDT", "OPUSDT", "NEARUSDT", "INJUSDT",
    "SUIUSDT", "TIAUSDT", "SEIUSDT", "PEPEUSDT", "WIFUSDT",
    "FETUSDT", "RNDRUSDT", "GRTUSDT", "SANDUSDT", "AXSUSDT",
    "MANAUSDT", "CHZUSDT", "GALAUSDT", "IMXUSDT",
    "LDOUSDT", "AAVEUSDT", "MKRUSDT", "SNXUSDT", "CRVUSDT",
    "COMPUSDT", "YFIUSDT", "SUSHIUSDT", "ALGOUSDT",
    "EGLDUSDT", "HBARUSDT", "ICPUSDT", "VETUSDT", "THETAUSDT",
    "FTMUSDT", "ZILUSDT", "NEOUSDT", "EOSUSDT",
    "XTZUSDT", "ZECUSDT", "KAVAUSDT",
    "FLOWUSDT", "MINAUSDT", "ANKRUSDT", "STXUSDT",
    "BANDUSDT", "OCEANUSDT", "MASKUSDT", "GMXUSDT",
    "DYDXUSDT", "SKLUSDT", "STORJUSDT",
]

last_state = {}
alert_count = 0

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d >= 0: gains += d
        else: losses -= d
    ag = gains / period
    al = losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
    if al == 0: return 100.0
    return 100.0 - (100.0 / (1.0 + ag / al))

def fetch_rsi_bybit(symbol):
    """Obtiene velas de Bybit Futuros (5m) y calcula RSI. Sin bloqueos geográficos."""
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",   # Futuros USDT Perpetual
        "symbol": symbol,
        "interval": "5",        # 5 minutos
        "limit": 100
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 429:
            log.warning("Rate limit Bybit — esperando 10s")
            time.sleep(10)
            return None, None
        r.raise_for_status()
        data = r.json()

        if data.get("retCode") != 0:
            log.warning(f"Par no existe en Bybit: {symbol} — {data.get('retMsg')}")
            return None, None

        klines = data["result"]["list"]
        if not klines or len(klines) < RSI_PERIOD + 1:
            return None, None

        # Bybit devuelve velas en orden descendente, hay que invertirlas
        klines = list(reversed(klines))
        closes = [float(k[4]) for k in klines]

        rsi = calc_rsi(closes)
        price = closes[-1]
        return rsi, price

    except Exception as e:
        log.error(f"Error {symbol}: {e}")
        return None, None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        r.raise_for_status()
        log.info("✅ Alerta enviada")
        return True
    except Exception as e:
        log.error(f"Error Telegram: {e}")
        return False

def format_alert(symbol, rsi, price, alert_type):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    display = symbol.replace("USDT", "/USDT")
    price_str = f"{price:,.4f}" if price < 1 else f"{price:,.2f}"
    if alert_type == "ob":
        emoji, title, signal = "🔴", f"SOBRECOMPRA — {display}", f"RSI ≥ {RSI_OVERBOUGHT} — posible caída"
    else:
        emoji, title, signal = "🟢", f"SOBREVENTA — {display}", f"RSI ≤ {RSI_OVERSOLD} — posible rebote"
    return (f"{emoji} <b>{title}</b>\n"
            f"RSI (14): <b>{rsi:.2f}</b>\n"
            f"Precio: <b>{price_str} USDT</b>\n"
            f"{signal}\n"
            f"🕐 {now}\n"
            f"RSI Hunter Bot")

def check_coins():
    global alert_count
    log.info(f"--- Iniciando ciclo: {len(PAIRS)} pares ---")
    for symbol in PAIRS:
        rsi, price = fetch_rsi_bybit(symbol)
        if rsi is None:
            time.sleep(0.3)
            continue

        new_state = "ob" if rsi >= RSI_OVERBOUGHT else "os" if rsi <= RSI_OVERSOLD else "neutral"
        prev_state = last_state.get(symbol, "neutral")
        log.info(f"{symbol:12s} | RSI: {rsi:6.2f} | {new_state}")

        if new_state != prev_state:
            if new_state in ("ob", "os"):
                send_telegram(format_alert(symbol, rsi, price, new_state))
                alert_count += 1
            last_state[symbol] = new_state

        time.sleep(0.2)

    log.info(f"Ciclo completo. Alertas totales: {alert_count}")

def main():
    log.info("RSI HUNTER BOT — Bybit Futuros Edition")
    if "PON_TU" in TELEGRAM_TOKEN:
        log.error("❌ Falta configurar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID")
        return

    pairs_list = " | ".join([p.replace("USDT", "/USDT") for p in PAIRS])
    send_telegram(
        f"🚀 <b>RSI HUNTER BOT INICIADO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Fuente: <b>Bybit Futuros (USDT Perpetual)</b>\n"
        f"🔍 Monitoreando: <b>{len(PAIRS)} pares</b>\n"
        f"⚙️ RSI sobreventa ≤ <b>{RSI_OVERSOLD}</b> | sobrecompra ≥ <b>{RSI_OVERBOUGHT}</b>\n"
        f"⏱️ Velas: <b>5 minutos</b>\n"
        f"🔄 Intervalo: cada <b>{CHECK_INTERVAL}s</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 {pairs_list}"
    )

    while True:
        try:
            check_coins()
        except Exception as e:
            log.error(f"Error en ciclo: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
