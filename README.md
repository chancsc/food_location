# 美食地点助手 (Food Location CLI)

A CLI tool that reads food screenshots, extracts shop metadata with Claude Vision, and lets you query shops by food type and area — responses in Simplified Chinese.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and fill in environment variables
cp .env.example .env
# Edit .env — set at minimum ANTHROPIC_API_KEY

# 3. Run
python food_cli.py --help
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key — routes vision requests to your chosen LLM |
| `OPENROUTER_MODEL` | No | Model to use for vision extraction (default: `google/gemini-flash-1.5`). Any vision-capable model on OpenRouter works, e.g. `anthropic/claude-sonnet-4-5`, `openai/gpt-4o` |
| `GOOGLE_PLACES_API_KEY` | No | Google Places (New) API key — enables real ratings, addresses, and Maps links. Without it, a Google Maps search URL is generated instead. |
| `FOOD_DB_PATH` | No | Path to the SQLite database file (default: `food_locations.db` in CWD) |

## Commands

### `ingest` — Add a shop from a screenshot

```bash
python food_cli.py ingest <image_path> [-l LOCATION]
```

- `image_path` — local path to a JPG, PNG, WEBP, or GIF screenshot
- `-l / --location` — optional area hint (e.g. `芙蓉`, `Seremban`) used if the image does not show a location

**Example:**

```bash
python food_cli.py ingest ~/screenshots/bkt_shop.jpg -l Seremban
```

**Output (Simplified Chinese):**

```
正在分析图片：bkt_shop.jpg …
已识别店铺：老爸肉骨茶（芙蓉）
正在查询 Google 地图信息 …

已成功储存：

店名      : 老爸肉骨茶
食物类型  : 肉骨茶 | 猪杂汤
地区      : 芙蓉
地址      : No 12, Jalan Yam Tuan, Seremban
评分      : ★★★★☆  4.2/5
Google 地图: https://maps.google.com/?cid=...
推荐理由  : 芙蓉老字号肉骨茶，汤底浓郁，猪肋骨入味
记录 ID   : 1
```

---

### `find` — Query shops by food type

```bash
python food_cli.py find <food_type> [-l LOCATION] [--json-output]
```

- `food_type` — Chinese or English food name (e.g. `肉骨茶`, `海南鸡饭`, `bak kut teh`)
- `-l / --location` — filter by area (e.g. `芙蓉`, `Seremban`)
- `--json-output` — emit raw JSON (used by nanobot agents)

**Example:**

```bash
python food_cli.py find 肉骨茶 -l 芙蓉
```

```
找到 2 家店铺提供「肉骨茶」（芙蓉 地区）：

── 第 1 家 ──
店名      : 老爸肉骨茶
...

── 第 2 家 ──
店名      : 明记肉骨茶
...
```

---

### `list` — List all stored shops

```bash
python food_cli.py list [-l LOCATION] [--json-output]
```

---

### `delete` — Remove a shop by ID

```bash
python food_cli.py delete <shop_id>
```

---

### `refresh` — Update Google Maps info for an existing shop

```bash
python food_cli.py refresh <shop_id>
```

Requires `GOOGLE_PLACES_API_KEY`. Useful if a shop was ingested before the API key was configured.

---

## How It Works

```
screenshot ──► Claude Vision ──► extracted JSON
                                     │
                              Google Places API
                              (or Maps search URL)
                                     │
                               SQLite database
                                     │
                          find / list ──► Simplified Chinese output
```

1. **`ingest`** sends the image to the configured OpenRouter model (default: `google/gemini-flash-1.5`) which extracts shop name, food types, location, address, and a description in Simplified Chinese. The model is selectable via `OPENROUTER_MODEL`.
2. The tool enriches the record with Google Places data (rating, official Maps URL, editorial summary) if `GOOGLE_PLACES_API_KEY` is set.
3. Everything is stored in a local SQLite database (`food_locations.db` by default).
4. **`find`** performs a full-text substring search across `food_types`, `shop_name`, `description`, and optionally filters by `location` / `address`.

## Notes

- The database is a plain SQLite file — back it up by copying the `.db` file.
- All user-facing output is in Simplified Chinese; use `--json-output` for machine-readable results.
- The `GOOGLE_PLACES_API_KEY` needs the **Places API (New)** product enabled in Google Cloud Console.
