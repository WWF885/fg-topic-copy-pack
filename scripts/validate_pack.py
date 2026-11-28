#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选题全量文案包 · 交付前硬校验
用法：
    python3 validate_pack.py manifest.json
    python3 validate_pack.py manifest.json --mode short
    python3 validate_pack.py manifest.json --platforms wechat

manifest.json 结构：
{
  "topic": "选题名", "mode": "long|short",
  "sections": {
    "oral":    {"title","cover","script","publish"},
    "radio":   {"title","cover","script","publish"},
    "wechat":  {"title","cover","summary","sections":[{"heading","text"}],"boards":[{"sec","caption","file"}],"publish"},
    "graphic": {"titles":[...],"cover","publish","cards":[{"name","text"}]}
  },
  "lead": {"name":"《XX手册》","keyword":"手册","path":"XTxxx_XX手册.html","sections":["..."]}
}
"""
import argparse
import json
import os
import re
import sys

FORBIDDEN_IN_VIDEO = re.compile(r"公众号|微信|加V|二维码|主页有|私信|回复.{0,3}关键词")
FORBIDDEN_IN_XHS = re.compile(r"公众号|微信|加V|二维码|主页有|私信|回复.{0,3}关键词")
FORBIDDEN_IN_LEAD = re.compile(r"扫码|扫一扫|加微信|私信我|进群|二维码")
LEAD_EXTERNAL = re.compile(r'<link[^>]+href="http|<script[^>]+src="http|<img[^>]+src="http|@import\s+url\(http|url\(https?://')
CJK_ASCII = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")
AI_FLAVOR_HARD = re.compile(r"赋能|闭环|底层逻辑|值得注意的是|综上所述|生态位|组合拳|抓手|颗粒度")
AI_FLAVOR_SOFT = re.compile(r"首先|其次|此外|第一，|第二，|总而言之|不难发现")

errors, warnings = [], []


def char_count(text):
    return len(re.sub(r"\s", "", text or ""))


def add(kind, code, msg):
    (errors if kind == "E" else warnings).append(f"[{code}] {msg}")


def check_range(name, text, lo, hi):
    n = char_count(text)
    if n == 0:
        add("E", "EMPTY", f"{name} 为空")
    elif n < lo or n > hi:
        add("E", "LEN", f"{name} 现有 {n} 字，要求 {lo}–{hi} 字")
    return n


def cover_parts(cover):
    for sep in ("／", "/", "|"):
        if sep in (cover or ""):
            return [p.strip() for p in cover.split(sep) if p.strip()]
    return []


def check_cover(name, cover):
    parts = cover_parts(cover)
    if len(parts) != 2:
        add("E", "COVER", f"{name} 封面需两行并用「／」分隔，现有：{cover!r}")
        return
    for p in parts:
        n = len(CJK_ASCII.findall(p))
        if n < 2 or n > 4:
            add("E", "COVER", f"{name} 封面「{p}」为 {n} 字，每行需 2–4 字")


def check_ai_flavor(name, text):
    hard = AI_FLAVOR_HARD.findall(text or "")
    if hard:
        add("E", "AI", f"{name} 出现 AI 味硬禁词：" + "、".join(sorted(set(hard))))
    soft = AI_FLAVOR_SOFT.findall(text or "")
    if len(soft) > 2:
        add("W", "AI", f"{name} 模板化连接词 {len(soft)} 处（{'、'.join(sorted(set(soft)))}），建议删到 2 处以内")


def check_forbidden(name, text, pattern, where):
    hit = pattern.findall(text or "")
    if hit:
        words = "、".join(sorted(set(hit)))
        add("E", "LEAK", f"{name} {where} 出现站外引流词：{words}")


def check_lead(lead, oral, graphic, base_dir, allowed=None):
    """引流资料：资料名、关键词、HTML 实体三者必须互相对得上。"""
    if not lead:
        add("E", "LEAD", "缺少 lead 板块：文案承诺的资料必须有对应的 HTML 实体")
        return
    name = (lead.get("name") or "").strip()
    kw = (lead.get("keyword") or "").strip()
    path = (lead.get("path") or "").strip()
    sections = lead.get("sections") or []

    if not name:
        add("E", "LEAD", "lead.name 为空：资料名必须与文案 CTA 承诺一致")
    else:
        n = len(CJK_ASCII.findall(name))
        if n < 4 or n > 20:
            add("E", "LEAD", f"资料名「{name}」为 {n} 字，要求 4–20 字")
        if not re.search("《.*》", name):
            add("W", "LEAD", f"资料名「{name}」建议加书名号《》，便于文案里统一指代")

    if not kw:
        add("E", "LEAD", "lead.keyword 为空")
    else:
        n = len(CJK_ASCII.findall(kw))
        if n < 2 or n > 6:
            add("E", "LEAD", f"关键词「{kw}」为 {n} 字，要求 2–6 字")
        pairs = [("口播发布文案", oral.get("publish", ""), "oral"), ("种草发布文案", graphic.get("publish", ""), "graphic")]
        for label, body, key in pairs:
            if allowed and key not in allowed:
                continue
            if body and kw not in body:
                add("E", "LEAD", f"{label} 未出现关键词「{kw}」，与资料对不上")

    if not (6 <= len(sections) <= 9):
        add("E", "LEAD", f"资料结构需 6–9 块，现有 {len(sections)} 块")

    if not path:
        add("E", "LEAD", "lead.path 为空：未指向 HTML 文件")
        return
    if not path.endswith(".html"):
        add("E", "LEAD", f"lead.path 需为 .html，现有 {path}")
        return

    fp = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(fp):
        add("E", "LEAD", f"找不到 HTML 文件：{path}")
        return

    size = os.path.getsize(fp)
    if size > 800 * 1024:
        add("E", "LEAD", f"HTML 体积 {size / 1024:.0f}KB，超过 800KB 上限")

    with open(fp, encoding="utf-8", errors="ignore") as f:
        html_text = f.read()

    if name:
        bare = name.strip("《》")
        if bare and bare not in html_text:
            add("E", "LEAD", f"HTML 页面未出现资料名「{bare}」")
    if kw and kw not in html_text:
        add("E", "LEAD", f"HTML 页面未出现关键词「{kw}」")
    if LEAD_EXTERNAL.search(html_text):
        add("E", "LEAD", "HTML 引用了外链资源（CDN/字体/图片），断网会打不开")
    hit = FORBIDDEN_IN_LEAD.findall(html_text)
    if hit:
        add("E", "LEAD", "HTML 出现违规引流词：" + "、".join(sorted(set(hit))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--mode", choices=["long", "short"], default=None)
    ap.add_argument("--platforms", default="oral,radio,wechat,graphic",
                    help="逗号分隔，只校验指定平台，如 --platforms wechat（用户只要单平台时用）")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        data = json.load(f)

    mode = args.mode or data.get("mode", "long")
    allowed = {p.strip() for p in args.platforms.split(",") if p.strip()}
    unknown = allowed - {"oral", "radio", "wechat", "graphic"}
    if unknown:
        add("E", "PLATFORM", "未知平台：" + "、".join(sorted(unknown)))
    base_dir = os.path.dirname(os.path.abspath(args.manifest))
    sec = data.get("sections", {})

    for key in ("oral", "radio", "wechat", "graphic"):
        if key in allowed and key not in sec:
            add("E", "MISSING", f"缺少 {key} 板块")

    oral = sec.get("oral", {}) if "oral" in allowed else {}
    if oral:
        check_range("口播标题", oral.get("title", ""), 6, 20)
        check_cover("口播", oral.get("cover", ""))
        lo, hi = (800, 1000) if mode == "long" else (240, 300)
        tag = "3分钟" if mode == "long" else "60秒"
        check_range(f"口播逐字稿({tag})", oral.get("script", ""), lo, hi)
        check_range("口播发布文案", oral.get("publish", ""), 140, 240)
        for f in ("title", "script", "publish"):
            check_forbidden("口播", oral.get(f, ""), FORBIDDEN_IN_VIDEO, f"的 {f}")

    radio = sec.get("radio", {}) if "radio" in allowed else {}
    if radio:
        check_range("广播标题", radio.get("title", ""), 6, 20)
        check_cover("广播", radio.get("cover", ""))
        check_range("广播稿", radio.get("script", ""), 1900, 2100)
        check_range("广播发布文案", radio.get("publish", ""), 140, 240)
        if "AI旅者广播站" not in (radio.get("script", "") or ""):
            add("W", "CTA", "广播稿未出现节目名《AI旅者广播站》")

    wx = sec.get("wechat", {}) if "wechat" in allowed else {}
    if wx:
        check_range("公众号标题", wx.get("title", ""), 6, 20)
        check_cover("公众号", wx.get("cover", ""))
        check_range("公众号摘要", wx.get("summary", ""), 50, 120)
        body = wx.get("sections", []) or []
        if not (6 <= len(body) <= 8):
            add("E", "SECTION", f"公众号正文需 6–8 节，现有 {len(body)} 节")
        total = 0
        for i, s_ in enumerate(body, 1):
            total += char_count(s_.get("text", ""))
            check_range(f"公众号正文第{i}节", s_.get("text", ""), 150, 300)
            if not (s_.get("heading") or "").strip():
                add("E", "HEADING", f"公众号正文第{i}节缺小标题")
        if total < 1350 or total > 1650:
            add("E", "LEN", f"公众号正文合计 {total} 字，要求 1350–1650 字（目标1500）")

        boards = wx.get("boards", []) or []
        if not (6 <= len(boards) <= 8):
            add("E", "BOARD", f"公众号画板需 6–8 张（一节一张），现有 {len(boards)} 张")
        if body and len(boards) and len(boards) < len(body) - 1:
            add("E", "BOARD", f"画板 {len(boards)} 张少于节数 {len(body)}，除引流收束节外每节都要有")
        for i, b in enumerate(boards, 1):
            cap = (b.get("caption") or "").strip()
            if not cap:
                add("E", "BOARD", f"画板{i:02d} 缺 caption（要让人看懂的结论）")
            elif len(CJK_ASCII.findall(cap)) > 12:
                add("E", "BOARD", f"画板{i:02d} 结论条「{cap}」超过 12 字")
            sec_id = str(b.get("sec") or "").strip()
            if not sec_id:
                add("E", "BOARD", f"画板{i:02d} 未标注对应节 sec")
            f_ = (b.get("file") or "").strip().lstrip("@./")
            if not f_:
                add("E", "BOARD", f"画板{i:02d} 缺 file")
            else:
                if not f_.endswith(".svg"):
                    add("W", "BOARD", f"画板{i:02d} 文件 {f_} 不是 .svg，飞书画板建议用 SVG")
                fp = f_ if os.path.isabs(f_) else os.path.join(base_dir, f_)
                if not os.path.exists(fp):
                    add("E", "BOARD", f"找不到画板文件：{f_}")
        check_range("公众号发布文案", wx.get("publish", ""), 140, 240)

    gr = sec.get("graphic", {}) if "graphic" in allowed else {}
    if gr:
        titles = gr.get("titles", []) or []
        if len(titles) != 3:
            add("E", "TITLE", f"种草标题备选需 3 条，现有 {len(titles)} 条")
        for i, t in enumerate(titles, 1):
            check_range(f"种草标题{i}", t, 6, 20)
            check_forbidden("种草", t, FORBIDDEN_IN_XHS, f"标题{i}")
        check_cover("种草", gr.get("cover", ""))
        check_range("种草发布文案", gr.get("publish", ""), 260, 380)
        check_forbidden("种草", gr.get("publish", ""), FORBIDDEN_IN_XHS, "发布文案")
        cards = gr.get("cards", []) or []
        if not (6 <= len(cards) <= 9):
            add("E", "CARD", f"知识卡片需 6–9 张，现有 {len(cards)} 张")
        for i, c in enumerate(cards, 1):
            if not (c.get("name") or "").strip():
                add("E", "CARD", f"卡{i:02d} 缺卡名")
            check_range(f"卡{i:02d} 内容", c.get("text", ""), 60, 160)

    if data.get("lead") or allowed == {"oral", "radio", "wechat", "graphic"}:
        check_lead(data.get("lead"), oral, gr, base_dir, allowed)
    else:
        add("W", "LEAD", "本次只校验部分平台且未填 lead，已跳过资料一致性检查")

    check_ai_flavor("口播逐字稿", oral.get("script", ""))
    check_ai_flavor("广播稿", radio.get("script", ""))
    check_ai_flavor("公众号正文", "".join(s_.get("text", "") for s_ in (wx.get("sections") or [])))
    check_ai_flavor("种草发布文案", gr.get("publish", ""))

    print(f"选题：{data.get('topic', '（未填）')}｜口播口径：{mode}｜资料：《{ (data.get('lead') or {}).get('name','').strip('《》') or '未填'}》")
    print(f"错误 {len(errors)} 项，提醒 {len(warnings)} 项")
    for e in errors:
        print("  ✗", e)
    for w in warnings:
        print("  !", w)
    if errors:
        print("结论：不通过，改完再交付。")
        return 1
    print("结论：通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
