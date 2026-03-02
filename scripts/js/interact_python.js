// interact with api_server (replaces QWebChannel)

function normalizeHttpBaseUrl(raw) {
    const v = String(raw || '').trim();
    if (!v) return '';
    const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
    return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;
}

function postLocationUpdateToParent(lng, lat) {
    try {
        if (typeof window.parent !== 'undefined' && window.parent && window.parent !== window) {
            window.parent.postMessage({
                type: 'locationUpdate',
                data: {
                    lng: lng,
                    lat: lat,
                    timestamp: Date.now()
                }
            }, '*');
        }
    } catch (e) {
    }
}

function _coerceNumber(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

async function _syncLocationOnce(lng, lat, maxDistanceM) {
    const lngNum = _coerceNumber(lng);
    const latNum = _coerceNumber(lat);
    if (lngNum === null || latNum === null) return;

    __lastLocationSyncAt = Date.now();
    postLocationUpdateToParent(lngNum, latNum);

    const resp = await jsonrpcRequest('update_location_and_get_nearest_place', {
        lng: lngNum,
        lat: latNum,
        max_distance_m: _coerceNumber(maxDistanceM) || 1000
    });

    const url = resp && resp.success && resp.data ? String(resp.data.url || '').trim() : '';
    if (url) {
        try {
            open_place_web_address(url);
        } catch (e) {
            console.warn('Failed to open nearest place url:', e);
        }
    }
}

function update_location_and_open_nearest_place(lng, lat, options = {}) {
    const maxDistanceM = (options && options.maxDistanceM !== undefined) ? options.maxDistanceM : 1000;
    const throttleMs = (options && options.throttleMs !== undefined) ? options.throttleMs : 1200;

    const lngNum = _coerceNumber(lng);
    const latNum = _coerceNumber(lat);
    if (lngNum === null || latNum === null) return;

    __pendingLocation = { lng: lngNum, lat: latNum, maxDistanceM: maxDistanceM };

    const now = Date.now();
    const sinceLast = now - (__lastLocationSyncAt || 0);
    if (sinceLast >= throttleMs && !__locationSyncTimer) {
        const payload = __pendingLocation;
        __pendingLocation = null;
        _syncLocationOnce(payload.lng, payload.lat, payload.maxDistanceM);
        return;
    }

    if (__locationSyncTimer) return;
    const delay = Math.max(50, throttleMs - sinceLast);
    __locationSyncTimer = setTimeout(() => {
        __locationSyncTimer = null;
        const payload = __pendingLocation;
        __pendingLocation = null;
        if (!payload) return;
        _syncLocationOnce(payload.lng, payload.lat, payload.maxDistanceM);
    }, delay);
}

let API_BASE_URL = normalizeHttpBaseUrl((typeof window !== 'undefined' && window.__AGENT_SERVER__) ? window.__AGENT_SERVER__ : '');
if (!API_BASE_URL) {
    try {
        API_BASE_URL = normalizeHttpBaseUrl(window.location && window.location.origin ? window.location.origin : '');
    } catch (e) {
        API_BASE_URL = '';
    }
}

function toWebSocketBaseUrl(httpBaseUrl) {
    try {
        const u = new URL(normalizeHttpBaseUrl(httpBaseUrl));
        const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${wsProto}//${u.host}`;
    } catch (e) {
        return '';
    }
}

const WS_BASE_URL = toWebSocketBaseUrl(API_BASE_URL);
let websocket = null;
let requestIdCounter = 0;

let __locationSyncTimer = null;
let __pendingLocation = null;
let __lastLocationSyncAt = 0;

// JSON-RPC 2.0 request helper
async function jsonrpcRequest(method, params = {}) {
    const requestId = ++requestIdCounter;

    try {
        const response = await fetch(`${API_BASE_URL}/jsonrpc`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: method,
                params: params,
                id: requestId
            })
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(`JSON-RPC error: ${data.error.message} (code: ${data.error.code})`);
        }

        return data.result;
    } catch (error) {
        console.error("JSON-RPC request error:", error);
        showAlert(`API request failed: ${error.message}`, true);
        return null;
    }
}

