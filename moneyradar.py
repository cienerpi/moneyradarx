import os
import logging
import requests
import re
from bs4 import BeautifulSoup
import pytz
from datetime import time

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise Exception("Не найден TELEGRAM_BOT_TOKEN в файле .env")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. ROMANIA – cursbanci.ro (банковские курсы)
def get_average_bank_rates() -> tuple[str, str, str, str]:
    url = "https://cursbanci.ro/ru/curs-valutar-banci"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/110.0.0.0 Safari/537.36")
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return ("Ошибка", "Ошибка", "Ошибка", "Ошибка")
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select("#tablecurs > tbody > tr")
    eur_buy_sum = eur_sell_sum = usd_buy_sum = usd_sell_sum = 0.0
    count = 0
    for row in rows:
        if row.find("th"):
            continue
        cells = row.find_all("td")
        if len(cells) < 5:
            continue
        try:
            eur_buy = float(cells[1].get_text(strip=True).replace(",", "."))
            eur_sell = float(cells[2].get_text(strip=True).replace(",", "."))
            usd_buy = float(cells[3].get_text(strip=True).replace(",", "."))
            usd_sell = float(cells[4].get_text(strip=True).replace(",", "."))
        except ValueError:
            continue
        eur_buy_sum += eur_buy
        eur_sell_sum += eur_sell
        usd_buy_sum += usd_buy
        usd_sell_sum += usd_sell
        count += 1
    if count == 0:
        return ("Нет данных", "Нет данных", "Нет данных", "Нет данных")
    eur_buy_avg = eur_buy_sum / count
    eur_sell_avg = eur_sell_sum / count
    usd_buy_avg = usd_buy_sum / count
    usd_sell_avg = usd_sell_sum / count
    return (f"{eur_buy_avg:.3f}", f"{eur_sell_avg:.3f}", f"{usd_buy_avg:.3f}", f"{usd_sell_avg:.3f}")

# 2. POLAND – Kantor Stalowa Wola (tadek.pl)
def get_kantor_rates() -> tuple[str, str, str, str]:
    url = "https://kantorstalowawola.tadek.pl/"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWeb.537.36 (KHTML, like Gecko) "
                       "Chrome/110.0.0.0 Safari/537.36")
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:
        return ("Ошибка", "Ошибка", "Ошибка", "Ошибка")
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.select_one("#kursy > div > div > div > div > table")
    if not table:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")
    if len(rows) < 4:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    usd_row = rows[0]
    usd_cells = usd_row.find_all("td")
    if len(usd_cells) < 5:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    usd_purchase_text = usd_cells[3].get_text(strip=True)
    usd_sale_text = usd_cells[4].get_text(strip=True)
    eur_row = rows[3]
    eur_cells = eur_row.find_all("td")
    if len(eur_cells) < 5:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    eur_purchase_text = eur_cells[3].get_text(strip=True)
    eur_sale_text = eur_cells[4].get_text(strip=True)
    def parse_rate(text: str) -> str:
        match = re.search(r"[\d.,]+", text)
        if match:
            num_str = match.group().replace(",", ".")
            try:
                rate_val = float(num_str) / 100.0
                return f"{rate_val:.3f}"
            except ValueError:
                return "Ошибка"
        else:
            return "Не найдено"
    usd_purchase_rate = parse_rate(usd_purchase_text)
    usd_sale_rate = parse_rate(usd_sale_text)
    eur_purchase_rate = parse_rate(eur_purchase_text)
    eur_sale_rate = parse_rate(eur_sale_text)
    return (usd_purchase_rate, usd_sale_rate, eur_purchase_rate, eur_sale_rate)

