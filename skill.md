# Skill: 美食地点助手 (Food Location Finder)

## Purpose

Store food shop records extracted from screenshots and answer user questions like "芙蓉哪里有肉骨茶？" ("Where can I find bak kut teh in Seremban?").

**Division of responsibility:**

| Who | What |
|---|---|
| **nanobot** | Receives screenshot → sends to LLM via OpenRouter → extracts JSON |
| **this CLI** | Receives JSON → stores in DB → enriches with Google Places → answers queries in Simplified Chinese |

The CLI does **no LLM calls**. All AI work is done by nanobot before calling `ingest`.

---

## Prerequisites

- Python 3.11+
- `pip install -r requirements.txt`
- Working directory: folder containing `food_cli.py`
- (Optional) `.env` with `GOOGLE_PLACES_API_KEY` for real ratings and Maps links

---

## Commands Reference

### 1. Store extracted shop data

```bash
python food_cli.py ingest '<json_string>' [-l <location>]
```

or via stdin:

```bash
echo '<json_string>' | python food_cli.py ingest
```

**JSON schema** (nanobot constructs this from LLM output):

```json
{
  "shop_name":   "店铺名称（必填）",
  "food_types":  ["食物类型1", "食物类型2"],
  "location":    "地区，如：芙蓉、Seremban",
  "address":     "完整地址（如可见）",
  "description": "店铺特色或招牌菜简短描述"
}
```

Only `shop_name` is required. Use `-l` to supply location when the LLM didn't extract one.

**When to use:** After nanobot receives a food screenshot and the LLM returns extracted shop info.

**Example nanobot invocation:**

```bash
python food_cli.py ingest '{"shop_name":"老爸肉骨茶","food_types":["肉骨茶"],"location":"芙蓉","description":"汤底浓郁，猪肋骨入味"}'
```

**Auto-enrichment:** every `ingest` call automatically queries Google Places (if `GOOGLE_PLACES_API_KEY` is set) to fill in address, rating, and Maps URL — even if the LLM only returned a shop name.

---

### 2. Look up a shop by name or URL (no screenshot needed)

```bash
python food_cli.py lookup "<name_or_url>" [-l <location>] [-t <food_type>]
```

| Argument | Required | Description |
|---|---|---|
| `name_or_url` | Yes | Shop name (e.g. `老爸肉骨茶`) or a Google Maps URL |
| `-l / --location` | No | Area hint (e.g. `芙蓉`) |
| `-t / --food-type` | No | Food type tag, repeatable (e.g. `-t 肉骨茶 -t 猪杂汤`) |

**When to use:**
- User mentions a shop name without a screenshot
- User pastes a Google Maps link
- Nanobot extracts a Maps URL from conversation and wants to store it

**Examples:**
```bash
python food_cli.py lookup "老爸肉骨茶" -l 芙蓉 -t 肉骨茶
python food_cli.py lookup "https://maps.google.com/?place_id=ChIJ..."
```

Without `GOOGLE_PLACES_API_KEY`, creates a basic record with a Maps search URL.

---

### 3. Find shops by food type

```bash
python food_cli.py find "<food_type>" [-l <location>] [--json-output]
```

| Argument | Required | Description |
|---|---|---|
| `food_type` | Yes | Chinese or English (e.g. `肉骨茶`, `海南鸡饭`, `bak kut teh`) |
| `-l / --location` | No | Area filter (e.g. `芙蓉`, `Seremban`) |
| `--json-output` | No | Emit JSON array instead of formatted text |

Search is substring-based: `鸡饭` matches `海南鸡饭`.

**When to use:** User asks "芙蓉哪里有肉骨茶？" or "which shops near Seremban serve Hainanese chicken rice?"

**Example:**
```bash
python food_cli.py find "肉骨茶" -l 芙蓉
```

**Output per shop includes:**
- 店名, 食物类型, 地区, 地址, 评分 (★ stars), Google 地图 URL, 推荐理由, 记录 ID

---

### 4. List all shops

```bash
python food_cli.py list [-l <location>] [--json-output]
```

**When to use:** User asks for a general overview or "show me all shops in Seremban".

---

### 5. Delete a shop

```bash
python food_cli.py delete <shop_id>
```

---

### 6. Refresh Google Maps info

```bash
python food_cli.py refresh <shop_id>
```

Re-queries Google Places for an existing record. Use if `GOOGLE_PLACES_API_KEY` was added after a shop was ingested.

---

## Typical Conversation Flows

### Flow A — User sends a food screenshot

1. Nanobot calls LLM with the image and this prompt (adapt as needed):

   > 请分析图片提取美食店铺信息，返回 JSON：{"shop_name","food_types","location","address","description"}，只返回 JSON。

2. LLM returns JSON string.
3. Nanobot runs:
   ```bash
   python food_cli.py ingest '<llm_json>' [-l <location_if_known>]
   ```
4. Return CLI stdout to user (already in Simplified Chinese).

### Flow B — User asks for a food recommendation

User says: **"芙蓉哪里有好吃的肉骨茶？"**

```bash
python food_cli.py find "肉骨茶" -l 芙蓉
```

- Results found → relay output, highlight Google Maps link and rating.
- No results → reply: "数据库中暂无芙蓉地区肉骨茶的记录，请分享相关截图让我添加。"

### Flow C — User asks what's available in an area

User says: **"芙蓉有哪些美食？"**

```bash
python food_cli.py list -l 芙蓉
```

### Flow D — User mentions a shop name or pastes a Maps link

User says: **"我知道芙蓉有一家叫老爸肉骨茶，帮我加进去"**
or pastes a Google Maps URL.

```bash
# By name
python food_cli.py lookup "老爸肉骨茶" -l 芙蓉 -t 肉骨茶

# By URL
python food_cli.py lookup "https://maps.google.com/?place_id=ChIJ..."
```

CLI auto-fetches address, rating, and Maps link from Google Places and stores the record.

### Flow E — Structured data for downstream processing

```bash
python food_cli.py find "肉骨茶" --json-output
python food_cli.py list --json-output
```

---

## Output Language

All stdout is in **Simplified Chinese**. Relay it directly without translation.

---

## Error Handling

| Exit code | Meaning | Suggested response |
|---|---|---|
| 0 | Success | Return stdout to user |
| 1 | Error (stderr has details) | Relay error, ask user to clarify or retry |

Common errors:

- `缺少必填字段 shop_name` — LLM extraction missed the shop name; ask for a clearer screenshot
- `JSON 解析失败` — malformed JSON from LLM; retry extraction with a stricter prompt
- `找不到 ID 为 X 的记录` — wrong shop ID; use `list` to check available IDs

---

## Data Notes

- Local SQLite file (`food_locations.db` by default, set `FOOD_DB_PATH` to override).
- Location search matches both `location` (district) and `address` fields.
- Google Maps URL is a direct `https://maps.google.com/` link when `GOOGLE_PLACES_API_KEY` is set, or a `https://www.google.com/maps/search/...` search URL otherwise.