// WebSocket connection
function connectWebSocket() {
    const clientId = `client_${Date.now()}`;
    console.log("Attempting to connect to WebSocket with clientId:", clientId);
    if (!WS_BASE_URL) {
        console.error('WebSocket base URL not configured');
        return;
    }
    websocket = new WebSocket(`${WS_BASE_URL}/ws/${clientId}`);

    websocket.onopen = function () {
        console.log("WebSocket connected successfully with clientId:", clientId);
        websocket.send(JSON.stringify({"NAME": "CJROK"}));
    };

    websocket.onmessage = function (event) {
        console.log("Received WebSocket message from backend:", event.data);
        try {
            const data = JSON.parse(event.data);
            console.log("Parsed WebSocket data:", data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error("Error parsing WebSocket message:", e);
            console.log("Raw message was:", event.data);
        }
    };

    websocket.onerror = function (error) {
        console.error("WebSocket error:", error);
    };

    websocket.onclose = function () {
        console.log("WebSocket disconnected");
        // Try reconnecting
        setTimeout(connectWebSocket, 5000);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    console.log("DEBUG: handleWebSocketMessage called with data:", data);
    console.log("received message");
    console.log(JSON.stringify(data));
    switch (data.type) {
        case "status_update":
            console.log("Processing status_update:", data);
            show_status_on_map(data.status);
            break;
        case "alert":
            console.log("Processing alert:", data);
            showAlert(data.message, data.is_error || false);
            break;
        case "command":
            console.log("Processing command:", data);
            handle_command(data.command, data.param_1, data.param_2);
            break;
        case "map_setting":
            console.log("Processing map_setting:", data);
            handle_map_setting_loaded(data.setting_json);
            break;
        case "map_chat_message":
            // Handle chat messages broadcast from backend
            console.log("Processing map_chat_message:", data);
            show_talk_message(data.from_user, data.to_user, data.content);
            break;
        default:
            console.log("Received unknown message type:", data.type, data);
            break;
    }
}

// Listen for postMessage from parent window (Electron renderer)
window.addEventListener('message', function(event) {
    // Validate message origin - Electron window may come from file:// or other protocols
    // Allow messages from Electron (file://, app://) or local server
    const allowedOrigins = ['file://'];
    try {
        const origin = new URL(API_BASE_URL).origin;
        allowedOrigins.push(origin);
    } catch (e) {
    }

    const isAllowedOrigin = allowedOrigins.some(origin =>
        event.origin === origin || event.origin.startsWith('file://')
    );

    if (!isAllowedOrigin && event.origin !== 'null') {
        console.warn('Received message from unexpected origin:', event.origin);
        return;
    }

    console.log('Received postMessage from parent window (Electron):', event.data);
    console.log('Message origin:', event.origin);

    // Handle different message types
    if (event.data.type === 'init') {
        console.log('Initialization message received:', event.data.data);

        // Send "received" acknowledgement back to parent window
        const response = {
            type: 'received',
            data: {
                message: 'Message received successfully',
                originalType: event.data.type,
                timestamp: Date.now()
            }
        };

        // For Electron, use '*' as targetOrigin due to file:// protocol limitations
        try {
            event.source.postMessage(response, '*');
            console.log('Sent "received" confirmation back to parent window (Electron)');
        } catch (error) {
            console.error('Error sending message back to parent:', error);
        }
    } else if (event.data.type === 'mapButtonAction') {
        // Handle button click requests from Electron frontend
        const action = event.data.action;
        const meta = (event.data && typeof event.data === 'object') ? (event.data.meta || {}) : {};
        console.log('Received mapButtonAction from electron:', action);

        try {
            if (meta && meta.setTopInfoDisabled !== undefined && meta.setTopInfoDisabled !== null) {
                const disabled = !!meta.setTopInfoDisabled;
                if (typeof window.setTopInfoDisabled === 'function') {
                    window.setTopInfoDisabled(disabled);
                } else {
                    const btn = document.getElementById('top_info_btn');
                    if (btn) {
                        btn.style.pointerEvents = disabled ? 'none' : '';
                        btn.style.opacity = disabled ? '0.5' : '';
                        btn.setAttribute('aria-disabled', disabled ? 'true' : 'false');
                    }
                }
            }
        } catch (e) {
            console.warn('Failed to update top info disabled state:', e);
        }

        const getInfoVisible = () => {
            try {
                const info = document.getElementById('info');
                if (!info) return false;
                return info.style.display !== 'none';
            } catch (e) {
                return false;
            }
        };

        const postToParent = (payload) => {
            try {
                if (window.parent && window.parent !== window) {
                    window.parent.postMessage(payload, '*');
                }
            } catch (e) {
            }
        };

        if (meta && meta.captureInfoPanelState) {
            // Capture BEFORE Square hides it.
            postToParent({
                type: 'infoPanelState',
                visible: getInfoVisible(),
                timestamp: Date.now()
            });
        }

        // Find the corresponding button and trigger click
        const buttonSelector = `.map-btn[data-title="${action}"]`;
        const button = document.querySelector(buttonSelector);

        if (button) {
            console.log('Found button, triggering click:', buttonSelector);
            button.click();

            try {
                if (typeof window.setAisnsVideoSoundGate === 'function') {
                    window.setAisnsVideoSoundGate(action === 'plaza');
                }
            } catch (e) {
            }

            // Restore info panel if requested (e.g., AI clicked after Square hid it)
            if (meta && meta.restoreInfoPanel) {
                try {
                    if (typeof showHistory === 'function') {
                        showHistory();
                    } else {
                        const info = document.getElementById('info');
                        if (info) info.style.display = 'block';
                    }
                } catch (e) {
                    console.warn('Failed to restore info panel:', e);
                }
            }
        } else {
            console.warn('Button not found:', buttonSelector);
        }
    } else if (event.data && event.data.type === 'snsPluginCommand') {
        const command = event.data.command;
        const params = (event.data && typeof event.data === 'object') ? (event.data.params || {}) : {};

        if (command === 'sendImTo') {
            try {
                const toUser = params && params.to_user ? String(params.to_user).trim() : '';
                const content = params && params.content ? String(params.content) : '';

                if (!toUser || !content) {
                    console.warn('[snsPluginCommand] sendImTo missing to_user/content');
                    return;
                }

                const fromUser = (typeof person_data_me !== 'undefined' && person_data_me && person_data_me.account)
                    ? String(person_data_me.account)
                    : '';

                if (!fromUser) {
                    console.warn('[snsPluginCommand] sendImTo missing current user account');
                    return;
                }

                if (typeof send_im === 'function') {
                    send_im(fromUser, toUser, content);
                } else {
                    console.warn('[snsPluginCommand] send_im function not found');
                }
            } catch (e) {
                console.warn('[snsPluginCommand] sendImTo failed:', e);
            }
        }
    }
    // Add handling for other message types here if needed
});

document.addEventListener("DOMContentLoaded", function () {
    // Connect WebSocket
    connectWebSocket();

    // Delay loading map settings to ensure all scripts are loaded
    setTimeout(() => {
        loadMapSetting();
    }, 1000);

    // Load more items
    loadMoreItems(true);
});

var show_talk_message = function (from, to, msg) {
    console.log(from);
    console.log(to);
    from_point = getPersonPointByAccount(from);
    person_data = getPersonDataByAccount(from);
    if (map_type == "google") {
        send_chat_msg(from_point.lng(), from_point.lat(), msg, person_data["nick_name"]);
    } else {
        send_chat_msg(from_point.lng, from_point.lat, msg, person_data["nick_name"]);
    }
}

var show_status_on_map = function (status) {
    aimodel_status.show(status);
}

var handle_command = function (command, param_1, param_2) {
    if (command == "talk_to_it") {
        if (map_type == "google") {
            let marker = getMarkerByNationId(param_1);
            hiddenMarkers[param_1] = marker;
        } else {
            div = document.getElementById(param_1);
            if (!div) {
                console.warn(`Element with ID ${param_1} not found on map`);
                return;
            }
            hiddenPoints[param_1] = div;
        }
        talk_to_it(param_1, param_2)
    } else if (command == "start_talk_to_it") {
        if (map_type == "google") {
            let marker = getMarkerByNationId(param_1);
            hiddenMarkers[param_1] = marker;
        } else {
            div = document.getElementById(param_1);
            if (!div) {
                console.warn(`Element with ID ${param_1} not found on map`);
                // return;
            }
            hiddenPoints[param_1] = div;
        }
        start_talk_to_it(param_1, param_2)
    } else if (command == "stop_talk_to_it") {
        try {
            stop_talk_to_it(param_1);
        } catch (e) {
            console.error("stop_talk_to_it failed:", e);
        }
    } else if (command == "move_to_a_place") {
        if (map_type == "google") {
            setPersonModelPointByNationId(nation_id_me, new google.maps.LatLng(parseFloat(param_2), parseFloat(param_1)));
        } else {
            alert("Moving");
            alert(param_2);
            setPersonModelPointByNationId(nation_id_me, new BMapGL.Point(parseFloat(param_1), parseFloat(param_2)));
        }
        setPersonPointByNationId(nation_id_me, parseFloat(param_1), parseFloat(param_2));
        findHim();
    } else if (command == "route_move_action") {
        route_move_action_from_python();
    } else if (command == "route_mode_free") {
        try {
            if (typeof route_status !== 'undefined') {
                route_status = "stopped";
            }
            if (typeof window !== 'undefined') {
                window.route_status = "stopped";
            }

            if (typeof stopTrack === 'function') {
                stopTrack();
            }

            if (typeof update_map_setting === 'function') {
                update_map_setting("route_status", "stopped");
                update_map_setting("route_start", "");
                update_map_setting("route_end", "");
                update_map_setting("route_current_position", "");
                update_map_setting("route", "");
            }

            const msgdiv = document.getElementById("setroute");
            if (msgdiv) {
                msgdiv.style.display = "none";
                const startInput = document.getElementById('start');
                const endInput = document.getElementById('end');
                if (startInput) startInput.removeAttribute('readonly');
                if (endInput) endInput.removeAttribute('readonly');

                const buttons = msgdiv.getElementsByTagName('button');
                for (let i = 0; i < buttons.length; i++) {
                    const button = buttons[i];
                    const action = (button && button.dataset) ? String(button.dataset.action || '') : '';
                    if (action === 'route-confirm') {
                        button.style.display = 'inline-block';
                    } else if (action === 'route-view' || action === 'route-reset') {
                        button.style.display = 'none';
                    }
                }

                const positionTypeSelect = document.getElementById("position_type");
                if (positionTypeSelect) {
                    positionTypeSelect.style.display = 'inline-block';
                }
            }

            if (typeof resetCoordinateLinks === 'function') {
                resetCoordinateLinks();
            }

            if (typeof initRouteDisplay === 'function') {
                initRouteDisplay();
            }
        } catch (e) {
            console.error("Failed to switch to Free mode:", e);
        }
    } else if (command == "show_information") {
        addMessageToBoard(param_1);
    } else if (command == "show_information_chat") {
        appendMessageToBoardChat(param_1);
    } else if (command == "load_information") {
        appendMessageToBoard(param_1);
    } else if (command == "load_information_chat") {
        appendMessageToBoardChat(param_1);
    } else if (command == "load_map_setting") {
        handle_map_setting_loaded(param_1);
    } else if (command == "clear_chat_history") {
        clear_chat_history();
    } else if (command == "clear_chat_list") {
        clear_chat_list();
    } else if (command == "check_place") {
        let lng = parseFloat(param_2.split('_')[0]);
        let lat = parseFloat(param_2.split('_')[1]);
        check_place(param_1, lng, lat)
    } else if (command == "python_setting_changed") {
        if (param_1 == "nick_name") {
            alert(param_2);
            person_data_me.nick_name = param_2;
        } else if (param_1 == "profile") {
            alert(param_2);
            person_data_me.profile = param_2;
        }
    }
}

async function loadMapSetting() {
    const result = await jsonrpcRequest("get_map_settings");


    if (result && result.success) {
        // Convert settings to legacy format
        const data = result.data;

        // Handle current position: server may return an array, convert to object
        let current_position_obj;
        if (Array.isArray(data.current_position) && data.current_position.length === 2) {
            current_position_obj = {
                lng: data.current_position[0],
                lat: data.current_position[1]
            };
        } else if (typeof data.current_position === 'object' && data.current_position !== null) {
            current_position_obj = data.current_position;
        } else {
            current_position_obj = {};
        }

        const setting_json = JSON.stringify({
            avatar3d: data.avatar3d,
            nationid: data.nationid,
            account: data.account,
            nick_name: data.nick_name,
            avatar: data.avatar,
            profile: data.profile,
            sns_url: data.sns_url,
            status: data.status,
            map_type: data.map_type,
            current_position: JSON.stringify(current_position_obj),
            home_position: JSON.stringify(data.home_position),
            route_current_position: JSON.stringify(data.route_current_position),
            route: data.route_distance,
            route_start: data.route_start,
            route_end: data.route_end,
            route_status: data.route_status
        });
        handle_map_setting_loaded(setting_json);
    }
}

function handle_map_setting_loaded(setting_json) {
    const settings = JSON.parse(setting_json);

    // Tolerant parsing for these three fields: if JSON.parse succeeds use parsed value, otherwise {}
    try {
        settings.current_position = settings.current_position ? JSON.parse(settings.current_position) : {};
    } catch (e) {
        settings.current_position = {};
    }

    try {
        settings.home_position = settings.home_position ? JSON.parse(settings.home_position) : {};
    } catch (e) {
        settings.home_position = {};
    }

    try {
        settings.route_current_position = settings.route_current_position ? JSON.parse(settings.route_current_position) : {};
    } catch (e) {
        settings.route_current_position = {};
    }

    const {
        avatar3d,
        nationid,
        account,
        nick_name,
        avatar,
        profile,
        sns_url,
        status,
        map_type,
        current_position,
        home_position: setting_home_position,
        route_current_position,
        route,
        route_start,
        route_end,
        route_status
    } = settings;

    // Check required fields; alert user if any is missing
    if (!nationid || nationid === "") {
        showAlert("Missing nationid configuration. Please check your settings.", true);
        return;
    }

    if (!account || account === "") {
        showAlert("Missing account configuration. Please check your settings.", true);
        return;
    }

    if (!current_position || !current_position.lng || !current_position.lat) {
        showAlert("Missing current location configuration. Please check your settings.", true);
        return;
    }

    if (!nick_name || nick_name === "") {
        showAlert("Missing nickname configuration. Please check your settings.", true);
        return;
    }

    if (!avatar || avatar === "") {
        showAlert("Missing avatar configuration. Please check your settings.", true);
        return;
    }

    if (!avatar3d || avatar3d === "") {
        showAlert("Missing 3D avatar configuration. Please check your settings.", true);
        return;
    }

    if (!profile || profile === "") {
        showAlert("Missing profile configuration. Please check your settings.", true);
        return;
    }

    if (map_type === undefined || map_type === null) {
        showAlert("Missing map type configuration. Please check your settings.", true);
        return;
    }

    // setting_home_position may be empty, but if provided it must include lng and lat
    if (setting_home_position &&
        (setting_home_position.lng === undefined || setting_home_position.lat === undefined)) {
        showAlert("Home location configuration is incomplete. Please check your settings.", true);
        return;
    }

    nation_id_me = nationid;

    if (route_current_position && Object.keys(route_current_position).length > 0) {
        addMessageToBoard("Route current position: " + route_current_position.lng + ", " + route_current_position.lat);
    }

    if (route && route !== "") {
        addMessageToBoard("Route distance: " + route);
    }

    if (route_end && route_end !== "") {
        addMessageToBoard("Route end: " + route_end);
    }

    if (route_start && route_start !== "") {
        addMessageToBoard("Route start: " + route_start);
    }

    if (route_status && route_status !== "") {
        var display_route_status;
        if (route_status == "playing") {
            display_route_status = "Specified route";
        } else if (route_status == "stopped") {
            display_route_status = "Free route";
        } else {
            display_route_status = "Unknown route type";
        }
        addMessageToBoard("Route status: " + display_route_status);
    }

    if (setting_home_position && Object.keys(setting_home_position).length > 0) {
        addMessageToBoard("Home position: " + setting_home_position.lng + ", " + setting_home_position.lat);
    } else {
        addMessageToBoard("Home position: Not set");
    }

    addMessageToBoard("Current position: " + current_position.lng + ", " + current_position.lat);
    var display_map_type = (map_type == "0") ? "google" : "baidu";
    addMessageToBoard("Map type: " + display_map_type);
    addMessageToBoard("Profile: " + profile);
    addMessageToBoard("3D avatar: " + avatar3d);
    addMessageToBoard("Avatar: " + avatar);
    addMessageToBoard("Nickname: " + nick_name);
    addMessageToBoard("XMPP account: " + account);
    addMessageToBoard("User ID: " + nationid);
    addMessageToBoard("Configuration loaded successfully:");

    window.current_position = current_position || {};

    if (map_type == "0") {
        if (typeof map !== 'undefined' && map !== null) {
            const googleCenter = new google.maps.LatLng(current_position.lat, current_position.lng);
            map.setCenter(googleCenter);
            console.log("Google map center updated:", current_position);
        }
    } else {
        if (typeof initializeMapCenter === 'function') {
            initializeMapCenter();
        }
    }

    home_position = (setting_home_position && typeof setting_home_position.lng !== 'undefined') ?
        {
            lng: setting_home_position.lng,
            lat: setting_home_position.lat,
            altitude: setting_home_position.altitude
        } : {};

    init_route_current_position = (route_current_position && typeof route_current_position.lng !== 'undefined') ?
        {
            lng: route_current_position.lng,
            lat: route_current_position.lat
        } : {};

    if (route) {
        init_route_distance = parseFloat(route);
        if (typeof window !== 'undefined') {
            window.currentDistance = parseFloat(route);
        } else {
            currentDistance = parseFloat(route);
        }
    }

    if (typeof route_status !== 'undefined' && route_status !== null) {
        window.route_status = route_status;
        initRouteDisplay();

        if (route_status === "playing") {
            setTimeout(function () {
                const startInput = document.getElementById("start");
                const endInput = document.getElementById("end");

                if (startInput && typeof route_start !== 'undefined' && route_start !== null) {
                    startInput.value = route_start;
                }

                if (endInput && typeof route_end !== 'undefined' && route_end !== null) {
                    endInput.value = route_end;
                }

                if (typeof planRoute === 'function' && !window.planRouteRunning) {
                    window.planRouteRunning = true;
                    try {
                        planRoute(false);
                        if (map_type == 1) {
                            setTimeout(function () {
                                continueTrack();
                            }, 15000);
                        }

                        setTimeout(function () {
                            pauseTrack();
                        }, 15500);
                    } catch (e) {
                        console.error("Error executing planRoute:", e);
                    } finally {
                        setTimeout(function () {
                            window.planRouteRunning = true;
                        }, 1000);
                    }
                }
            }, 100);
        }
    }

    person_data_me = {
        nation_id: nationid,
        account: account,
        location: [current_position.lng, current_position.lat],
        nick_name: nick_name,
        avatar: avatar,
        avatar_3d: avatar3d,
        profile: profile,
        sns_url: sns_url,
        status: status
    };

    loadModel(person_data_me);
    load_persons_data_and_show();
}

async function update_map_setting(field_name, field_value) {
    await jsonrpcRequest("update_map_settings", {[field_name]: field_value});
}

async function loadMoreItems(init_flag) {
    // TODO: Implement API for loading more items
    console.log("loadMoreItems", init_flag);
}

async function loadMoreItemsChat() {
    // TODO: Implement API for loading more chat items
    console.log("loadMoreItemsChat");
}

function open_url(url) {
    // Open links in Electron
    const u = String(url || '').trim();
    if (!u) {
        if (typeof showAlert === 'function') {
            showAlert('ai_sns_server is not configured', true);
        }
        return;
    }
    if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
        window.electronAPI.openUrl(u);
    } else {
        window.open(u, "_blank");
    }
}

function userInfo() {
    // Use postMessage to ask Electron frontend to open the user config dialog
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'openDialog',
            dialogType: 'avatar'
        }, '*');
    }
    console.log("userInfo");
}

