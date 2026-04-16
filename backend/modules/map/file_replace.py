import logging
from pathlib import Path
from typing import Dict, List


GOOGLE_KEY_PLACEHOLDER = "your_api_key"
BAIDU_KEY_PLACEHOLDER = "your_api_key"
GOOGLE_MAP_ID_PLACEHOLDER = "your_map_id"
BAIDU_MAP_ID_SENTINEL = "do_not_need_map_id"

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _should_skip(old_val: str, new_val: str) -> bool:
    """Return True when there is nothing useful to replace."""
    if not old_val or not new_val:
        return True
    return old_val == new_val


def _do_replace(
    rel_path: str,
    pairs: List[tuple],
    logger: logging.Logger,
) -> None:
    """Read *rel_path* (relative to repo root), apply (old, new) string
    replacements in order, and write back only if something changed."""
    abs_path = (_REPO_ROOT / rel_path).resolve()
    if not abs_path.exists():
        logger.warning("File not found for map-config replace: %s", abs_path)
        return

    try:
        content = abs_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error("Cannot read %s: %s", abs_path, exc)
        return

    original = content
    for old_val, new_val in pairs:
        if _should_skip(old_val, new_val):
            logger.debug("  skip pair old=%r new=%r (no-op)", old_val, new_val)
            continue
        if old_val in content:
            content = content.replace(old_val, new_val)
            logger.info("  replaced %r -> %r in %s", old_val, new_val, rel_path)
        else:
            logger.debug("  old value %r not found in %s", old_val, rel_path)

    if content != original:
        try:
            abs_path.write_text(content, encoding="utf-8")
            logger.info("Written updated file: %s", abs_path)
        except Exception as exc:
            logger.error("Cannot write %s: %s", abs_path, exc)
    else:
        logger.info("No changes needed for %s", rel_path)


def replace_map_config_in_files(
    old_api_keys: List[str],
    old_map_ids: List[str],
    new_api_keys: List[str],
    new_map_ids: List[str],
    logger: logging.Logger,
) -> None:
    """Replace map configuration in local HTML/JS files.

    Updates:
    - Google key:  scripts/googlemap3d.html  (key=…)
    - Google mapId: scripts/js/google/map_common.js  (mapId: "…")
    - Baidu key:  scripts/map.html  (ak=…)

    Attempts replacement using both DB old values AND stable placeholders.
    Uses plain string replacement — no regex — for reliability.
    """
    google_key = new_api_keys[0] if len(new_api_keys) > 0 else ""
    baidu_key = new_api_keys[1] if len(new_api_keys) > 1 else ""
    google_map_id = new_map_ids[0] if len(new_map_ids) > 0 else ""

    old_google_key = old_api_keys[0].strip() if len(old_api_keys) > 0 else ""
    old_baidu_key = old_api_keys[1].strip() if len(old_api_keys) > 1 else ""
    old_google_map_id = old_map_ids[0].strip() if len(old_map_ids) > 0 else ""

    logger.info(
        "replace_map_config_in_files: google_key=%r, google_map_id=%r, baidu_key=%r, "
        "old_google_key=%r, old_google_map_id=%r, old_baidu_key=%r",
        google_key, google_map_id, baidu_key,
        old_google_key, old_google_map_id, old_baidu_key,
    )

    # --- Google API key in googlemap3d.html ---
    # The file contains:  key=<value>&callback=  or  key=<value>"
    google_key_pairs: List[tuple] = []
    if old_google_key:
        google_key_pairs.append(("key=" + old_google_key, "key=" + google_key))
    google_key_pairs.append(("key=" + GOOGLE_KEY_PLACEHOLDER, "key=" + google_key))

    _do_replace("scripts/googlemap3d.html", google_key_pairs, logger)

    # --- Google mapId in map_common.js ---
    # The file contains:  mapId: "…"
    map_id_pairs: List[tuple] = []
    if old_google_map_id:
        map_id_pairs.append(('"' + old_google_map_id + '"', '"' + google_map_id + '"'))
    map_id_pairs.append(('"' + GOOGLE_MAP_ID_PLACEHOLDER + '"', '"' + google_map_id + '"'))

    _do_replace("scripts/js/google/map_common.js", map_id_pairs, logger)

    # --- Baidu API key in map.html ---
    # The file contains:  ak=<value>"  or  ak=<value></script>
    baidu_key_pairs: List[tuple] = []
    if old_baidu_key:
        baidu_key_pairs.append(("ak=" + old_baidu_key, "ak=" + baidu_key))
    baidu_key_pairs.append(("ak=" + BAIDU_KEY_PLACEHOLDER, "ak=" + baidu_key))

    _do_replace("scripts/map.html", baidu_key_pairs, logger)
