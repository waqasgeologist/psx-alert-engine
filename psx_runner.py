import datetime
import os
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Set your ntfy topic name here (or pass it via GitHub Secrets)
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "Khan_PSX_Alerts")

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
    requests.post(
        url, data=body.encode("utf-8"), headers=headers, timeout=10
    )
    print(f"Delivered: {title}")
  except Exception as e:
    print(f"ntfy error: {e}")


def get_psx_price(symbol):
  url = f"https://dps.psx.com.pk/company/{symbol}"
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/115.0.0.0 Safari/537.36"
      )
  }
  try:
    res = requests.get(url, headers=headers, timeout=8)
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")
      quote = soup.find("div", class_="quote__close")
      if quote:
        raw = quote.text.replace("Rs.", "").replace(",", "").strip()
        return float(raw)
  except Exception as err:
    print(f"Error reading {symbol}: {err}")
  return None


def main():
  # Convert UTC to Pakistan Standard Time (UTC+5)
  now_pkt = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
  time_label = now_pkt.strftime("%H:%M")
  day_label = now_pkt.strftime("%A")

  print(f"Running PSX check for {day_label} at {time_label} PKT...")

  lines = [f"**PSX Snapshot ({day_label} {time_label} PKT):**\n"]
  target_breaches = []

  for symbol, targets in WATCHLIST.items():
    price = get_psx_price(symbol)
    if price is None:
      lines.append(f"• **{symbol}**: N/A")
      continue

    high = targets["target_high"]
    low = targets["target_low"]
    lines.append(
        f"• **{symbol}**: Rs. {price:.2f}  \n  [Low: {low:.2f} | High:"
        f" {high:.2f}]"
    )

    # Check for breakouts or breakdowns
    if price >= high:
      target_breaches.append(
          f"🚨 BREAKOUT: {symbol} at Rs. {price:.2f} (Target >= {high:.2f})"
      )
    elif price <= low:
      target_breaches.append(
          f"⚠️ BREAKDOWN: {symbol} at Rs. {price:.2f} (Target <= {low:.2f})"
      )

  # 1. Send priority alert if any stock crossed target boundaries
  if target_breaches:
    breach_body = "\n".join(target_breaches)
    send_ntfy_push(
        title="PSX TARGET TRIGGERED",
        body=breach_body,
        priority=5,
        tags="warning,rotating_light",
    )

  # 2. Send the general scheduled digest
  digest_body = "\n".join(lines)
  send_ntfy_push(
      title=f"PSX Update ({time_label})",
      body=digest_body,
      priority=3,
      tags="bar_chart",
  )


if __name__ == "__main__":
  main()