# 3. BULGARIA – Unicredit Bulbank
def get_unicredit_rates() -> tuple[str, str, str, str]:
    url = "https://www.unicreditbulbank.bg/bg/kursove-indeksi/valutni-kursove/"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/110.0.0.0 Safari/537.36")
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:
        return ("Ошибка", "Ошибка", "Ошибка", "Ошибка")
    soup = BeautifulSoup(response.text, "html.parser")
    table_body = soup.select_one("#main-id > div > div > div.index-currency-table > div > div > table > tbody")
    if not table_body:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    euro_row = table_body.select_one("tr:nth-child(2)")
    if euro_row:
        euro_buy_elem = euro_row.select_one("td:nth-child(3)")
        euro_sell_elem = euro_row.select_one("td:nth-child(4)")
        try:
            euro_buy_val = float(euro_buy_elem.get_text(strip=True).replace(",", "."))
            euro_sell_val = float(euro_sell_elem.get_text(strip=True).replace(",", "."))
            euro_buy_text = f"{euro_buy_val:.3f}"
            euro_sell_text = f"{euro_sell_val:.3f}"
        except Exception:
            euro_buy_text = euro_sell_text = "Ошибка"
    else:
        euro_buy_text = euro_sell_text = "Не найдено"
    dollar_row = table_body.select_one("tr:nth-child(3)")
    if dollar_row:
        dollar_buy_elem = dollar_row.select_one("td:nth-child(3)")
        dollar_sell_elem = dollar_row.select_one("td:nth-child(4)")
        try:
            dollar_buy_val = float(dollar_buy_elem.get_text(strip=True).replace(",", "."))
            dollar_sell_val = float(dollar_sell_elem.get_text(strip=True).replace(",", "."))
            dollar_buy_text = f"{dollar_buy_val:.3f}"
            dollar_sell_text = f"{dollar_sell_val:.3f}"
        except Exception:
            dollar_buy_text = dollar_sell_text = "Ошибка"
    else:
        dollar_buy_text = dollar_sell_text = "Не найдено"
    # Возвращаем сначала USD, потом EUR
    return (dollar_buy_text, dollar_sell_text, euro_buy_text, euro_sell_text)

# 4. MOLDOVA – noi.md
def get_noi_rates() -> tuple[str, str, str, str]:
    url = "https://noi.md/ru/curs/"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/110.0.0.0 Safari/537.36")
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception:
        return ("Ошибка", "Ошибка", "Ошибка", "Ошибка")
    soup = BeautifulSoup(response.text, "html.parser")
    row = soup.select_one("#exchange-table > tbody > tr:nth-child(2)")
    if not row:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    usd_purchase_elem = row.select_one("td:nth-child(2) > span")
    usd_sale_elem = row.select_one("td:nth-child(3)")
    eur_purchase_elem = row.select_one("td:nth-child(4) > span")
    eur_sale_elem = row.select_one("td:nth-child(5)")
    usd_purchase = usd_purchase_elem.get_text(strip=True) if usd_purchase_elem else "Не найдено"
    usd_sale = usd_sale_elem.get_text(strip=True) if usd_sale_elem else "Не найдено"
    eur_purchase = eur_purchase_elem.get_text(strip=True) if eur_purchase_elem else "Не найдено"
    eur_sale = eur_sale_elem.get_text(strip=True) if eur_sale_elem else "Не найдено"
    return (usd_purchase, usd_sale, eur_purchase, eur_sale)

# 5. UKRAINE – PrivatBank (используем данные с ПриватБанка)
def get_privat_rates_tuple() -> tuple[str, str, str, str]:
    url = 'https://privatbank.ua/rates-archive'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return ("Ошибка", "Ошибка", "Ошибка", "Ошибка")
    soup = BeautifulSoup(resp.text, 'html.parser')
    pairs = soup.select('div.currency-pairs')
    if not pairs:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")
    wanted = {"USD": None, "EUR": None}
    for pair in pairs:
        name_tag = pair.select_one('.names span')
        purchase_tag = pair.select_one('.purchase span')
        sale_tag = pair.select_one('.sale span')
        if not (name_tag and purchase_tag and sale_tag):
            continue
        cur = name_tag.get_text(strip=True).upper()
        buy = purchase_tag.get_text(strip=True)
        sell = sale_tag.get_text(strip=True)
        if "USD" in cur:
            wanted["USD"] = (buy, sell)
        elif "EUR" in cur:
            wanted["EUR"] = (buy, sell)
    if wanted["USD"] and wanted["EUR"]:
        return (wanted["USD"][0], wanted["USD"][1], wanted["EUR"][0], wanted["EUR"][1])
    else:
        return ("Не найдено", "Не найдено", "Не найдено", "Не найдено")

