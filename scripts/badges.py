# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "aiohttp>=3.9.0",
# ]
# ///

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import quote_plus

import aiohttp

OUT_JSON = "./badges.json"
JSON_URL = "https://raw.githubusercontent.com/ballistics-lab/.github/refs/heads/main/badges.json"
PUB_API_URL = "https://pub.dev/api/packages/{pkg}/score"
SHIELDS_IO_BADGE = (
    "https://img.shields.io/badge/dynamic/json"
    "?label={label}&query={query}&url=" + quote_plus(JSON_URL)
)
PUB_PACKAGES = [
    "dart_bclibc",
    "dart_bclibc_flutter",
    "a7p",
    "flutpak",
    "ob_dump_reader",
    "ob_dump_reader_flutter"
]

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def build_badge_url(label: str, query: str) -> str:
    return SHIELDS_IO_BADGE.format(label=label, query=quote_plus(query))


def parse_pub_score_tags(tags: List[str]) -> Dict[str, str]:
    result = {"platform": "unknown", "sdk": "unknown"}

    platform_values = []
    sdk_values = []
    
    for tag in tags:
        if tag.startswith("platform:"):
            platform_values.append(tag.split(":", 1)[1])
        elif tag.startswith("sdk:"):
            sdk_values.append(tag.split(":", 1)[1])

    if platform_values:
        result["platform"] = " | ".join(platform_values)
    if sdk_values:
        result["sdk"] = " | ".join(sdk_values)
    
    return result


async def fetch_pub_package_data(
    session: aiohttp.ClientSession, pkg: str
) -> Optional[Dict[str, Any]]:
    url = PUB_API_URL.format(pkg=pkg)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            resp.raise_for_status()
            data = await resp.json()
            tags = data.get("tags", [])
            if not tags:
                logger.warning(f"Пакет {pkg} не має тегів")
                return None

            parsed = parse_pub_score_tags(tags)
            return {
                pkg: {
                    "platform": {
                        "v": parsed["platform"],
                        "q": build_badge_url(
                            label="platform", query=f"$.pub.{pkg}.platform.v"
                        ),
                    },
                    "sdk": {
                        "v": parsed["sdk"],
                        "q": build_badge_url(label="sdk", query=f"$.pub.{pkg}.sdk.v"),
                    },
                }
            }
    except aiohttp.ClientError as e:
        logger.error(f"HTTP error for {pkg}: {e}")
    except asyncio.TimeoutError:
        logger.error(f"TImeout for {pkg}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {pkg}: {e}")
    except Exception as e:
        logger.exception(f"Unknown error for {pkg}: {e}")
    return None


async def collect_pub_data(packages: List[str]) -> Dict[str, Any]:
    logging.info("Collecting data from pub.dev")
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_pub_package_data(session, pkg) for pkg in packages]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    collected = {}
    for res in results:
        if isinstance(res, dict):
            collected.update(res)
        elif isinstance(res, Exception):
            logger.error(f"Exception on collecting: {res}")
    return collected


async def main() -> None:
    logger.info("Collecting data from indexes")

    badges = {"pub": await collect_pub_data(PUB_PACKAGES)}

    try:
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(badges, f, indent=2, ensure_ascii=False)
        logger.info(f"Data sucsessfully stored to {OUT_JSON}")
    except OSError as e:
        logger.error(f"File write error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
