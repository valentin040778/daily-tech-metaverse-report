import os
import base64
import datetime
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

TICKERS = ["AAPL", "MSFT", "NVDA", "META", "RBLX", "U"]  # Unity вместо тикера U
CSV_PATH = "data.csv"
PNG_PATH = "daily_chart.png"

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TO_EMAIL = "valentin0407@gmail.com"
FROM_EMAIL = "valentin0407@gmail.com"  # можно временно reports@example.com

# --- определить дату вчерашнего дня ---
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

# --- загрузить данные через yfinance ---
rows = []
for t in TICKERS:
    tk = yf.Ticker(t)
    hist = tk.history(start=yesterday - datetime.timedelta(days=5), end=yesterday + datetime.timedelta(days=1))
    if hist.empty:
        continue
    row = hist.tail(1).iloc[0]
    close = float(row["Close"])
    rows.append({"date": yesterday.isoformat(), "ticker": t, "close": close})

if not rows:
    raise SystemExit("No data fetched — possibly market closed")

df_new = pd.DataFrame(rows)

# --- накопление данных ---
if os.path.exists(CSV_PATH):
    df_old = pd.read_csv(CSV_PATH)
    df = pd.concat([df_old, df_new], ignore_index=True)
    df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
else:
    df = df_new

df.to_csv(CSV_PATH, index=False)

# --- построение графика ---
pivot = df.pivot(index="date", columns="ticker", values="close").sort_index()
pivot = pivot.fillna(method="ffill")
norm = pivot.divide(pivot.iloc[0]).multiply(100)  # базовый индекс 100

plt.figure(figsize=(10, 6))
for col in norm.columns:
    plt.plot(norm.index, norm[col], label=col)
plt.xticks(rotation=45)
plt.title("Tech & Metaverse Index (base = 100)")
plt.legend()
plt.tight_layout()
plt.savefig(PNG_PATH)

# --- отправка email ---
if not SENDGRID_API_KEY:
    raise SystemExit("SENDGRID_API_KEY not set")

with open(PNG_PATH, "rb") as f:
    data = f.read()
encoded = base64.b64encode(data).decode()

message = Mail(
    from_email=FROM_EMAIL,
    to_emails=TO_EMAIL,
    subject=f"Tech & Metaverse Report — {yesterday.isoformat()}",
    html_content=f"<p>Attached: updated performance chart as of {yesterday.isoformat()}</p>",
)
attachment = Attachment(
    FileContent(encoded),
    FileName("daily_chart.png"),
    FileType("image/png"),
    Disposition("attachment"),
)
message.attachment = attachment

sg = SendGridAPIClient(SENDGRID_API_KEY)
resp = sg.send(message)
print("Email sent:", resp.status_code)