function advSetting() {
    // TODO: Implement advanced settings
    console.log("advSetting");
}

function Maximize() {
    document.getElementById("maximize").style.display = "none";
    document.getElementById("minimize").style.display = "flex";

    document.querySelector('.top-bar').classList.add('collapsed');
    document.querySelector('.right-menu').classList.add('collapsed');

    const topBarIcon = document.querySelector('.top-bar-toggle i');
    topBarIcon.classList.remove('fa-angle-double-up');
    topBarIcon.classList.add('fa-angle-double-down');

    const rightMenuIcon = document.querySelector('.right-menu .menu-toggle i');
    rightMenuIcon.classList.remove('fa-angle-double-right');
    rightMenuIcon.classList.add('fa-angle-double-left');

    // Tell Electron frontend to collapse sidebar and right panel
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'togglePanels',
            action: 'collapse'
        }, '*');
    }

    if (typeof window.electron !== 'undefined') {
        window.electron.maximize();
    }
}

function Minimize() {
    document.getElementById("minimize").style.display = "none";
    document.getElementById("maximize").style.display = "flex";

    document.querySelector('.top-bar').classList.remove('collapsed');
    document.querySelector('.right-menu').classList.remove('collapsed');

    const topBarIcon = document.querySelector('.top-bar-toggle i');
    topBarIcon.classList.remove('fa-angle-double-down');
    topBarIcon.classList.add('fa-angle-double-up');

    const rightMenuIcon = document.querySelector('.right-menu .menu-toggle i');
    rightMenuIcon.classList.remove('fa-angle-double-left');
    rightMenuIcon.classList.add('fa-angle-double-right');

    // Tell Electron frontend to expand sidebar and right panel
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'togglePanels',
            action: 'expand'
        }, '*');
    }

    if (typeof window.electron !== 'undefined') {
        window.electron.minimize();
    }
}

