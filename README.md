# Topic Copy Pack · 选题全量文案包

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](VERSION)

> 一个选题进去，四平台成品加一篇结构化飞书文档出来。

---

## 它解决什么问题

同一件事，要写成口播稿、广播稿、公众号长文、小红书图文，大多数人是在一份稿子上改四遍。结果是四个平台都像同一个人的同一篇文章：视频不抓人，广播不陪人，公众号没论证，图文没干货。

本 Skill 的做法是：**把四个平台当成四种文体，分别成稿，再装进同一副文档骨架。**

---

## 核心特性

| 特性 | 说明 |
|---|---|
| **一题四稿** | 口播视频、广播音频、公众号软文、种草图文，各自独立结构 |
| **固定文档骨架** | 章节名、编号、层级一字不改，四平台对齐可比 |
| **平台规则内置** | 字数区间、钩子位置、节奏、结尾动作，写死在规范里 |
| **引流合规硬校验** | 视频/小红书零站外引流，只有公众号/广播站可导私域 |
| **知识卡片规范** | 6–9 张 3:4，筛选→拆解→模板→验收→总表→行动 |
| **交付前自检** | 脚本校验字数、封面、卡片数、违规词，不合格不交付 |

---

## 快速开始

```bash
# 交付前硬校验（manifest 结构见脚本头部注释）
python3 scripts/validate_pack.py manifest.json
python3 scripts/validate_pack.py manifest.json --mode short
```

在 Agent 里直接说：

> 用「选题全量文案包」，把《我想用AI把过去的工作重新做一遍》做成一整套四平台文案。

---

## 目录

```
SKILL.md                流程总纲（Agent 入口）
agents/doubao.yaml      豆包技能面板配置
references/
  doc-skeleton.md       飞书文档骨架（XML 模板）
  platform-specs.md     四平台字数、结构、引流合规
  ip-persona.md         人设、语气、金句、禁区
  card-specs.md         知识卡片规范
scripts/
  validate_pack.py      交付前硬校验
```

---

## 设计哲学

1. **骨架固定，内容自由。** 结构统一才能批量生产，也才能对比优劣。
2. **四种文体，不做四份改写。** 口播靠钩子，广播靠陪伴，公众号靠论证，图文靠卡片。
3. **合规写进脚本。** 靠提醒守不住，靠校验才守得住。
4. **没跑通就说没跑通。** 不编数据、不编案例、不编身份。

---

## License

MIT © 2026 WWF885
