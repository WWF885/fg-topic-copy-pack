#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选题全量文案包 · 交付前硬校验
用法：
    python3 validate_pack.py manifest.json
    python3 validate_pack.py manifest.json --mode short

manifest.json 结构：
{
  "topic": "选题名称",
  "mode": "long",                       # long(默认,约3分钟) | short(60秒)
  "sections": {
    "oral":    {"title": "", "cover": "第一行／第二行", "script": "", "publish": ""},
    "radio":   {"title": "", "cover": "", "script": "", "publish": ""},
    "wechat":  {"title": "", "cover": "", "summary": "",
                "sections": [{"heading": "", "text": ""}, ...],   # 必须6节
                "images": [{"pos": "", "desc": ""}, ...],         # 最多5张
                "publish": ""},
    "graphic": {"titles": ["", "", ""], "cover": "", "publish": "",
                "cards": [{"name": "", "text": ""}, ...]}         # 6–9张
  }
}
"""
import argparse
import json
import re
import sys
import unicodedata

FORBIDDEN_IN_VIDEO = re.compile(r"公众号|微信|加V|二维码|主页有|私信|回复.{0,3}关键词")
FORBIDDEN_IN_XHS = re.compile(r"公众号|微信|加V|二维码|主页有|私信|回复.{0,3}关键词")
CJK_ASCII = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")

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


def check_forbidden(name, text, pattern, where):
    hit = pattern.findall(text or "")
    if hit:
        add("E", "LEAK", f"{name} {where} 出现站外引流词：{'、'.join(sorted(set(hit))}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--mode", choices=["long", "short"], default=None)
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        data = json.load(f)

    mode = args.mode or data.get("mode", "long")
    sec = data.get("sections", {})

    for key in ("oral", "radio", "wechat", "graphic"):
        if key not in sec:
            add("E", "MISSING", f"缺少 {key} 板块")

    # 口播视频
    oral = sec.get("oral", {})
    if oral:
        check_range("口播标题", oral.get("title", ""), 6, 20)
        check_cover("口播", oral.get("cover", ""))
        lo, hi = (900, 1150) if mode == "long" else (240, 300)
        check_range(f"口播逐字稿({'3分钟' if mode == 'long' else '60秒'})",
                    oral.get("script", ""), lo, hi)
        check_range("口播发布文案", oral.get("publish", ""), 140, 240)
        for f in ("title", "script", "publish"):
            check_forbidden("口播", oral.get(f, ""), FORBIDDEN_IN_VIDEO, f"的 {f}")

    # 广播音频
    radio = sec.get("radio", {})
    if radio:
        check_range("广播标题", radio.get("title", ""), 6, 20)
        check_cover("广播", radio.get("cover", ""))
        check_range("广播稿", radio.get("script", ""), 1000, 1250)
        check_range("广播发布文案", radio.get("publish", ""), 140, 240)
        if "AI旅者广播站" not in (radio.get("script", "") or ""):
            add("W", "CTA", "广播稿未出现节目名《AI旅者广播站》")

    # 公众号
    wx = sec.get("wechat", {})
    if wx:
        check_range("公众号标题", wx.get("title", ""), 6, 20)
        check_cover("公众号", wx.get("cover", ""))
        check_range("公众号摘要", wx.get("summary", ""), 50, 120)
        body = wx.get("sections", []) or []
        if len(body) != 6:
            add("E", "SECTION", f"公众号正文需 6 节，现有 {len(body)} 节")
        total = 0
        for i, s in enumerate(body, 1):
            total += char_count(s.get("text", ""))
            check_range(f"公众号正文第{i}节", s.get("text", ""), 130, 280)
            if not (s.get("heading") or "").strip():
                add("E", "HEADING", f"公众号正文第{i}节缺小标题")
        if total < 1000 or total > 1600:
            add("E", "LEN", f"公众号正文合计 {total} 字，要求 1000–1600 字")
        imgs = wx.get("images", []) or []
        if len(imgs) > 5:
            add("E", "IMG", f"公众号配图 {len(imgs)} 张，最多 5 张")
        check_range("公众号发布文案", wx.get("publish", ""), 140, 240)

    # 种草图文
    gr = sec.get("graphic", {})
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

    print(f"选题：{data.get('topic', '（未填）')}｜口播口径：{mode}")
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
