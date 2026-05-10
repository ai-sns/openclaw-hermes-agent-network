"""SNS Module - API Router - Async version."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from db.database import get_db
from runtime.apps.sns.service_async import SNSService
from runtime.apps.sns.schemas import (
    UserStatsResponse,
    ContactResponse,
    ChatMessageResponse,
    SendMessageRequest,
    SendMessageResponse,
    AIChatRequest,
    AIChatResponse,
    AIChatConfigResponse,
    AIChatConfigUpdateRequest,
    Avatar3DItem,
    ProfessionItem,
    SocialRoleItem,
    SocialRoleUpdateRequest,
    HumanControlStateRequest,
    HumanMessageRequest,
    AgentInstructionRequest,
    EndActiveConversationRequest,
    PromptByTitleUpdateRequest,
    MarkContactReadRequest,
    A2AXmppCallRequest
)

from runtime.apps.sns.memory.router import router as memory_router

router = APIRouter()

router.include_router(memory_router, tags=["Memory"])


@router.get("/user-stats", response_model=UserStatsResponse)
async def get_user_stats(db: AsyncSession = Depends(get_db)):
    """Get user statistics"""
    service = SNSService(db)
    return await service.get_user_stats()


@router.get("/contacts", response_model=List[ContactResponse])
async def get_contacts(db: AsyncSession = Depends(get_db)):
    """Get contact list from ai_friend table"""
    service = SNSService(db)
    return await service.get_contacts()


@router.get("/chat-history/{account}", response_model=List[ChatMessageResponse])
async def get_chat_history(account: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get chat history with a specific contact"""
    service = SNSService(db)
    return await service.get_chat_history(account, limit)


@router.post("/send-message", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest, db: AsyncSession = Depends(get_db)):
    """Send a message via XMPP"""
    service = SNSService(db)
    return await service.send_message(request.to_account, request.content)


@router.post("/mark-contact-read")
async def mark_contact_read(
    request: MarkContactReadRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a contact as read (clear red dot) and persist to DB."""
    service = SNSService(db)
    return await service.mark_contact_read(request.account)


@router.post("/send-file")
async def send_file(
    to_account: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Send a file via XMPP"""
    service = SNSService(db)
    return await service.send_file(to_account, file)


@router.post("/ai-chat", response_model=AIChatResponse)
async def ai_chat(request: AIChatRequest):
    """Chat with AI agent"""
    from runtime.apps.sns.ai_service import SNSAIService

    try:
        reply = await SNSAIService.chat_with_agent(
            agent_identifier=request.agent_identifier,
            message=request.message,
            mode=request.mode
        )

        if reply.startswith("Error:"):
            return AIChatResponse(success=False, reply="", error=reply)

        return AIChatResponse(success=True, reply=reply)
    except Exception as e:
        return AIChatResponse(success=False, reply="", error=str(e))


@router.post("/start-engine")
async def start_social_engine(db: AsyncSession = Depends(get_db)):
    """Start the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.start_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to start social engine: {str(e)}"
        }



@router.post("/pause-engine")
async def pause_social_engine(db: AsyncSession = Depends(get_db)):
    """Pause the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.pause_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to pause social engine: {str(e)}"
        }


@router.post("/resume-engine")
async def resume_social_engine(db: AsyncSession = Depends(get_db)):
    """Resume the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.resume_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to resume social engine: {str(e)}"
        }


@router.post("/stop-engine")
async def stop_social_engine(db: AsyncSession = Depends(get_db)):
    """Stop the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.stop_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to stop social engine: {str(e)}"
        }


@router.post("/restart-engine")
async def restart_social_engine(db: AsyncSession = Depends(get_db)):
    """Restart the AI social engine"""
    try:
        service = SNSService(db)
        result = await service.restart_social_engine()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to restart social engine: {str(e)}"
        }


@router.get("/engine-status")
async def get_social_engine_status(db: AsyncSession = Depends(get_db)):
    """Get the current AI social engine status"""
    try:
        service = SNSService(db)
        result = await service.get_social_engine_status()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get social engine status: {str(e)}",
            "running": False,
        }


@router.get("/engine-inspect/default")
async def engine_inspect_default(db: AsyncSession = Depends(get_db)):
    """Get a default snapshot of key engine variables for debugging."""
    try:
        service = SNSService(db)
        return await service.engine_inspect_default()
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to inspect engine: {str(e)}",
        }