function userSetting() {
    // Use postMessage to ask Electron frontend to open the social role dialog
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'openDialog',
            dialogType: 'socialRole'
        }, '*');
    }
    console.log("userSetting");
}

function jobSetting() {
    // Use postMessage to ask Electron frontend to open the profession dialog
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'openDialog',
            dialogType: 'profession'
        }, '*');
    }
    console.log("jobSetting");
}

function showGameTarget() {
    // TODO: Implement game target display
    console.log("showGameTarget");
}

function mapcfgSetting() {
    // Use postMessage to ask Electron frontend to open the map config dialog
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'openDialog',
            dialogType: 'mapConfig'
        }, '*');
    }
    console.log("mapcfgSetting");
}

function open_place_web_address(url) {
    console.log("open_place_web_address", url);

    // Tell Electron frontend to add a Profile tab in the right status panel
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'openPlaceWebAddress',
            url: url
        }, '*');
    }
}

function open_sns_profile(url) {

    console.log("open_sns_profile", url);

    // Tell Electron frontend to add a Profile tab in the right status panel
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'openSNSProfile',
            url: url
        }, '*');
    }
}

function close_sns_profile() {
    console.log("close_sns_profile");

    // Tell Electron frontend to close the Profile tab
    if (typeof window.parent !== 'undefined') {
        window.parent.postMessage({
            type: 'closeSNSProfile'
        }, '*');
    }
}

async function send_im(from, to, msg) {
    await jsonrpcRequest("send_map_chat_message", {
        from_user: from,
        to_user: to,
        content: msg
    });
}
