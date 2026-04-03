"""
╔══════════════════════════════════════════════════╗
║          RSI HUNTER — TELEGRAM BOT               ║
║  Replica exacta de tu app RSI Hunter             ║
║  Notificaciones reales aunque la pantalla        ║
║  esté apagada o el celular bloqueado             ║
╚══════════════════════════════════════════════════╝

CONFIGURACIÓN RÁPIDA:
1. Crea tu bot en Telegram hablando con @BotFather → /newbot
2. Copia el TOKEN que te da BotFather
3. Escríbele /start a tu bot y luego ve a:
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   Busca "chat":{"id": XXXXXXXXX} — ese es tu CHAT_ID
4. Pon TOKEN y CHAT_ID abajo
5. Sube a Render.com gratis (instrucciones al final)
"""

import os
import time
import requests
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# ⚙️  CONFIGURACIÓN — EDITA ESTO
# ─────────────────────────────────────────────

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "PON_TU_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "PON_TU_CHAT_ID_AQUI")

# Monedas a monitorear — Top 150 por capitalización/volumen en Binance
COINS = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA", "AVAX", "SHIB", "DOT",
    "LINK", "TRX", "MATIC", "LTC", "BCH", "UNI", "ATOM", "XLM", "ETC", "FIL",
    "APT", "ARB", "OP", "NEAR", "INJ", "SUI", "TIA", "SEI", "PEPE", "WIF",
    "FET", "RNDR", "GRT", "SAND", "AXS", "MANA", "CHZ", "ENJ", "GALA", "IMX",
    "LDO", "AAVE", "MKR", "SNX", "CRV", "COMP", "1INCH", "BAL", "YFI", "SUSHI",
    "ALGO", "EGLD", "HBAR", "ICP", "VET", "THETA", "FTM", "ONE", "ZIL", "IOTA",
    "NEO", "EOS", "XTZ", "DASH", "ZEC", "XMR", "WAVES", "KSM", "ICX", "ONT",
    "QTUM", "ZRX", "BAT", "CVC", "STORJ", "SKL", "OGN", "NKN", "BAND", "RLC",
    "ROSE", "CELO", "ANKR", "SXP", "RSR", "REEF", "DENT", "HOT", "WIN", "TWT",
    "CFX", "STX", "KAVA", "FLUX", "HNT", "MINA", "FLOW", "AKT", "IOTX", "CTSI",
    "SPELL", "JOE", "MAGIC", "HIGH", "HOOK", "AMB", "LQTY", "SSV", "AGLD", "RPL",
    "GMX", "PERP", "DYDX", "OCEAN", "NMR", "REN", "ORN", "MLN", "API3", "UMA",
    "CELR", "BICO", "PYR", "MASK", "ACH", "POLY", "BEL", "IDEX", "PAXG", "QNT",
    "VRA", "GLMR", "MOVR", "ACA", "KMA", "VOXEL", "GAL", "LOKA", "FARM", "RAY",
]

# Umbrales RSI (igual que tu app por defecto)
RSI_OVERBOUGHT = int(os.getenv("RSI_OB", "80"))   # Sobrecompra
RSI_OVERSOLD   = int(os.getenv("RSI_OS", "20"))   # Sobreventa

# Intervalo de revisión en segundos (30s = igual que tu app)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))

# Periodo RSI (igual que tu app)
RSI_PERIOD = 14

# ─────────────────────────────────────────────
# ESTADO — rastrea última alerta por moneda
# ─────────────────────────────────────────────
last_state = {}   # { "BTC": "neutral" | "ob" | "os" }
alert_count = 0

# ─────────────────────────────────────────────
# RSI CALCULATION (misma lógica que tu app)
# ─────────────────────────────────────────────
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains = losses = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    ag = gains / period
    al = losses / period
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (period - 1) + max(d, 0)) / period
        al = (al * (period - 1) + max(-d, 0)) / period
    if al == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + ag / al))

