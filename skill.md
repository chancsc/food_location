# Skill: 美食地点助手 (Food Location Finder)

## Purpose

This skill lets the nanobot agent record food shops from screenshots and answer user questions like "哪里有肉骨茶？" ("Where can I find bak kut teh?") — replies are always in **Simplified Chinese**.

The underlying tool is a Python CLI (`food_cli.py`) backed by a local SQLite database enriched with Google Maps data.

---

## Prerequisites

- Python 3.11+
- Dependencies installed: `pip install -r requirements.txt`
- `.env` file present with at minimum `OPENROUTER_API_KEY` set
- Working directory: the folder containing `food_cli.py`

**Key env vars for nanobot:**

| Variable | Required | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter key — routes vision requests to the selected LLM |
| `OPENROUTER_MODEL` | No | Vision-capable model slug (default `google/gemini-flash-1.5`). Nanobot can override per-session. |
| `GOOGLE_PLACES_API_KEY` | No | Enables real ratings + Maps links; falls back to a search URL |

---

## Commands Reference

### 1. Ingest a screenshot

```bash
python food_cli.py ingest <image_path> [-l <location_hint>]
```

| Argument | Type | Required | Description |
|---|---|---|---|
| `image_path` | string | Yes | Absolute or relative path to image (JPG/PNG/WEBP/GIF) |
| `-l / --location` | string | No | Area hint if not visible in image (e.g. `芙蓉`, `Seremban`) |

**When to use:** User sends a food photo or shop screenshot and wants it saved.

**Example invocation:**
```bash
python food_cli.py ingest /tmp/upload_1234.jpg -l 芙蓉
```

**Output:** Human-readable Simplified Chinese confirmation with shop details.

---

### 2. Find shops by food type

```bash
python food_cli.py find "<food_type>" [-l <location>] [--json-output]
```

| Argument | Type | Required | Description |
|---|---|---|---|
| `food_type` | string | Yes | Food name in Chinese or English (e.g. `肉骨茶`, `海南鸡饭`) |
| `-l / --location` | string | No | Area filter (e.g. `芙蓉`, `Seremban`) |
| `--json-output` | flag | No | Emit JSON array instead of formatted text |

**When to use:** User asks "芙蓉哪里有肉骨茶？" or "which shops near Seremban serve Hainanese chicken rice?"

**Example invocations:**
```bash
python food_cli.py find "肉骨茶" -l 芙蓉
python food_cli.py find "海南鸡饭" --json-output
```

**Formatted output fields (each shop):**
- 店名 — shop name
- 食物类型 — food categories (pipe-separated)
- 地区 — area / district
- 地址 — full address (if available)
- 评分 — star rating out of 5
- Google 地图 — Google Maps URL (direct link or search URL)
- 推荐理由 — editorial description / why it's good
- 记录 ID — database ID

**JSON output fields:** same keys as above plus `id`, `created_at`, `updated_at`, `google_place_id`.

---

### 3. List all shops

```bash
python food_cli.py list [-l <location>] [--json-output]
```

**When to use:** User asks for a general overview or "show me everything in Seremban".

---

### 4. Delete a shop

```bash
python food_cli.py delete <shop_id>
```

**When to use:** User says "remove that entry" or "delete shop ID 3".

---

### 5. Refresh Google Maps info

```bash
python food_cli.py refresh <shop_id>
```

**When to use:** User wants updated ratings/addresses for an existing record, or the record was added before `GOOGLE_PLACES_API_KEY` was configured.

---

## Typical Conversation Flows

### Flow A — User sends a screenshot

1. Save the image attachment to a temp file (e.g. `/tmp/food_img.jpg`).
2. Run: `python food_cli.py ingest /tmp/food_img.jpg -l <location if known>`
3. Return the CLI output verbatim (already in Simplified Chinese).

### Flow B — User asks for a food recommendation

User says: **"芙蓉哪里有好吃的肉骨茶？"**

1. Run: `python food_cli.py find "肉骨茶" -l 芙蓉`
2. If results found — return the formatted output, highlighting the Google Maps link and rating.
3. If no results — reply: "数据库中暂无芙蓉地区肉骨茶的记录，请分享相关截图让我添加。"

### Flow C — User asks for all shops in an area

User says: **"芙蓉有哪些美食？"**

1. Run: `python food_cli.py list -l 芙蓉`
2. Summarise the list in Chinese, grouping by food type if helpful.

### Flow D — Structured data needed

Append `--json-output` to any `find` or `list` command, then parse the JSON array for downstream processing.

---

## Output Language

All CLI output (except error messages directed to stderr) is in **Simplified Chinese**. The agent should relay this output directly without translation.

---

## Error Handling

| Exit code | Meaning | Suggested agent response |
|---|---|---|
| 0 | Success | Return stdout to user |
| 1 | Error (see stderr) | Relay the error message and ask user to clarify or retry |

Common errors:
- `OPENROUTER_API_KEY is not set` — instruct user to set the env var
- `找不到文件` — image path is wrong; ask user to resend
- `未能识别出店铺信息` — image is unclear; ask for a better screenshot

---

## Data Notes

- Database is a local SQLite file (`food_locations.db` by default, configurable via `FOOD_DB_PATH`).
- Food type search is substring-based — searching `鸡饭` will match `海南鸡饭`.
- Location search matches both `location` (district) and `address` fields.
- Google Maps URLs are direct `https://maps.google.com/` links when `GOOGLE_PLACES_API_KEY` is set, or `https://www.google.com/maps/search/...` search URLs otherwise.
