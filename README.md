# 美食地点助手 (Food Location CLI)

A CLI tool for storing and querying food shop records. Screenshot analysis and LLM interaction are handled entirely by the nanobot agent — this tool focuses on persistence and lookup.

## Architecture

```
User screenshot
      │
      ▼
  nanobot agent
  (LLM via OpenRouter)
      │  extracts JSON
      ▼
python food_cli.py ingest '<json>'
      │
      ├─► Google Places API  (rating, address, official Maps URL)
      │   or Maps search URL (fallback, no API key needed)
      │
      ▼
  SQLite database
      │
python food_cli.py find / list
      │
      ▼
  Simplified Chinese output
```

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # optional: add GOOGLE_PLACES_API_KEY
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_PLACES_API_KEY` | No | Google Places (New) API key — enables real ratings, addresses, and Maps links. Without it, a Google Maps search URL is generated instead. |
| `FOOD_DB_PATH` | No | Path to the SQLite database file (default: `food_locations.db` in CWD) |

## Commands

### `ingest` — Store extracted shop data

Accepts a JSON string as an argument or via stdin.

```bash
python food_cli.py ingest '<json>' [-l LOCATION]
echo '<json>' | python food_cli.py ingest
```

**JSON schema** (produced by the LLM extraction step in nanobot):

```json
{
  "shop_name":   "店铺名称",
  "food_types":  ["食物类型1", "食物类型2"],
  "location":    "地区（如：芙蓉）",
  "address":     "完整地址（可选）",
  "description": "招牌菜或店铺特色（可选）"
}
```

Only `shop_name` is required. The `-l / --location` flag fills in `location` if omitted from the JSON.

**Example:**

```bash
python food_cli.py ingest '{"shop_name":"老爸肉骨茶","food_types":["肉骨茶","猪杂汤"],"location":"芙蓉","description":"汤底浓郁，猪肋骨入味"}'
```

```
已成功储存：

店名      : 老爸肉骨茶
食物类型  : 肉骨茶 | 猪杂汤
地区      : 芙蓉
地址      : No 12, Jalan Yam Tuan, Seremban
评分      : ★★★★☆  4.2/5
Google 地图: https://maps.google.com/?cid=...
推荐理由  : 汤底浓郁，猪肋骨入味
记录 ID   : 1
```

---

### `find` — Query by food type

```bash
python food_cli.py find <food_type> [-l LOCATION] [--json-output]
```

Search is substring-based: `鸡饭` matches `海南鸡饭`.

```bash
python food_cli.py find 肉骨茶 -l 芙蓉
python food_cli.py find "bak kut teh" --json-output
```

---

### `list` — List all shops

```bash
python food_cli.py list [-l LOCATION] [--json-output]
```

---

### `delete` — Remove a record

```bash
python food_cli.py delete <shop_id>
```

---

### `refresh` — Update Google Maps info

```bash
python food_cli.py refresh <shop_id>
```

Requires `GOOGLE_PLACES_API_KEY`. Useful if a shop was ingested before the key was configured.

---

## Notes

- The database is a plain SQLite file — back it up by copying the `.db` file.
- All user-facing output is in Simplified Chinese.
- `--json-output` on `find` and `list` emits a JSON array for downstream processing.
- The `GOOGLE_PLACES_API_KEY` needs the **Places API (New)** product enabled in Google Cloud Console.