# ─────────────────────────────────────────────
# BINANCE API (misma fuente que tu app)
# ─────────────────────────────────────────────
def fetch_rsi(symbol):
    """Obtiene RSI y precio actual desde Binance (gratis, sin API key)"""
    pair = symbol.upper() + "USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=5m&limit=100"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        closes = [float(k[4]) for k in data]
        rsi = calc_rsi(closes, RSI_PERIOD)
        price = closes[-1]
        return rsi, price
    except Exception as e:
        log.error(f"Error fetching {symbol}: {e}")
        return None, None

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────
def send_telegram(message):
    """Envía mensaje a Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        log.info(f"✅ Telegram enviado")
        return True
    except Exception as e:
        log.error(f"Error Telegram: {e}")
        return False

def format_alert(symbol, rsi, price, alert_type):
    """Formatea la alerta igual que tu app"""
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    price_str = f"{price:,.2f}" if price >= 1 else f"{price:.6f}"

    if alert_type == "ob":
        emoji = "🔴"
        title = f"SOBRECOMPRA — {symbol}/USDT"
        signal = f"RSI supera {RSI_OVERBOUGHT} ⚠ Posible caída"
        rsi_color = "🔴"
    else:
        emoji = "🟢"
        title = f"SOBREVENTA — {symbol}/USDT"
        signal = f"RSI bajo {RSI_OVERSOLD} 💚 Posible rebote"
        rsi_color = "🟢"

    msg = (
        f"{emoji} <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 RSI (14): <b>{rsi:.2f}</b> {rsi_color}\n"
        f"💰 Precio: <b>{price_str} USDT</b>\n"
        f"📡 {signal}\n"
        f"🕐 {now}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>RSI Hunter Bot</i>"
    )
    return msg

# ─────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────
def check_coins():
    """Revisa todas las monedas y dispara alertas si hay cambio de estado"""
    global alert_count
    for symbol in COINS:
        rsi, price = fetch_rsi(symbol)
        if rsi is None:
            continue

        is_ob = rsi >= RSI_OVERBOUGHT
        is_os = rsi <= RSI_OVERSOLD
        new_state = "ob" if is_ob else "os" if is_os else "neutral"
        prev_state = last_state.get(symbol, "neutral")

        log.info(f"{symbol}/USDT | RSI: {rsi:.2f} | Precio: {price:.2f} | Estado: {new_state}")

        # Solo alerta si el estado CAMBIÓ (igual que tu app)
        if new_state != prev_state:
            if new_state in ("ob", "os"):
                msg = format_alert(symbol, rsi, price, new_state)
                if send_telegram(msg):
                    alert_count += 1
                    log.info(f"🚨 ALERTA #{alert_count}: {symbol} → {new_state.upper()} (RSI {rsi:.2f})")
            last_state[symbol] = new_state

        time.sleep(0.3)  # pausa entre monedas — con 150 coins el ciclo dura ~45s

def startup_message():
    """Mensaje de inicio al arrancar el bot"""
    coins_str = " | ".join([f"{c}/USDT" for c in COINS])
    msg = (
        f"🚀 <b>RSI HUNTER BOT INICIADO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Monitoreando:\n<code>{coins_str}</code>\n\n"
        f"⚙️ Configuración:\n"
        f"• Sobrecompra (OB): RSI ≥ {RSI_OVERBOUGHT}\n"
        f"• Sobreventa (OS): RSI ≤ {RSI_OVERSOLD}\n"
        f"• Revisión cada: {CHECK_INTERVAL}s\n"
        f"• Fuente: Binance 5m\n\n"
        f"✅ Las notificaciones llegarán aunque\n"
        f"tu pantalla esté apagada."
    )
    send_telegram(msg)

def main():
    log.info("=" * 50)
    log.info("   RSI HUNTER BOT — INICIANDO")
    log.info("=" * 50)
    log.info(f"Monedas: {', '.join(COINS)}")
    log.info(f"OB: {RSI_OVERBOUGHT} | OS: {RSI_OVERSOLD} | Intervalo: {CHECK_INTERVAL}s")

    # Validar configuración
    if "PON_TU" in TELEGRAM_TOKEN or "PON_TU" in TELEGRAM_CHAT_ID:
        log.error("❌ Falta configurar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID")
        log.error("   Edita el archivo o usa variables de entorno en Render")
        return

    startup_message()
    log.info("✅ Bot en marcha. Monitoreando señales RSI...")

    while True:
        try:
            check_coins()
        except Exception as e:
            log.error(f"Error en ciclo principal: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
