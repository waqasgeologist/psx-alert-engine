import datetime
import os
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Set your ntfy topic name here (or pass it via GitHub Secrets)
NTFY_TOPIC = "Khan_PSX_Alerts"

WATCHLIST = {
    "LOTCHEM": {"target_high": 27.50, "target_low": 25.00},
    "PIBTL": {"target_high": 17.00, "target_low": 14.50},
    "SLGL": {"target_high": 15.00, "target_low": 13.50},
    "SELECT": {"target_high": 33.00, "target_low": 31.00},
    "AGP": {"target_high": 170.00, "target_low": 150.00},
}

def send_ntfy_push(title, body, priority=3, tags="chart_with_upwards_trend"):
  url = f"https://ntfy.sh/{NTFY_TOPIC}"
  headers = {
      "Title": title,
      "Priority": str(priority),
      "Tags": tags,
      "Markdown": "yes",
  }
  try:
    res = requests.post(
        url, data=body.encode("utf-8"), headers=headers, timeout=15
    )
    print(
        f"[ntfy.sh Response] Status: {res.status_code} | Body:"
        f" {res.text.strip()}"
    )
  except Exception as e:
    print(f"[ntfy.sh Error] Failed to reach server: {e}")


def get_psx_price(symbol):
  session = requests.Session()
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "application/json, text/plain, */*",
      "Referer": f"https://dps.psx.com.pk/company/{symbol}",
  }

  # 1. Primary: PSX JSON Endpoint
  try:
    api_url = f"https://dps.psx.com.pk/timeseries/int/{symbol}"
    res = session.get(api_url, headers=headers, timeout=8)
    if res.status_code == 200:
      data = res.json()
      if data and "data" in data and len(data["data"]) > 0:
        return float(data["data"][-1][1])
    else:
      print(f"[{symbol}] JSON API returned status: {res.status_code}")
  except Exception as err:
    print(f"[{symbol}] JSON API error: {err}")

  # 2. Fallback: HTML Scraping
  try:
    page_url = f"https://dps.psx.com.pk/company/{symbol}"
    res = session.get(page_url, headers=headers, timeout=8)
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")
      quote = soup.find("div", class_="quote__close")
      if quote:
        raw = quote.text.replace("Rs.", "").replace(",", "").strip()
        return float(raw)
    else:
      print(f"[{symbol}] HTML page returned status: {res.status_code}")
  except Exception as err:
    print(f"[{symbol}] HTML scraper error: {err}")

  return None


def main():
  # Current time in Pakistan Standard Time (UTC + 5)
  now_pkt = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
  time_label = now_pkt.strftime("%H:%M")
  day_label = now_pkt.strftime("%A")

  print(
      f"--- PSX Runner execution started for {day_label} at {time_label} PKT ---"
  )
  print(f"Targeting ntfy topic: https://ntfy.sh/{NTFY_TOPIC}")

  lines = [f"**PSX Snapshot ({day_label} {time_label} PKT):**\n"]
  target_breaches = []

  for symbol, targets in WATCHLIST.items():
    price = get_psx_price(symbol)
    high = targets["target_high"]
    low = targets["target_low"]

    if price is not None:
      lines.append(
          f"• **{symbol}**: Rs. {price:.2f}  \n  [Low: {low:.2f} | High:"
          f" {high:.2f}]"
      )
      if price >= high:
        target_breaches.append(
            f"🚨 BREAKOUT: {symbol} at Rs. {price:.2f} (Target >= {high:.2f})"
        )
      elif price <= low:
        target_breaches.append(
            f"⚠️ BREAKDOWN: {symbol} at Rs. {price:.2f} (Target <= {low:.2f})"
        )
    else:
      lines.append(f"• **{symbol}**: No data (Blocked or Closed)")

  # Send High Priority Target Alerts if any trigger fired
  if target_breaches:
    breach_body = "\n".join(target_breaches)
    send_ntfy_push(
        title="PSX TARGET TRIGGERED",
        body=breach_body,
        priority=5,
        tags="warning,rotating_light",
    )

  # Always send the scheduled market digest
  digest_body = "\n".join(lines)
  send_ntfy_push(
      title=f"PSX Update ({time_label})",
      body=digest_body,
      priority=5,
      tags="bar_chart",
  )
  print("--- Run completed ---")


if __name__ == "__main__":
  main()
