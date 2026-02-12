import json
import sys
from datetime import date as _date


def _normalize_ampm(value: str) -> str:
    v = (value or "").strip().lower()
    if v in ("am", "a", "morning", "上午"):
        return "am"
    if v in ("pm", "p", "afternoon", "下午"):
        return "pm"
    return v


def main(params: dict) -> dict:
    params = params or {}

    date_str = str(params.get("date") or "").strip()
    ampm_raw = str(params.get("ampm") or "").strip()

    if not date_str:
        date_str = _date.today().isoformat()

    # very light validation for YYYY-MM-DD
    if len(date_str) != 10 or date_str[4] != "-" or date_str[7] != "-":
        return {
            "success": False,
            "error": "Invalid date format. Expected YYYY-MM-DD",
            "received": {"date": date_str, "ampm": ampm_raw},
        }

    ampm = _normalize_ampm(ampm_raw) or "am"
    if ampm not in ("am", "pm"):
        return {
            "success": False,
            "error": "Invalid ampm value. Use am/pm (or morning/afternoon, 上午/下午)",
            "received": {"date": date_str, "ampm": ampm_raw},
        }

    # Demo output (you can replace with real API call later)
    return {
        "success": True,
        "data": {
            "city": "Shanghai",
            "date": date_str,
            "ampm": ampm,
            "weather": "sunny",
            "temperature_c": 22 if ampm == "am" else 26,
        },
    }


if __name__ == "__main__":
    raw = sys.stdin.read() or "{}"
    try:
        params = json.loads(raw)
    except Exception:
        params = {}

    result = main(params if isinstance(params, dict) else {})
    print(json.dumps(result, ensure_ascii=False))
