# User-Defined A2A Ad-hoc Commands

Place custom ad-hoc command plugins in this directory. Each `.py` file should contain one or more classes that extend `AdhocCommand`.

## Quick Start

1. Create a new `.py` file in this directory (e.g., `weather.py`).
2. Define a class extending `AdhocCommand` from the base module.
3. Restart the application — the command will be auto-discovered and registered.

## Example

```python
from runtime.apps.sns.a2a_commands.base import AdhocCommand, CommandContext


class WeatherCommand(AdhocCommand):
    node = "urn:xmpp:a2a:cmd:weather"
    name = "Weather Lookup"
    description = "Look up weather for a city"
    form_fields = [
        {"var": "city", "type": "text-single", "label": "City"},
    ]

    async def handle_execute(self, iq, session, ctx):
        """Stage 1: Present form."""
        # Default implementation from base class builds form from self.form_fields
        return await super().handle_execute(iq, session, ctx)

    async def handle_submit(self, payload, session, ctx):
        """Stage 2: Process form and return result."""
        values = {}
        if hasattr(payload, 'get_fields'):
            for var_name, fld in payload.get_fields().items():
                val = fld.get('value', '')
                if isinstance(val, list):
                    val = '\n'.join(str(v) for v in val)
                values[var_name] = val

        city = values.get('city', 'Unknown')
        result_form = ctx.make_result_form(
            {"city": city, "temperature": "20°C", "condition": "Sunny"},
            title="Weather Result"
        )
        session['payload'] = result_form
        session['next'] = None
        session['has_next'] = False
        return session
```

## Notes

- **Plugin files** cannot be deleted or edited from the frontend UI, only enabled/disabled.
- The `ctx` (CommandContext) object provides: `xmpp_client`, `a2a_manager`, `logger`, and helper methods like `make_form()` and `make_result_form()`.
- File names starting with `_` are ignored by the scanner.
- If your command `node` conflicts with a built-in command, the built-in takes priority.