# 6. CRYPTO – CoinGecko API
def get_crypto_rates() -> tuple[str, str]:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        btc = data.get("bitcoin", {}).get("usd")
        eth = data.get("ethereum", {}).get("usd")
        if btc is not None and eth is not None:
            return (f"{float(btc):.2f}", f"{float(eth):.2f}")
        else:
            return ("Не найдено", "Не найдено")
    except Exception:
        return ("Ошибка", "Ошибка")

# Функция для формирования итогового сообщения
def build_currency_message() -> str:
    # ROMANIA
    eur_buy_avg, eur_sell_avg, usd_buy_avg, usd_sell_avg = get_average_bank_rates()
    # POLAND (Kantor Stalowa Wola)
    usd_purchase, usd_sale, eur_purchase, eur_sale = get_kantor_rates()
    # BULGARIA (Unicredit Bulbank) - возвращает (usd_buy, usd_sell, eur_buy, eur_sell)
    uni_usd_buy, uni_usd_sell, uni_eur_buy, uni_eur_sell = get_unicredit_rates()
    # MOLDOVA (noi.md)
    noi_usd_purchase, noi_usd_sale, noi_eur_purchase, noi_eur_sale = get_noi_rates()
    # UKRAINE – PrivatBank
    privat_usd_purchase, privat_usd_sale, privat_eur_purchase, privat_eur_sale = get_privat_rates_tuple()
    # CRYPTO – CoinGecko
    crypto_btc, crypto_eth = get_crypto_rates()

    message = (
        "<b>🇷🇴 ROMANIA</b>\n"
        "💵 USD: <b>{}</b> / <b>{}</b>\n"
        "💶 EUR: <b>{}</b> / <b>{}</b>\n\n"
        "<b>🇵🇱 POLAND</b>\n"
        "💵 USD: <b>{}</b> / <b>{}</b>\n"
        "💶 EUR: <b>{}</b> / <b>{}</b>\n\n"
        "<b>🇧🇬 BULGARIA</b>\n"
        "💵 USD: <b>{}</b> / <b>{}</b>\n"
        "💶 EUR: <b>{}</b> / <b>{}</b>\n\n"
        "<b>🇲🇩 MOLDOVA</b>\n"
        "💵 USD: <b>{}</b> / <b>{}</b>\n"
        "💶 EUR: <b>{}</b> / <b>{}</b>\n\n"
        "<b>🇺🇦 UKRAINE</b>\n"
        "💵 USD: <b>{}</b> / <b>{}</b>\n"
        "💶 EUR: <b>{}</b> / <b>{}</b>\n\n"
        "<b>🔗 Криптовалюты:</b>\n"
        "🪙 <b>Bitcoin:</b> <b>{}</b> $\n"
        "🔷 <b>Ethereum:</b> <b>{}</b> $"
    ).format(
        usd_buy_avg, usd_sell_avg, eur_buy_avg, eur_sell_avg,
        usd_purchase, usd_sale, eur_purchase, eur_sale,
        uni_usd_buy, uni_usd_sell, uni_eur_buy, uni_eur_sell,
        noi_usd_purchase, noi_usd_sale, noi_eur_purchase, noi_eur_sale,
        privat_usd_purchase, privat_usd_sale, privat_eur_purchase, privat_eur_sale,
        crypto_btc, crypto_eth
    )
    return message

# Команда бота
async def rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = build_currency_message()
    await update.message.reply_text(message, parse_mode=ParseMode.HTML)

# Ежедневная отправка курса валют в группу с chat_id = -1002510214338
async def scheduled_currency_rate(context: ContextTypes.DEFAULT_TYPE):
    message = build_currency_message()
    await context.bot.send_message(chat_id=-1002510214338, text=message, parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 SeaScript RateBot активен и готов к работе.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("rate", rate_command))
    application.add_handler(CommandHandler("start", start))
    tz = pytz.timezone('Europe/Kiev')
    application.job_queue.run_daily(scheduled_currency_rate, time(hour=13, minute=00, tzinfo=tz))
    application.run_polling()

if __name__ == "__main__":
    main()
