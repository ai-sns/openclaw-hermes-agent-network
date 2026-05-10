"""
Base class and context for XMPP A2A ad-hoc command plugins.

All ad-hoc commands (builtin, plugin, or config-type) inherit from AdhocCommand.
CommandContext provides access to shared services without tight coupling.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CommandContext:
    """Injected context available to all command handlers."""
    xmpp_client: Any = None
    a2a_manager: Any = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("a2a_commands"))

    def make_form(self, ftype: str = 'form', title: str = ''):
        """Create an XEP-0004 data form via the XMPP client."""
        return self.xmpp_client['xep_0004'].make_form(ftype=ftype, title=title)

    def make_result_form(self, data: Dict[str, Any], title: str = 'Result') -> Any:
        """Create a result-type form populated with key-value fields."""
        form = self.make_form(ftype='result', title=title)
        for key, value in data.items():
            form.addField(
                var=key,
                ftype='text-single',
                label=key.replace('_', ' ').title(),
                value=str(value) if value is not None else '',
            )
        return form


class AdhocCommand:
    """
    Abstract base class for all ad-hoc command plugins.

    Subclasses must define:
        - node: str       — unique command node URI
        - name: str       — display name shown to peers

    And implement:
        - handle_execute  — stage 1: present form to caller
        - handle_submit   — stage 2: process submission, return result
    """

    node: str = ""
    name: str = ""
    description: str = ""
    # NOTE: declared as None to avoid the classic mutable-default pitfall.
    # Subclasses override with a fresh list literal; readers use _get_fields().
    form_fields: Optional[List[Dict[str, Any]]] = None

    # Source tag for UI display (set by registry)
    _source: str = "builtin"

    def _get_fields(self) -> List[Dict[str, Any]]:
        """Return form_fields safely, treating None as empty list."""
        return list(self.form_fields) if self.form_fields else []

    def get_metadata(self) -> Dict[str, Any]:
        """Return command metadata for API/frontend consumption."""
        return {
            "node": self.node,
            "name": self.name,
            "description": self.description,
            "form_fields": self._get_fields(),
            "source": self._source,
        }

    async def handle_execute(self, iq, session, ctx: CommandContext) -> dict:
        """
        Stage 1 (execute): Build and return a data form for the caller.

        Default implementation builds a form from self.form_fields.
        Override for custom behavior.
        """
        form = ctx.make_form(ftype='form', title=self.name)
        for field_def in self._get_fields():
            form.addField(
                var=field_def.get('var', ''),
                ftype=field_def.get('type', 'text-single'),
                label=field_def.get('label', ''),
                value=field_def.get('default', ''),
            )
        session['payload'] = form
        session['next'] = None  # Will be wired by registry
        session['has_next'] = True
        session['allow_complete'] = True
        return session

    async def handle_submit(self, payload, session, ctx: CommandContext) -> dict:
        """
        Stage 2 (complete): Process submitted form data and return result.

        Default implementation returns form values as-is in a result form.
        Override for custom behavior.
        """
        # Extract submitted values
        values = {}
        if hasattr(payload, 'get_fields'):
            fields = payload.get_fields()
            for var_name, fld in fields.items():
                val = fld.get('value', '')
                if isinstance(val, list):
                    val = '\n'.join(str(v) for v in val)
                values[var_name] = val
        elif hasattr(payload, 'get_values'):
            values = dict(payload.get_values())

        result_form = ctx.make_result_form(values, title=f'{self.name} Result')
        session['payload'] = result_form
        session['next'] = None
        session['has_next'] = False
        return session


class TemplateCommand(AdhocCommand):
    """
    A config-type command that uses a response template with {{var}} substitution.

    Created dynamically from JSON config stored in aisns_cfg.memo.
    """

    _source = "config"

    def __init__(self, node: str, name: str, form_fields: List[Dict[str, Any]],
                 response_template: Optional[Dict[str, Any]] = None,
                 description: str = ""):
        self.node = node
        self.name = name
        self.description = description
        self.form_fields = form_fields
        self._response_template = response_template or {}

    async def handle_submit(self, payload, session, ctx: CommandContext) -> dict:
        """Process form and apply template substitution."""
        # Extract submitted values
        values = {}
        if hasattr(payload, 'get_fields'):
            fields = payload.get_fields()
            for var_name, fld in fields.items():
                val = fld.get('value', '')
                if isinstance(val, list):
                    val = '\n'.join(str(v) for v in val)
                values[var_name] = val
        elif hasattr(payload, 'get_values'):
            values = dict(payload.get_values())

        # Apply template substitution
        result_data = {}
        for key, tmpl in self._response_template.items():
            if isinstance(tmpl, str):
                rendered = tmpl
                for var_name, var_val in values.items():
                    rendered = rendered.replace('{{' + var_name + '}}', str(var_val))
                result_data[key] = rendered
            else:
                result_data[key] = tmpl

        # If no template defined, echo submitted values
        if not result_data:
            result_data = values

        result_form = ctx.make_result_form(result_data, title=f'{self.name} Result')
        session['payload'] = result_form
        session['next'] = None
        session['has_next'] = False
        return session