@router.post("/engine-inspect/var")
async def engine_inspect_var(request: dict, db: AsyncSession = Depends(get_db)):
    """Read an engine variable by path (e.g. taskmng.current_objective)."""
    try:
        name = request.get("name") if isinstance(request, dict) else None
        service = SNSService(db)
        return await service.engine_inspect_var(str(name or ""))
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to inspect variable: {str(e)}",
        }


@router.post("/engine-inspect/call")
async def engine_inspect_call(request: dict, db: AsyncSession = Depends(get_db)):
    """Call an engine function by path with args/kwargs."""
    try:
        payload = request if isinstance(request, dict) else {}
        name = payload.get("name")
        args = payload.get("args")
        kwargs = payload.get("kwargs")
        service = SNSService(db)
        return await service.engine_inspect_call(str(name or ""), args=args, kwargs=kwargs)
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to call function: {str(e)}",
        }


@router.get("/config", response_model=AIChatConfigResponse)
async def get_ai_chat_config(user_id: str = None, db: AsyncSession = Depends(get_db)):
    """Get AI chat configuration, including a2a_config extracted from memo JSON."""
    service = SNSService(db)
    config = await service.get_ai_chat_config(user_id)

    # Extract a2a_config from memo JSON for frontend consumption
    a2a_config = None
    memo_raw = getattr(config, 'memo', None) or ''
    if isinstance(memo_raw, str) and memo_raw.strip():
        try:
            import json as _json
            memo_obj = _json.loads(memo_raw)
            if isinstance(memo_obj, dict):
                a2a_config = memo_obj.get('a2a_config')
        except Exception:
            pass

    resp = AIChatConfigResponse.model_validate(config)
    resp.a2a_config = a2a_config
    return resp


