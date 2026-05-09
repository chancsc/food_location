#!/usr/bin/env python3
"""美食地点助手 CLI — 储存美食店铺信息，按食物类型或地区查询。

摄取流程由 nanobot 负责：
  nanobot 将截图发送给 LLM → 获取 JSON 提取结果 → 调用 ingest 命令存入数据库。
"""

import json
import os
import sys

import click
from dotenv import load_dotenv

from database import FoodDatabase
from places import fallback_maps_search_url, search_google_places

load_dotenv()

DB_PATH = os.environ.get("FOOD_DB_PATH", "food_locations.db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db() -> FoodDatabase:
    return FoodDatabase(DB_PATH)


def _format_shop_zh(shop: dict) -> str:
    """Render a shop record in Simplified Chinese."""
    lines: list[str] = []

    lines.append(f"店名      : {shop.get('shop_name') or '未知'}")

    food_types = shop.get("food_types") or "[]"
    if isinstance(food_types, str):
        try:
            food_types = json.loads(food_types)
        except Exception:
            food_types = [food_types]
    if food_types:
        lines.append(f"食物类型  : {' | '.join(food_types)}")

    if shop.get("location"):
        lines.append(f"地区      : {shop['location']}")
    if shop.get("address"):
        lines.append(f"地址      : {shop['address']}")
    if shop.get("rating"):
        stars = round(shop["rating"])
        lines.append(f"评分      : {'★' * stars}{'☆' * (5 - stars)}  {shop['rating']}/5")
    if shop.get("google_maps_url"):
        lines.append(f"Google 地图: {shop['google_maps_url']}")
    if shop.get("description"):
        lines.append(f"推荐理由  : {shop['description']}")

    lines.append(f"记录 ID   : {shop.get('id')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """美食地点助手\n\n储存截图提取结果，按食物类型或地区查询。"""


@cli.command()
@click.argument("extracted_json", required=False)
@click.option("-l", "--location", default=None,
              help="覆盖或补充地区信息（如：芙蓉、Seremban）")
def ingest(extracted_json: str | None, location: str | None):
    """储存 LLM 提取的店铺 JSON 并enriched Google 地图信息。

    EXTRACTED_JSON 为 JSON 字符串，可省略并改为从 stdin 读取。

    必填字段：shop_name
    可选字段：food_types (list)、location、address、description

    示例（nanobot 调用方式）：

    \b
    python food_cli.py ingest '{"shop_name":"老爸肉骨茶","food_types":["肉骨茶"],"location":"芙蓉"}'

    \b
    echo '{"shop_name":"..."}' | python food_cli.py ingest
    """
    if extracted_json is None:
        if not sys.stdin.isatty():
            extracted_json = sys.stdin.read().strip()
        else:
            click.echo("错误：请提供 JSON 字符串参数或通过 stdin 传入。", err=True)
            sys.exit(1)

    try:
        extracted: dict = json.loads(extracted_json)
    except json.JSONDecodeError as exc:
        click.echo(f"错误：JSON 解析失败 — {exc}", err=True)
        sys.exit(1)

    if not extracted.get("shop_name"):
        click.echo("错误：JSON 中缺少必填字段 shop_name。", err=True)
        sys.exit(1)

    # Allow CLI --location to fill in a missing location
    if location and not extracted.get("location"):
        extracted["location"] = location

    shop_name = extracted["shop_name"]
    loc = extracted.get("location") or ""

    # Enrich with Google Places (or generate a fallback search URL)
    google_info = search_google_places(shop_name, loc)
    if not google_info:
        google_info = {"google_maps_url": fallback_maps_search_url(shop_name, loc)}

    db = _db()
    shop_id = db.add_shop(extracted, google_info)
    shop = db.get_shop(shop_id)

    click.echo("\n已成功储存：\n")
    click.echo(_format_shop_zh(shop))


@cli.command()
@click.argument("food_type")
@click.option("-l", "--location", default=None, help="地区过滤（如：芙蓉）")
@click.option("--json-output", is_flag=True, help="输出原始 JSON（供机器人解析）")
def find(food_type: str, location: str | None, json_output: bool):
    """查找提供特定食物类型的店铺。

    FOOD_TYPE 可以是中文或英文（如：肉骨茶、bak kut teh、海南鸡饭）。
    """
    db = _db()
    results = db.search_shops(food_type=food_type, location=location)

    if json_output:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
        return

    loc_label = f"（{location} 地区）" if location else ""
    if not results:
        click.echo(f"抱歉，暂无「{food_type}」{loc_label}的店铺记录。")
        return

    click.echo(f"找到 {len(results)} 家店铺提供「{food_type}」{loc_label}：\n")
    for i, shop in enumerate(results, 1):
        click.echo(f"── 第 {i} 家 ──")
        click.echo(_format_shop_zh(shop))
        click.echo()


@cli.command("list")
@click.option("-l", "--location", default=None, help="按地区过滤")
@click.option("--json-output", is_flag=True, help="输出原始 JSON（供机器人解析）")
def list_shops(location: str | None, json_output: bool):
    """列出数据库中所有店铺记录。"""
    db = _db()
    results = db.list_shops(location=location)

    if json_output:
        click.echo(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if not results:
        click.echo("数据库暂无任何店铺记录。")
        return

    loc_label = f"（{location} 地区）" if location else ""
    click.echo(f"共 {len(results)} 家店铺记录{loc_label}：\n")
    for i, shop in enumerate(results, 1):
        click.echo(f"── {i}. {shop.get('shop_name')} ──")
        click.echo(_format_shop_zh(shop))
        click.echo()


@cli.command()
@click.argument("shop_id", type=int)
def delete(shop_id: int):
    """删除指定 ID 的店铺记录。"""
    db = _db()
    if db.delete_shop(shop_id):
        click.echo(f"已删除 ID 为 {shop_id} 的店铺记录。")
    else:
        click.echo(f"错误：找不到 ID 为 {shop_id} 的记录。", err=True)
        sys.exit(1)


@cli.command()
@click.argument("shop_id", type=int)
def refresh(shop_id: int):
    """重新查询指定店铺的 Google 地图信息。"""
    db = _db()
    shop = db.get_shop(shop_id)
    if not shop:
        click.echo(f"错误：找不到 ID 为 {shop_id} 的记录。", err=True)
        sys.exit(1)

    shop_name = shop.get("shop_name", "")
    location  = shop.get("location") or ""

    click.echo(f"正在为「{shop_name}」查询 Google 地图信息 …")
    google_info = search_google_places(shop_name, location)

    if not google_info:
        click.echo("未找到 Google 地图信息（请确认 GOOGLE_PLACES_API_KEY 已配置）。")
        return

    db.update_google_info(shop_id, google_info)
    updated = db.get_shop(shop_id)
    click.echo("\n已更新：\n")
    click.echo(_format_shop_zh(updated))


if __name__ == "__main__":
    cli()
