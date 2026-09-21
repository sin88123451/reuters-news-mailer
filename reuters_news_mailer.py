import feedparser
import smtplib
import os
import json
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

CATEGORIES = [
    ("Top News",   "https://feeds.reuters.com/reuters/topNews"),
    ("World",      "https://feeds.reuters.com/Reuters/worldNews"),
    ("Business",   "https://feeds.reuters.com/reuters/businessNews"),
    ("Technology", "https://feeds.reuters.com/reuters/technologyNews"),
    ("Science",    "https://feeds.reuters.com/reuters/scienceNews"),
    ("Health",     "https://feeds.reuters.com/reuters/healthNews"),
    ("Sports",     "https://feeds.reuters.com/reuters/sportsNews"),
]

SENDER    = os.environ["GMAIL_USER"]
PASSWORD  = os.environ["GMAIL_PASSWORD"]
RECIPIENT = os.environ["RECIPIENT_EMAIL"]
TOP_N     = 5


def translate(text):
    if not text:
        return ""
    try:
        encoded = urllib.parse.quote(text[:500])
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl=ja&dt=t&q={encoded}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return "".join(item[0] for item in data[0] if item[0])
    except Exception:
        return ""


def fetch_news(url, n=TOP_N):
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:n]:
        title   = entry.get("title", "")
        summary = entry.get("summary", "")
        items.append({
            "title":      title,
            "summary":    summary,
            "title_ja":   translate(title),
            "summary_ja": translate(summary),
            "link":       entry.get("link", ""),
        })
    return items


def build_html(sections):
    today = datetime.now().strftime("%Y/%m/%d")
    rows = ""
    for cat_name, items in sections:
        rows += f"""
        <tr>
          <td colspan="2" style="background:#f26522;color:#fff;padding:10px 16px;
              font-size:15px;font-weight:bold;">Reuters {cat_name}</td>
        </tr>"""
        for i, it in enumerate(items, 1):
            bg = "#f9f9f9" if i % 2 == 0 else "#ffffff"
            rows += f"""
        <tr style="background:{bg};">
          <td style="padding:10px 16px;font-size:14px;vertical-align:top;width:30px;color:#888;">{i}.</td>
          <td style="padding:10px 16px;font-size:14px;vertical-align:top;">
            <a href="{it['link']}" style="color:#f26522;font-weight:bold;text-decoration:none;">{it['title']}</a>
            <div style="color:#003f5c;font-size:13px;margin-top:2px;font-weight:bold;">{it['title_ja']}</div>
            <div style="color:#555;margin-top:6px;font-size:13px;">{it['summary']}</div>
            <div style="color:#777;margin-top:2px;font-size:12px;font-style:italic;">{it['summary_ja']}</div>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#eee;font-family:sans-serif;">
  <table width="660" align="center" cellpadding="0" cellspacing="0"
         style="background:#fff;margin:20px auto;border-radius:8px;overflow:hidden;
                box-shadow:0 2px 8px rgba(0,0,0,.15);">
    <tr>
      <td colspan="2" style="background:#f26522;padding:20px 24px;">
        <div style="color:#fff;font-size:22px;font-weight:bold;">Reuters 朝刊</div>
        <div style="color:#ffe0cc;font-size:13px;margin-top:4px;">{today} Morning Edition</div>
      </td>
    </tr>
    {rows}
    <tr>
      <td colspan="2" style="padding:14px 16px;font-size:12px;color:#aaa;text-align:center;">
        Source: Reuters RSS / 自動配信（日本語訳は機械翻訳）
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())


def main():
    sections = []
    for cat_name, url in CATEGORIES:
        items = fetch_news(url)
        if items:
            sections.append((cat_name, items))

    if not sections:
        print("ニュース取得なし（RSS変更の可能性）")
        return

    today   = datetime.now().strftime("%Y/%m/%d")
    subject = f"【Reuters】{today} 朝のまとめ"
    html    = build_html(sections)
    send_email(subject, html)
    print(f"送信完了: {subject}")


if __name__ == "__main__":
    main()
