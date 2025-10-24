import os
import base64
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import investpy

# --- Конфигурация ---
TICKERS = {
    "AAPL": "Apple Inc",
    "MSFT": "Microsoft Corp",
    "META": "Meta Platforms Inc",
    "NVDA": "NVIDIA Corp",
    "RBLX": "Roblox Corp",
    "U": "Unity Software Inc"
}
CSV_PATH = "data.csv"
CHART_PATH = "chart.png"
PDF_PATH = "report.pdf"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
TO_EMAIL = "valentin0407@gmail.com"
FROM_EMAIL = "reports@example.com"

# --- Определяем даты ---
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

# --- Скачиваем данные через investpy ---
rows = []
for symbol, name in TICKERS.items():
    try:
        data = investpy.get_stock_historical_data(
            stock=name,
            country='United States',
            from_date=(yesterday - datetime.timedelta(days=14)).strftime("%d/%m/%Y"),
            to_date=yesterday.strftime("%d/%m/%Y")
        )
        if not data.empty:
            close = float(data["Close"].iloc[-1])
            rows.append({"date": yesterday.isoformat(), "ticker": symbol, "close": close})
    except Exception as e:
        print(f"Ошибка для {symbol}: {e}")

if not rows:
    raise SystemExit("❌ Нет данных (Investing.com ничего не вернул)")

df_new = pd.DataFrame(rows)

# --- Объединяем с историей ---
if os.path.exists(CSV_PATH):
    df_old = pd.read_csv(CSV_PATH)
    df = pd.concat([df_old, df_new], ignore_index=True)
    df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
else:
    df = df_new

df.to_csv(CSV_PATH, index=False)

# --- График ---
pivot = df.pivot(index="date", columns="ticker", values="close").sort_index()
pivot = pivot.fillna(method="ffill")
norm = pivot.divide(pivot.iloc[0]).multiply(100)

plt.figure(figsize=(10, 6))
for col in norm.columns:
    plt.plot(norm.index, norm[col], label=col)
plt.xticks(rotation=45)
plt.title("Tech & Metaverse Index (base = 100)")
plt.legend()
plt.tight_layout()
plt.savefig(CHART_PATH)

# --- PDF отчёт ---
c = canvas.Canvas(PDF_PATH, pagesize=letter)
c.setFont("Helvetica-Bold", 16)
c.drawString(50, 750, f"Tech & Metaverse Daily Report — {yesterday.isoformat()}")
c.setFont("Helvetica", 12)
c.drawString(50, 730, f"Всего тикеров: {len(TICKERS)}")
c.drawImage(CHART_PATH, 50, 400, width=500, height=300)

# Последние значения
y_pos = 370
for _, r in df_new.iterrows():
    c.drawString(50, y_pos, f"{r['ticker']}: {r['close']:.2f} USD")
    y_pos -= 20
c.save()

# --- Отправка письма ---
if not SENDGRID_API_KEY:
    raise SystemExit("SENDGRID_API_KEY not set")

with open(PDF_PATH, "rb") as f:
    data = f.read()
encoded = base64.b64encode(data).decode()

message = Mail(
    from_email=FROM_EMAIL,
    to_emails=TO_EMAIL,
    subject=f"Tech & Metaverse Report — {yesterday.isoformat()}",
    html_content=f"<p>Attached: PDF report for {yesterday.isoformat()}</p>"
)
attachment = Attachment(
    FileContent(encoded),
    FileName("report.pdf"),
    FileType("application/pdf"),
    Disposition("attachment")
)
message.attachment = attachment

sg = SendGridAPIClient(SENDGRID_API_KEY)
resp = sg.send(message)
print("✅ Email sent:", resp.status_code)

