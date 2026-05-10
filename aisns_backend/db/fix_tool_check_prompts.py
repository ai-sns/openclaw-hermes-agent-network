"""One-off DB updater: rewrite the two __tool_check_*__ prompts so they no
longer contain the misleading "get system information" instruction that biased
the LLM into calling get_system_info regardless of context.

Run once after pulling the matching seed_data.py changes:

    python -m db.fix_tool_check_prompts

(Idempotent — safe to run multiple times.)
"""

from db.DBFactory import Session
from db.models.agent import Prompt


NEW_BEFORE_ACTIVITY = (
    'You are an AI agent playing a virtual social life game on Google Maps.\n'
    'You are about to decide your next action in the game.\n'
    'Before proceeding, review the current situation below and determine if any of your available tools could '
    'help you make a better decision.\n'
    '\n'
    'If you find a useful tool, call it now and return the result.\n'
    'If no tool is needed, simply reply with the single phrase: NO_TOOL_NEEDED\n'
    '\n'
    'Keep your response concise. Do NOT plan or choose the next game action — just focus on whether a tool '
    'call would provide useful information right now.'
)

NEW_BEFORE_REVIEW = (
    'You are an AI agent playing a virtual social life game on Google Maps.\n'
    'You are currently in a conversation with another player.\n'
    'Before reviewing this conversation, check if any of your available tools could provide useful context '
    '(e.g., price lookup, information search, knowledge retrieval).\n'
    '\n'
    'If the peer explicitly asks you to use an A2A / XMPP ad-hoc command (e.g. exchange business card, '
    'invoke a peer skill), you MUST call the a2a_xmpp_adhoc tool with the matching command_node listed '
    'in the "Discovered commands on this peer" section, instead of replying with text.\n'
    'If you find a useful tool, call it now and return the result.\n'
    'If no tool is needed, simply reply with the single phrase: NO_TOOL_NEEDED\n'
    '\n'
    'Keep your response concise. Do NOT evaluate or continue the conversation — just focus on whether a tool '
    'call would be helpful.'
)


UPDATES = {
    '__tool_check_before_activity__': NEW_BEFORE_ACTIVITY,
    '__tool_check_before_review__': NEW_BEFORE_REVIEW,
}


def main() -> None:
    session = Session()
    try:
        changed = 0
        for title, new_content in UPDATES.items():
            row = session.query(Prompt).filter_by(title=title).first()
            if row is None:
                print(f"[skip] prompt not found: {title}")
                continue
            if (row.content or '') == new_content:
                print(f"[ok ] already up-to-date: {title}")
                continue
            row.content = new_content
            changed += 1
            print(f"[upd] {title}")
        if changed:
            session.commit()
        print(f"Done. {changed} row(s) updated.")
    finally:
        session.close()


if __name__ == '__main__':
    main()
