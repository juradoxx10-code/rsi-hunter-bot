import os, time, requests, logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "PON_TU_TOKEN_AQUI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "PON_TU_CHAT_ID_AQUI")
RSI_OVERBOUGHT = int(os.getenv("RSI_OB", "80"))
RSI_OVERSOLD   = int(os.getenv("RSI_OS", "20"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
RSI_PERIOD = 14

COINS = [
    "bitcoin","ethereum","binancecoin","solana","ripple","dogecoin","cardano",
    "avalanche-2","shiba-inu","polkadot","chainlink","tron","matic-network",
    "litecoin","bitcoin-cash","uniswap","cosmos","stellar","ethereum-classic",
    "filecoin","aptos","arbitrum","optimism","near","injective-protocol",
    "sui","celestia","sei-network","pepe","dogwifcoin","fetch-ai","render-token",
    "the-graph","the-sandbox","axie-infinity","decentraland","chiliz","enjincoin",
    "gala","immutable-x","lido-dao","aave","maker","synthetix-network-token",
    "curve-dao-token","compound-governance-token","1inch","balancer","yearn-finance",
    "sushi","algorand","elrond-erd-2","hedera-hashgraph","internet-computer",
    "vechain","theta-token","fantom","harmony","zilliqa","iota",
    "neo","eos","tezos","dash","zcash","monero","waves","kusama","icon","ontology",
    "qtum","0x","basic-attention-token","storj","skale","nkn","band-protocol",
    "oasis-network","celo","ankr","reserve-rights-token","dent","holotoken",
    "conflux-token","stacks","kava","flux","helium","mina-protocol","flow",
    "akash-network","iotex","cartesi","gmx","perpetual-protocol","dydx",
    "ocean-protocol","numeraire","ren","api3","uma","celer-network","mask-network",
    "pax-gold","quant-network","moonbeam","raydium"
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

def fetch_rsi(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": "1", "interval": "minute"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        prices = [p[1] for p in data["prices"]]
        if len(prices) < RSI_PERIOD + 1:
            return None, None
        rsi = calc_rsi(prices)
        price = prices[-1]
        return rsi, price
    except Exception as e:
        log.error(f"Error {coin_id}: {e}")
        return None, None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}, timeout=10)
        r.raise_for_status()
        log.info("Telegram enviado")
        return True
    except Exception as e:
        log.error(f"Error Telegram: {e}")
        return False

def format_alert(coin_id, rsi, price, alert_type):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    symbol = coin_id.upper()
    price_str = f"{price:,.2f}" if price >= 1 else f"{price:.6f}"
    if alert_type == "ob":
        emoji, title, signal = "🔴", f"SOBRECOMPRA — {symbol}/USD", f"RSI supera {RSI_OVERBOUGHT} posible caida"
    else:
        emoji, title, signal = "🟢", f"SOBREVENTA — {symbol}/USD", f"RSI bajo {RSI_OVERSOLD} posible rebote"
    return (f"{emoji} <b>{title}</b>\n"
            f"RSI (14): <b>{rsi:.2f}</b>\n"
            f"Precio: <b>{price_str} USD</b>\n"
            f"{signal}\n{now}\nRSI Hunter Bot")

def check_coins():
    global alert_count
    for coin_id in COINS:
        rsi, price = fetch_rsi(coin_id)
        if rsi is None:
            continue
        new_state = "ob" if rsi >= RSI_OVERBOUGHT else "os" if rsi <= RSI_OVERSOLD else "neutral"
        prev_state = last_state.get(coin_id, "neutral")
        log.info(f"{coin_id} | RSI: {rsi:.2f} | {new_state}")
        if new_state != prev_state:
            if new_state in ("ob", "os"):
                send_telegram(format_alert(coin_id, rsi, price, new_state))
                alert_count += 1
            last_state[coin_id] = new_state
        time.sleep(2)

def main():
    log.info("RSI HUNTER BOT INICIANDO con CoinGecko")
    if "PON_TU" in TELEGRAM_TOKEN:
        log.error("Falta TELEGRAM_TOKEN")
        return
    send_telegram("🚀 <b>RSI HUNTER BOT INICIADO</b>\nUsando CoinGecko sin restricciones ✅")
    while True:
        try:
            check_coins()
        except Exception as e:
            log.error(f"Error: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
