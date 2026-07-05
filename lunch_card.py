# -*- coding: utf-8 -*-
"""午餐小抄卡片產生器。
讀 lunch_note.txt 的簡單標記，排成漂亮的分區卡片(整頁 HTML)。
標記格式(每天我幫她填)：
    DATE: 6/24
    LEAD: 大盤一句話…
    # red | ① 真的要動手
    - 汎銓 → 清掉 | 反彈破底失敗…（"|"前是股名/動作，後是說明；沒有"|"就只有股名）
    # orange | ② 太燙…
    - 世界先進 / 長榮航 | 各賣一點…
    SUMMARY: 今天唯一非做不可…
顏色：red 橘 orange 藍 blue 灰 gray（對應動手/賣強/看著/抱著）。
"""
import os

COLORS = {"red": "#e5534b", "orange": "#e0870f", "blue": "#2f6fe0", "gray": "#8a9099"}

CARD_CSS = """
  *{box-sizing:border-box}
  body{margin:0;background:#fff;color:#1f2328;font-family:'Noto Sans TC','Microsoft JhengHei',sans-serif;padding:18px 16px 34px;line-height:1.5}
  .lh{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .lh h1{font-size:30px;margin:0;font-weight:900;letter-spacing:1px}
  .lh .date{font-size:17px;color:#a0a6ad;font-weight:800}
  .lead{color:#9aa0a6;font-size:15px;margin:8px 0 12px;line-height:1.65}
  .rule{border-top:1px solid #e6e8eb;margin-bottom:6px}
  .sec{margin:16px 0}
  .sh{display:flex;align-items:center;gap:9px;font-size:19px;font-weight:800;margin-bottom:6px}
  .bar{width:5px;height:22px;border-radius:3px;flex:0 0 auto}
  .item{margin:9px 0 9px 15px}
  .nm{font-weight:800;font-size:16px}
  .dt{color:#6b7280;font-size:14.5px;margin-top:2px;line-height:1.55}
  .sumbox{margin-top:20px;background:#eaf7ef;border:1px solid #cdeadb;border-radius:12px;padding:13px 15px}
  .sumbox .lbl{color:#2ea043;font-size:12px;font-weight:800;margin-bottom:4px}
  .sumbox .txt{font-weight:800;font-size:16px;line-height:1.6;color:#1f2328}
"""


def _esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def parse(text):
    date = lead = summary = ""
    sections = []
    cur = None
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("DATE:"):
            date = s[5:].strip()
        elif s.startswith("LEAD:"):
            lead = s[5:].strip()
        elif s.startswith("SUMMARY:"):
            summary = s[8:].strip()
        elif s.startswith("#"):
            parts = s[1:].split("|", 1)
            color = COLORS.get(parts[0].strip().lower(), "#8a9099")
            title = parts[1].strip() if len(parts) > 1 else ""
            cur = {"color": color, "title": title, "items": []}
            sections.append(cur)
        elif s.startswith("-") and cur is not None:
            parts = s[1:].split("|", 1)
            names = parts[0].strip()
            detail = parts[1].strip() if len(parts) > 1 else ""
            cur["items"].append({"names": names, "detail": detail})
    return date, lead, sections, summary


def render_card(text):
    date, lead, sections, summary = parse(text)
    date_span = f'<span class="date">{_esc(date)}</span>' if date else ""
    body = f'<div class="lh"><h1>午餐小抄</h1>{date_span}</div>'
    if lead:
        body += f'<div class="lead">{_esc(lead)}</div>'
    body += '<div class="rule"></div>'
    for sec in sections:
        c = sec["color"]
        body += f'<div class="sec"><div class="sh"><span class="bar" style="background:{c}"></span><span>{_esc(sec["title"])}</span></div>'
        for it in sec["items"]:
            body += f'<div class="item"><div class="nm" style="color:{c}">{_esc(it["names"])}</div>'
            if it["detail"]:
                body += f'<div class="dt">{_esc(it["detail"])}</div>'
            body += '</div>'
        body += '</div>'
    if summary:
        body += f'<div class="sumbox"><div class="lbl">一句話</div><div class="txt">{_esc(summary)}</div></div>'
    return (
        "<!DOCTYPE html>\n<html lang=\"zh-TW\"><head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "<meta name=\"robots\" content=\"noindex, nofollow, noarchive, nosnippet\">\n"
        "<title>午餐小抄</title>\n<style>" + CARD_CSS + "</style></head><body>\n" + body + "\n</body></html>"
    )
