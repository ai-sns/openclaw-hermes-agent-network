import logging
from pathlib import Path
import shutil
from typing import Dict, List
from runtime.shared import debug_info


GOOGLE_KEY_PLACEHOLDER = "your_api_key"
BAIDU_KEY_PLACEHOLDER = "your_api_key"
GOOGLE_MAP_ID_PLACEHOLDER = "your_map_id"
BAIDU_MAP_ID_SENTINEL = "do_not_need_map_id"

_REPO_ROOT = Path(__file__).resolve().parents[3]

# Map-config files that are git-ignored at runtime and shipped only as
# ``*.example`` templates. They must exist on disk for the map iframe to load
# (served via the ``/static`` mount).
MAP_CONFIG_FILES = (
    "static/googlemap3d.html",
    "static/map.html",
    "static/js/google/map_common.js",
)


def _should_skip(old_val: str, new_val: str) -> bool:
    """Return True when there is nothing useful to replace."""
    if not old_val or not new_val:
        return True
    return old_val == new_val


def _create_from_template_if_missing(rel_path: str, logger: logging.Logger) -> bool:
    """Ensure *rel_path* exists, creating it from its ``.example`` template
    when missing. Returns True if the file exists (or was created)."""
    abs_path = (_REPO_ROOT / rel_path).resolve()
    if abs_path.exists():
        return True

    template_path = (_REPO_ROOT / (rel_path + ".example")).resolve()
    if not template_path.exists():
        logger.warning(
            "Map-config file missing and no template exists: %s (template: %s)",
            abs_path,
            template_path,
        )
        return False

    try:
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template_path, abs_path)
        logger.info(
            "Created missing map-config file from template: %s -> %s",
            template_path,
            abs_path,
        )
        return True
    except Exception as exc:
        logger.error(
            "Failed to create missing map-config file from template: %s -> %s (%s)",
            template_path,
            abs_path,
            exc,
        )
        return False


def ensure_map_files_from_templates(logger: logging.Logger) -> None:
    """Create any missing map-config files from their ``.example`` templates.

    Safe to call at startup. This guarantees the map iframe can always load
    ``/static/googlemap3d.html`` and ``/static/map.html`` even before the user
    has saved any map configuration (the real files are git-ignored)."""
    for rel_path in MAP_CONFIG_FILES:
        _create_from_template_if_missing(rel_path, logger)


def _do_replace(
    rel_path: str,
    pairs: List[tuple],
    logger: logging.Logger,
) -> None:
    """Read *rel_path* (relative to repo root), apply (old, new) string
    replacements in order, and write back only if something changed."""
    if not _create_from_template_if_missing(rel_path, logger):
        return

    abs_path = (_REPO_ROOT / rel_path).resolve()
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
    - Google key:  static/googlemap3d.html  (key=…)
    - Google mapId: static/js/google/map_common.js  (mapId: "…")
    - Baidu key:  static/map.html  (ak=…)

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

    _do_replace("static/googlemap3d.html", google_key_pairs, logger)

    # --- Google mapId in map_common.js ---
    # The file contains:  mapId: "…"
    map_id_pairs: List[tuple] = []
    if old_google_map_id:
        map_id_pairs.append(('"' + old_google_map_id + '"', '"' + google_map_id + '"'))
    map_id_pairs.append(('"' + GOOGLE_MAP_ID_PLACEHOLDER + '"', '"' + google_map_id + '"'))

    _do_replace("static/js/google/map_common.js", map_id_pairs, logger)

    # --- Baidu API key in map.html ---
    # The file contains:  ak=<value>"  or  ak=<value></script>
    baidu_key_pairs: List[tuple] = []
    if old_baidu_key:
        baidu_key_pairs.append(("ak=" + old_baidu_key, "ak=" + baidu_key))
    baidu_key_pairs.append(("ak=" + BAIDU_KEY_PLACEHOLDER, "ak=" + baidu_key))

    _do_replace("static/map.html", baidu_key_pairs, logger)
