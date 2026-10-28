import feedparser
import smtplib
import os
import json
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# Reuters の公式RSS廃止のため Google News 経由で取得
BASE = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q=site:reuters.com"
CATEGORIES = [
    ("Top News",   f"{BASE}"),
    ("World",      f"{BASE}+world"),
    ("Business",   f"{BASE}+business"),
    ("Technology", f"{BASE}+technology"),
    ("Science",    f"{BASE}+science"),
    ("Health",     f"{BASE}+health"),
    ("Sports",     f"{BASE}+sports"),
]

SENDER     = os.environ["GMAIL_USER"]
PASSWORD   = os.environ["GMAIL_PASSWORD"]
RECIPIENTS = [r.strip() for r in os.environ["RECIPIENT_EMAIL"].split(",") if r.strip()]
DEEPL_KEY  = os.environ["DEEPL_API_KEY"]
TOP_N     = 5

_UA_PC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def translate(text):
    if not text:
        return ""
    try:
        payload = urllib.parse.urlencode({
            "text": text[:500],
            "target_lang": "JA",
            "source_lang": "EN",
        }).encode()
        req = urllib.request.Request(
            "https://api-free.deepl.com/v2/translate",
            data=payload,
            headers={"Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return data["translations"][0]["text"]
    except Exception as e:
        print(f"  translate failed: {e}")
        return text  # 失敗時は原文を返す


def fetch_news(url, n=TOP_N):
    feed = feedparser.parse(url, request_headers={"User-Agent": _UA_PC})
    print(f"  fetch {url[:80]} → {len(feed.entries)} 件")
    items = []
    for entry in feed.entries[:n]:
        title = entry.get("title", "")
        items.append({
            "title":    title,
            "title_ja": translate(title),
            "link":     entry.get("link", ""),
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
            <div style="color:#003f5c;font-size:13px;margin-top:4px;font-weight:bold;">{it['title_ja']}</div>
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
        Source: Reuters via Google News RSS / 自動配信（日本語訳は機械翻訳）
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(subject, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER
    msg["To"]      = ", ".join(RECIPIENTS)
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, PASSWORD)
        server.sendmail(SENDER, RECIPIENTS, msg.as_string())


def main():
    sections = []
    for cat_name, url in CATEGORIES:
        items = fetch_news(url)
        if items:
            sections.append((cat_name, items))

    if not sections:
        print("ニュース取得なし")
        return

    today   = datetime.now().strftime("%Y/%m/%d")
    subject = f"【Reuters】{today} 朝のまとめ"
    html    = build_html(sections)
    send_email(subject, html)
    print(f"送信完了: {subject}")


if __name__ == "__main__":
    main()
