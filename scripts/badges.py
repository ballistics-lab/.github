# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests>=2.34.2",
# ]
# ///

import requests
import json
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


OUT_JSON = "./badges.json"
JSON_URL = "https://raw.githubusercontent.com/ballistics-lab/.github/refs/heads/main/badges.json"
SHIELDS_IO_DYNAMIC_JSON = "https://img.shields.io/badge/dynamic/json"

PUB_API_EP = "https://pub.dev/api/packages/{pkg}/score"
PUB_BADGE = (
    SHIELDS_IO_DYNAMIC_JSON + "?label={label}&query={query}&url=" + quote_plus(JSON_URL)
)
PUB_PKGS = ["dart_bclibc", "a7p", "ob_dump_reader", "ob_dump_reader_flutter"]


def pub():
    def join_(key: str, tags: list[str]) -> str:
        values = list(
            map(
                lambda t: t.split(":", 1)[1],
                filter(lambda t: t.startswith(key + ":"), tags),
            )
        )
        return " | ".join(values) if values else "unknown"

    def process_package(pkg: str):
        try:
            resp = requests.get(PUB_API_EP.format(pkg=pkg), timeout=2)
            resp.raise_for_status()
            tags = resp.json().get("tags", [])
            if tags:
                pfm = join_("platform", tags)
                sdk = join_("sdk", tags)
                return {
                    pkg: {
                        "platform": {
                            "v": pfm,
                            "q": PUB_BADGE.format(
                                label="platform",
                                query=quote_plus(f"$.pub.{pkg}.platform.v"),
                            ),
                        },
                        "sdk": {
                            "v": sdk,
                            "q": PUB_BADGE.format(
                                label="sdk", query=quote_plus(f"$.pub.{pkg}.sdk.v")
                            ),
                        },
                    }
                }
        except Exception as e:
            logging.error(e)
        return None

    collected = {}
    for result in filter(None, map(process_package, PUB_PKGS)):
        collected.update(result)
    return collected


def main():
    badges = {"pub": pub()}
    with open(OUT_JSON, "w") as fp:
        json.dump(badges, fp, indent=2)


if __name__ == "__main__":
    main()
