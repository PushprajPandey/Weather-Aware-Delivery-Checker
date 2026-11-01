import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

INPUT_FILE = Path("orders.json")
OUTPUT_FILE = Path("orders_updated.json")
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
DELAY_CONDITIONS = {"Rain", "Snow", "Extreme", "Thunderstorm", "Tornado", "Squall"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("weather_run.log", encoding="utf-8")],
)
log = logging.getLogger("weather")

# Suppress httpx verbose logging
logging.getLogger("httpx").setLevel(logging.WARNING)

MOCK_WEATHER = {
    "new york": {"main": "Rain", "description": "heavy intensity rain", "temp": 11.2},
    "mumbai": {"main": "Clouds", "description": "scattered clouds", "temp": 31.0},
    "london": {"main": "Snow", "description": "light snow", "temp": -1.5},
}


class CityNotFound(Exception):
    pass


async def fetch_weather(client: httpx.AsyncClient, city: str, api_key: str | None, mock: bool) -> dict:
    if mock:
        await asyncio.sleep(0.2)
        data = MOCK_WEATHER.get(city.lower())
        if not data:
            raise CityNotFound(f"City '{city}' not found (mock)")
        return data

    try:
        resp = await client.get(
            WEATHER_URL, params={"q": city, "appid": api_key, "units": "metric"}, timeout=10
        )
    except httpx.RequestError:
        raise RuntimeError("Network error occurred")

    if resp.status_code == 404:
        raise CityNotFound(f"City '{city}' not found")
    if resp.status_code == 401:
        raise RuntimeError("Invalid or not-yet-activated API key")
    if resp.status_code != 200:
        raise RuntimeError(f"Weather API returned HTTP {resp.status_code}")

    body = resp.json()
    w = body["weather"][0]
    return {"main": w["main"], "description": w["description"], "temp": body["main"]["temp"]}


async def generate_apology(client: httpx.AsyncClient, order: dict, weather: dict) -> str:
    first_name = order["customer"].split()[0]
    fallback = (
        f"Hi {first_name}, your order to {order['city']} is delayed due to "
        f"{weather['description']}. We appreciate your patience!"
    )

    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return fallback

    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    prompt = (
        f"Write a brief apology to {first_name} whose delivery to {order['city']} is delayed "
        f"by {weather['description']}. Keep it warm, 1-2 sentences, mention the weather, "
        f"thank them for patience."
    )
    
    try:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 120},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return fallback


async def process_order(client: httpx.AsyncClient, order: dict, api_key: str | None, mock: bool) -> dict:
    try:
        weather = await fetch_weather(client, order["city"], api_key, mock)
    except CityNotFound as exc:
        log.error("Order %s: %s", order["order_id"], exc)
        order["weather_check"] = "failed: city not found"
        return order
    except Exception as exc:
        log.error("Order %s: weather lookup failed: %s", order["order_id"], exc)
        order["weather_check"] = f"failed: {exc}"
        return order

    order["weather"] = f"{weather['main']} ({weather['description']}, {weather['temp']}°C)"
    order["weather_check"] = "ok"

    if weather["main"] in DELAY_CONDITIONS:
        order["status"] = "Delayed"
        order["apology_message"] = await generate_apology(client, order, weather)
        log.info("Order %s -> DELAYED (%s)", order["order_id"], weather["main"])
    else:
        log.info("Order %s -> on track (%s)", order["order_id"], weather["main"])
    
    return order


async def main(mock: bool) -> None:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not mock and not api_key:
        raise SystemExit("OPENWEATHER_API_KEY missing. Add it to .env or run with --mock.")

    orders = json.loads(INPUT_FILE.read_text(encoding="utf-8"))

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *(process_order(client, o, api_key, mock) for o in orders),
            return_exceptions=True,
        )

    updated = []
    for order, result in zip(orders, results):
        if isinstance(result, Exception):
            log.error("Order %s: unexpected error: %s", order["order_id"], type(result).__name__)
            order["weather_check"] = "failed: unexpected error"
            updated.append(order)
        else:
            updated.append(result)

    OUTPUT_FILE.write_text(json.dumps(updated, indent=2, ensure_ascii=False), encoding="utf-8")
    delayed = sum(1 for o in updated if o["status"] == "Delayed")
    log.info("Done. %d/%d orders delayed. Saved to %s", delayed, len(updated), OUTPUT_FILE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Use fake weather data (offline demo)")
    args = parser.parse_args()
    asyncio.run(main(args.mock))