@router.put("/config")
async def update_ai_chat_config(
    request: AIChatConfigUpdateRequest,
    user_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Update AI chat configuration"""
    service = SNSService(db)
    return await service.update_ai_chat_config(user_id, request.dict(exclude_unset=True))


@router.get("/a2a/commands")
async def list_a2a_commands(db: AsyncSession = Depends(get_db)):
    """
    Return the merged list of all A2A ad-hoc commands available on this node.

    The list contains:
      - All built-in commands discovered in a2a_commands/ package
      - All user plugins discovered in aisns_backend/scripts/a2a_commands/
      - All config-type commands stored in aisns_cfg.memo.a2a_config.adhoc_commands

    Each entry has an `enabled` flag computed from the DB config (default True
    when no explicit state is stored). The frontend uses this list to render
    the unified command UI in the User Configuration dialog.
    """
    import json as _json
    try:
        from runtime.apps.sns.a2a_commands import discover_commands, build_config_commands

        # Discover builtin + plugin commands
        try:
            discovered = discover_commands()
        except Exception as e:
            return {"success": False, "message": f"Discovery failed: {e}", "commands": []}

        # Load enabled state + config commands from DB
        enabled_lookup = {}
        config_commands_def = []
        try:
            service = SNSService(db)
            cfg = await service.get_ai_chat_config(None)
            memo_raw = getattr(cfg, 'memo', None) or ''
            if isinstance(memo_raw, str) and memo_raw.strip():
                memo_obj = _json.loads(memo_raw)
                if isinstance(memo_obj, dict):
                    a2a_cfg = memo_obj.get('a2a_config') or {}
                    config_commands_def = a2a_cfg.get('adhoc_commands') or []
                    for entry in config_commands_def:
                        if isinstance(entry, dict) and entry.get('node'):
                            enabled_lookup[entry['node']] = entry.get('enabled', True)
        except HTTPException:
            pass
        except Exception:
            pass

        # Build config commands and append to the discovered list
        try:
            cfg_cmds = build_config_commands(config_commands_def)
        except Exception:
            cfg_cmds = []

        merged_nodes = set()
        commands_meta = []
        for cmd in list(discovered) + list(cfg_cmds):
            if not cmd.node or cmd.node in merged_nodes:
                continue
            merged_nodes.add(cmd.node)
            meta = cmd.get_metadata()
            meta['enabled'] = enabled_lookup.get(cmd.node, True)
            # For config commands, include the response_template so UI can edit it
            if meta.get('source') == 'config':
                # Find the matching definition for response_template
                for entry in config_commands_def:
                    if isinstance(entry, dict) and entry.get('node') == cmd.node:
                        meta['response_template'] = entry.get('response_template') or {}
                        break
            commands_meta.append(meta)

        return {"success": True, "commands": commands_meta}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}", "commands": []}


@router.post("/config/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user_id: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload avatar image"""
    service = SNSService(db)
    return await service.upload_avatar(user_id, file)


@router.post("/avatar-dialog/upload-avatar")
async def upload_avatar_dialog(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload avatar for SNS avatar dialog and generate composed avatar map image."""
    service = SNSService(db)
    return await service.upload_avatar_dialog(file)


@router.post("/avatar-dialog/submit")
async def submit_avatar_dialog(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Submit avatar/profile updates and forward to remote server."""
    service = SNSService(db)
    return await service.submit_avatar_dialog(request)


@router.get("/avatars3d", response_model=List[Avatar3DItem])
async def get_avatars_3d():
    """Get list of available 3D avatars"""
    import os
    import glob

    avatar_dir = "static/avatar3d"
    avatars = []

    png_files = glob.glob(os.path.join(avatar_dir, "*.png"))
    for png_file in sorted(png_files):
        basename = os.path.basename(png_file)
        name = os.path.splitext(basename)[0]
        glb_file = os.path.join(avatar_dir, f"{name}.glb")

        if os.path.exists(glb_file):
            avatars.append(Avatar3DItem(
                name=name,
                preview_url=f"/static/avatar3d/{basename}",
                model_url=f"/static/avatar3d/{name}.glb"
            ))

    return avatars


@router.get("/professions", response_model=List[ProfessionItem])
async def get_professions():
    """Get list of available professions"""
    professions = [
        ProfessionItem(
            name="Doctor",
            cost=800,
            description="Setup fee: 800",
            service_description="Remote medical consultation",
            service_price="200",
        ),
        ProfessionItem(
            name="Restaurateur",
            cost=800,
            description="Setup fee: 800",
            service_description="Meal delivery service",
            service_price="20",
        ),
        ProfessionItem(name="Singer", cost=None, description=""),
        ProfessionItem(name="Painter", cost=None, description=""),
        ProfessionItem(name="Designer", cost=None, description=""),
        ProfessionItem(name="Programmer", cost=None, description=""),
        ProfessionItem(name="Teacher", cost=None, description=""),
        ProfessionItem(name="Other", cost=None, description=""),
    ]
    return professions


@router.get("/social-roles", response_model=List[SocialRoleItem])
async def get_social_roles(db: AsyncSession = Depends(get_db)):
    """Get social roles (prompts with SNS tag)"""
    service = SNSService(db)
    return await service.get_social_roles()


@router.get("/social-roles/{role_id}", response_model=SocialRoleItem)
async def get_social_role(role_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific social role by ID"""
    service = SNSService(db)
    role = await service.get_social_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Social role not found")
    return role


@router.put("/social-roles/{role_id}")
async def update_social_role(
    role_id: int,
    request: SocialRoleUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a social role"""
    service = SNSService(db)
    result = await service.update_social_role(role_id, request.dict(exclude_unset=True))
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/prompts/by-title/{title}")
async def get_prompt_by_title(
    title: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a prompt record by its title."""
    service = SNSService(db)
    result = await service.get_prompt_by_title(title)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message") or "Prompt not found")
    return result


@router.put("/prompts/by-title/{title}")
async def upsert_prompt_by_title(
    title: str,
    request: PromptByTitleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a prompt content by its title."""
    service = SNSService(db)
    result = await service.upsert_prompt_content_by_title(title, request.content)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.delete("/social-roles/{role_id}")
async def delete_social_role(
    role_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a social role"""
    service = SNSService(db)
    result = await service.delete_social_role(role_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/user-info")
async def get_user_info(db: AsyncSession = Depends(get_db)):
    """Get user information from aisns_cfg"""
    service = SNSService(db)
    return await service.get_user_info()


@router.put("/user-info")
async def update_user_info(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update user information in aisns_cfg"""
    service = SNSService(db)
    return await service.update_user_info(request)


@router.post("/change-nationpassword")
async def change_nationpassword(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.change_nationpassword(request)


@router.get("/map-config")
async def get_map_config(db: AsyncSession = Depends(get_db)):
    """Get map configuration"""
    service = SNSService(db)
    return await service.get_map_config()


@router.put("/map-config")
async def update_map_config(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update map configuration"""
    service = SNSService(db)
    return await service.update_map_config(request)


@router.get("/model-info")
async def get_model_info(db: AsyncSession = Depends(get_db)):
    """
    Get AI model information from aisns_cfg, agent_cfg, and llm_config

    Returns:
        Model information including provider, model name, and agent name
    """
    service = SNSService(db)
    return await service.get_model_info()


@router.get("/resource-overview")
async def get_resource_overview(db: AsyncSession = Depends(get_db)):
    """Get Resource tab overview content"""
    service = SNSService(db)
    return await service.get_resource_overview()


@router.get("/current-status-overview")
async def get_current_status_overview(db: AsyncSession = Depends(get_db)):
    """Get Current Status overview content"""
    service = SNSService(db)
    return await service.get_current_status_overview()


@router.post("/human-control-state")
async def set_human_control_state(
    request: HumanControlStateRequest,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.set_human_control_state(
        human_take_over=request.human_take_over,
        human_talk_type=request.human_talk_type
    )


@router.post("/human-message")
async def send_human_message(
    request: HumanMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.send_human_message(request.message)


@router.post("/agent-instruction")
async def submit_agent_instruction(
    request: AgentInstructionRequest,
    db: AsyncSession = Depends(get_db)
):
    service = SNSService(db)
    return await service.submit_agent_instruction(request.instruction)


@router.post("/end-active-conversation")
async def end_active_conversation(
    request: EndActiveConversationRequest,
    db: AsyncSession = Depends(get_db),
):
    service = SNSService(db)
    return await service.end_active_conversation(
        reason=request.reason,
        message=request.message or "",
        resume_activity=bool(request.resume_activity),
    )


# ── XMPP A2A Debug Endpoints ──────────────────────────────────────────────
# These endpoints let you verify the A2A setup without a third-party XMPP client.

@router.get("/xmpp-a2a/debug/status")
async def xmpp_a2a_debug_status():
    """Return the current XMPP A2A status, including registered features,
    ad-hoc commands, and the cached agent card.
    """
    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        manager = XMPPClientManager.get_instance()
        client = manager.get_client()
        if client is None:
            return {"success": False, "message": "XMPP client not started"}

        a2a = getattr(client, "_a2a_manager", None)
        if a2a is None:
            return {"success": False, "message": "A2A manager not initialized"}

        status = {
            "success": True,
            "connected": bool(client.is_connected()),
            "jid": str(getattr(client, "boundjid", "")),
            "bare_jid": str(getattr(client.boundjid, "bare", "")) if getattr(client, "boundjid", None) else "",
            "agent_card": a2a._agent_card,
            "disco_features": list(getattr(a2a, "_registered_features", []) or []),
            "adhoc_commands": list(getattr(a2a, "_registered_commands", []) or []),
            "plugins": [],
        }

        # Try multiple paths to enumerate loaded slixmpp plugins
        try:
            pm = client.plugin
            names = None
            for attr in ("_plugins", "_enabled"):
                try:
                    obj = getattr(pm, attr, None)
                    if obj:
                        names = sorted(list(obj))
                        break
                except Exception:
                    continue
            if names is None:
                try:
                    names = sorted(list(iter(pm)))
                except Exception:
                    names = []
            status["plugins"] = names
        except Exception as e:
            status["plugins_error"] = repr(e)

        return status
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


@router.get("/xmpp-a2a/debug/pep-items")
async def xmpp_a2a_debug_pep_items():
    """Read items from the A2A agent card PEP/PubSub node on the local account."""
    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        from runtime.apps.sns.xmpp_a2a import A2A_PEP_NODE
        manager = XMPPClientManager.get_instance()
        client = manager.get_client()
        if client is None or not client.is_connected():
            return {"success": False, "message": "XMPP client not connected"}

        try:
            pubsub = client['xep_0060']
        except Exception:
            pubsub = None
        if pubsub is None:
            return {"success": False, "message": "xep_0060 not available"}

        try:
            iq = await pubsub.get_items(client.boundjid.bare, A2A_PEP_NODE, timeout=10)
        except Exception as e:
            return {"success": False, "message": f"get_items failed: {e!r}"}

        items_out = []
        try:
            for item in iq['pubsub']['items']['substanzas']:
                try:
                    from slixmpp.xmlstream import tostring
                    items_out.append({
                        "id": item.get('id', ''),
                        "xml": tostring(item.xml, xmlns='http://jabber.org/protocol/pubsub'),
                    })
                except Exception:
                    items_out.append({"id": item.get('id', ''), "xml": ""})
        except Exception as e:
            return {"success": False, "message": f"parse failed: {e!r}"}

        return {"success": True, "node": A2A_PEP_NODE, "items": items_out, "count": len(items_out)}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


@router.post("/xmpp-a2a/debug/call-exchange")
async def xmpp_a2a_debug_call_exchange(request: dict):
    """Invoke exchange_business_card on a target JID via generic ad-hoc path.

    Body: {"target_jid": "lili@xabber.de/RESOURCE"}
    """
    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        from runtime.apps.sns.xmpp_a2a import A2A_ADHOC_EXCHANGE_NODE
        manager = XMPPClientManager.get_instance()
        client = manager.get_client()
        if client is None or not client.is_connected():
            return {"success": False, "message": "XMPP client not connected"}

        a2a = getattr(client, "_a2a_manager", None)
        if a2a is None:
            return {"success": False, "message": "A2A manager not initialized"}

        target_jid = (request or {}).get("target_jid") or ""
        if not target_jid:
            target_jid = client.boundjid.full

        # Build form_data from local business card
        my_card = a2a._load_my_business_card() or {}
        form_data = {
            key: (my_card.get(key, '') or '')
            for key in ('name', 'company', 'title', 'email', 'xmpp', 'website', 'phone')
        }

        result = await a2a.call_adhoc_command(target_jid, A2A_ADHOC_EXCHANGE_NODE, form_data)
        return {"success": result.get("ok", False), "target_jid": target_jid, "result": result.get("result")}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


@router.post("/xmpp-a2a/debug/discover-commands")
async def xmpp_a2a_debug_discover_commands(request: dict):
    """Discover ad-hoc commands on a peer.

    Body: {"target_jid": "peer@domain", "agent_card": {...} (optional)}
    """
    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        manager = XMPPClientManager.get_instance()
        client = manager.get_client()
        if client is None or not client.is_connected():
            return {"success": False, "message": "XMPP client not connected"}

        a2a = getattr(client, "_a2a_manager", None)
        if a2a is None:
            return {"success": False, "message": "A2A manager not initialized"}

        target_jid = (request or {}).get("target_jid") or ""
        if not target_jid:
            return {"success": False, "message": "target_jid is required"}

        agent_card = (request or {}).get("agent_card")
        commands = await a2a.discover_peer_adhoc_commands(target_jid, agent_card=agent_card)
        return {"success": True, "target_jid": target_jid, "commands": commands}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


@router.post("/xmpp-a2a/debug/inspect-command")
async def xmpp_a2a_debug_inspect_command(request: dict):
    """Inspect a peer's ad-hoc command form without submitting.

    Body: {"target_jid": "peer@domain", "command_node": "urn:xmpp:a2a:cmd:..."}
    """
    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        manager = XMPPClientManager.get_instance()
        client = manager.get_client()
        if client is None or not client.is_connected():
            return {"success": False, "message": "XMPP client not connected"}

        a2a = getattr(client, "_a2a_manager", None)
        if a2a is None:
            return {"success": False, "message": "A2A manager not initialized"}

        target_jid = (request or {}).get("target_jid") or ""
        command_node = (request or {}).get("command_node") or ""
        if not target_jid or not command_node:
            return {"success": False, "message": "target_jid and command_node are required"}

        result = await a2a.call_adhoc_command(target_jid, command_node, inspect_only=True)
        return {"success": result.get("ok", False), "target_jid": target_jid, "result": result}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


@router.post("/xmpp-a2a/call")
async def xmpp_a2a_call(request: A2AXmppCallRequest):
    """Call a peer agent's A2A service via XMPP Ad-hoc Command.

    Sends a JSON-RPC 2.0 request through the XMPP ad-hoc command node
    (urn:xmpp:a2a:cmd:tasks) and waits for the peer's response.
    Timeout: 300 seconds. Non-blocking for other server requests.

    Request body:
      - peer_jid (str, required): Peer's XMPP JID (e.g. user@domain)
      - method (str): "tasks/send" (default) or "tasks/get"
      - task_id (str): Task ID (required for tasks/get)
      - message_text (str): Text message for tasks/send
      - message_data (dict): Data payload for tasks/send
      - skill_id (str): Target skill ID on the peer agent
      - metadata (dict): Extra metadata to attach

    Returns:
      {"success": true/false, "result": {...}} or {"success": false, "error": "..."}
    """
    import uuid as _uuid
    import json as _json
    from runtime.apps.sns.xmpp_a2a import A2A_ADHOC_TASK_NODE

    peer_jid = (request.peer_jid or "").strip()
    method = (request.method or "tasks/send").strip()

    if not peer_jid:
        return {"success": False, "error": "peer_jid is required"}
    if method not in ("tasks/send", "tasks/get"):
        return {"success": False, "error": f"Unsupported method: {method}. Use 'tasks/send' or 'tasks/get'."}

    # Get XMPP client and A2A manager
    try:
        from runtime.apps.sns.xmpp_client import XMPPClientManager
        manager = XMPPClientManager.get_instance()
        client = manager.get_client()
        if client is None or not client.is_connected():
            return {"success": False, "error": "XMPP client not connected"}

        a2a_mgr = getattr(client, "_a2a_manager", None)
        if a2a_mgr is None:
            return {"success": False, "error": "XMPP A2A manager not initialized"}
    except Exception as e:
        return {"success": False, "error": f"Failed to get XMPP client: {e}"}

    # Build JSON-RPC 2.0 request
    rpc_id = str(_uuid.uuid4())[:8]

    if method == "tasks/send":
        parts = []
        message_text = (request.message_text or "").strip()
        if message_text:
            parts.append({"type": "text", "text": message_text})
        message_data = request.message_data
        if isinstance(message_data, dict) and message_data:
            parts.append({"type": "data", "data": message_data})
        if not parts:
            parts.append({"type": "text", "text": "Hello"})

        rpc_params = {
            "id": f"task-{rpc_id}",
            "message": {"role": "user", "parts": parts},
        }
        skill_id = (request.skill_id or "").strip()
        if skill_id:
            rpc_params["skillId"] = skill_id
        metadata = request.metadata
        if isinstance(metadata, dict) and metadata:
            rpc_params["metadata"] = metadata
    else:
        # tasks/get
        task_id = (request.task_id or "").strip()
        if not task_id:
            return {"success": False, "error": "task_id is required for tasks/get"}
        rpc_params = {"id": task_id}

    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": rpc_params,
        "id": rpc_id,
    }

    # Call peer via generic ad-hoc command path — form_data contains the serialized JSON-RPC request
    form_data = {"jsonrpc_request": _json.dumps(jsonrpc_request, ensure_ascii=False)}
    result = await a2a_mgr.call_adhoc_command(peer_jid, A2A_ADHOC_TASK_NODE, form_data)

    if result.get("ok"):
        # Parse the jsonrpc_response field from the generic result dict
        raw_result = result.get("result", {}) or {}
        jsonrpc_response_str = str(raw_result.get("jsonrpc_response", "") or "").strip()
        if not jsonrpc_response_str:
            # Preserve old API semantics: empty jsonrpc_response is an error.
            return {"success": False, "rpc_id": rpc_id, "error": "Empty response from peer"}
        try:
            response_dict = _json.loads(jsonrpc_response_str)
        except _json.JSONDecodeError as e:
            return {"success": False, "rpc_id": rpc_id, "error": f"Invalid JSON response: {e}"}
        # Check for JSON-RPC error
        if "error" in response_dict and response_dict["error"]:
            err = response_dict["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"success": False, "rpc_id": rpc_id, "error": f"JSON-RPC error: {msg}", "raw": response_dict}
        return {"success": True, "rpc_id": rpc_id, "result": response_dict.get("result", {})}
    else:
        response = {
            "success": False,
            "rpc_id": rpc_id,
            "error": result.get("error", "Unknown error"),
        }
        if result.get("detail") is not None:
            response["detail"] = result.get("detail")
        return response

