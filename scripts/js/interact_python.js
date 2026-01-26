// interact with api_server (replaces QWebChannel)

const API_BASE_URL = "http://localhost:8788";
let websocket = null;
let requestIdCounter = 0;

// JSON-RPC 2.0 请求工具函数
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
        showAlert(`API请求失败: ${error.message}`, true);
        return null;
    }
}

// WebSocket 连接
function connectWebSocket() {
    const clientId = `client_${Date.now()}`;
    console.log("Attempting to connect to WebSocket with clientId:", clientId);
    websocket = new WebSocket(`ws://localhost:8788/ws/${clientId}`);

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
        // 尝试重连
        setTimeout(connectWebSocket, 5000);
    };
}

// 处理 WebSocket 消息
function handleWebSocketMessage(data) {
    console.log("DEBUG: handleWebSocketMessage called with data:", data);
    console.log("received message");
    console.log(JSON.stringify(data));
    switch (data.type) {
        case "chat_message":
            console.log("Processing chat_message:", data);
            show_talk_message(data.from, data.to, data.content);
            break;
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
            // 处理后端广播的聊天消息
            console.log("Processing map_chat_message:", data);
            show_talk_message(data.from_user, data.to_user, data.content);
            break;
        default:
            console.log("Received unknown message type:", data.type, data);
            break;
    }
}

// 监听来自父窗口的 postMessage (Electron renderer)
window.addEventListener('message', function(event) {
    // 验证消息来源 - Electron 窗口可能来自 file:// 或其他协议
    // 允许来自 Electron (file://, app://) 或本地服务器的消息
    const allowedOrigins = [
        'file://',
        'http://localhost:8788',
        'http://127.0.0.1:8788'
    ];

    const isAllowedOrigin = allowedOrigins.some(origin =>
        event.origin === origin || event.origin.startsWith('file://')
    );

    if (!isAllowedOrigin && event.origin !== 'null') {
        console.warn('Received message from unexpected origin:', event.origin);
        return;
    }

    console.log('Received postMessage from parent window (Electron):', event.data);
    console.log('Message origin:', event.origin);

    // 处理不同类型的消息
    if (event.data.type === 'init') {
        console.log('Initialization message received:', event.data.data);

        // 发送 "received" 确认消息回父窗口
        const response = {
            type: 'received',
            data: {
                message: 'Message received successfully',
                originalType: event.data.type,
                timestamp: Date.now()
            }
        };

        // 对于 Electron，使用 '*' 作为 targetOrigin，因为 file:// 协议的限制
        try {
            event.source.postMessage(response, '*');
            console.log('Sent "received" confirmation back to parent window (Electron)');
        } catch (error) {
            console.error('Error sending message back to parent:', error);
        }
    }
    // 可以在这里添加处理其他类型消息的逻辑
});

document.addEventListener("DOMContentLoaded", function () {
    // 连接 WebSocket
    connectWebSocket();

    // 延迟加载地图配置，确保所有脚本都已加载
    setTimeout(() => {
        loadMapSetting();
    }, 1000);

    // 加载更多项目
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
                return;
            }
            hiddenPoints[param_1] = div;
        }
        start_talk_to_it(param_1, param_2)
    } else if (command == "move_to_a_place") {
        if (map_type == "google") {
            setPersonModelPointByNationId(nation_id_me, new google.maps.LatLng(parseFloat(param_2), parseFloat(param_1)));
        } else {
            alert("moving");
            alert(param_2);
            setPersonModelPointByNationId(nation_id_me, new BMapGL.Point(parseFloat(param_1), parseFloat(param_2)));
        }
        setPersonPointByNationId(nation_id_me, parseFloat(param_1), parseFloat(param_2));
        findHim();
    } else if (command == "route_move_action") {
        route_move_action_from_python();
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
        // 将配置转换为原格式
        const data = result.data;

        // 处理当前位置：服务器返回数组，需要转换为对象格式
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

    // 对这三个值进行容错处理，如果json.parse正确则使用parse后的值赋值，否则{}
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

    // 检查所有必要字段是否存在，如果不存在则提醒用户
    if (!nationid || nationid === "") {
        showAlert("缺少 nationid 配置，请检查设置", true);
        return;
    }

    if (!account || account === "") {
        showAlert("缺少 account 配置，请检查设置", true);
        return;
    }

    if (!current_position || !current_position.lng || !current_position.lat) {
        showAlert("缺少当前位置配置，请检查设置", true);
        return;
    }

    if (!nick_name || nick_name === "") {
        showAlert("缺少昵称配置，请检查设置", true);
        return;
    }

    if (!avatar || avatar === "") {
        showAlert("缺少头像配置，请检查设置", true);
        return;
    }

    if (!avatar3d || avatar3d === "") {
        showAlert("缺少3D头像配置，请检查设置", true);
        return;
    }

    if (!profile || profile === "") {
        showAlert("缺少个人资料配置，请检查设置", true);
        return;
    }

    if (map_type === undefined || map_type === null) {
        showAlert("缺少地图类型配置，请检查设置", true);
        return;
    }

    // setting_home_position 可以为空，但如果提供了就需要有lng和lat
    if (setting_home_position &&
        (setting_home_position.lng === undefined || setting_home_position.lat === undefined)) {
        showAlert("家庭位置配置不完整，请检查设置", true);
        return;
    }

    nation_id_me = nationid;

    if (route_current_position && Object.keys(route_current_position).length > 0) {
        addMessageToBoard("路线当前位置: " + route_current_position.lng + ", " + route_current_position.lat);
    }

    if (route && route !== "") {
        addMessageToBoard("路线距离: " + route);
    }

    if (route_end && route_end !== "") {
        addMessageToBoard("路线终点: " + route_end);
    }

    if (route_start && route_start !== "") {
        addMessageToBoard("路线起点: " + route_start);
    }

    if (route_status && route_status !== "") {
        var display_route_status;
        if (route_status == "playing") {
            display_route_status = "指定路线";
        } else if (route_status == "stopped") {
            display_route_status = "自由路线";
        } else {
            display_route_status = "路线类型不明";
        }
        addMessageToBoard("路线状态: " + display_route_status);
    }

    if (setting_home_position && Object.keys(setting_home_position).length > 0) {
        addMessageToBoard("家庭位置: " + setting_home_position.lng + ", " + setting_home_position.lat);
    } else {
        addMessageToBoard("家庭位置: 未设置");
    }

    addMessageToBoard("当前位置: " + current_position.lng + ", " + current_position.lat);
    var display_map_type = (map_type == "0") ? "google" : "baidu";
    addMessageToBoard("地图类型: " + display_map_type);
    addMessageToBoard("个人资料: " + profile);
    addMessageToBoard("3D头像: " + avatar3d);
    addMessageToBoard("头像: " + avatar);
    addMessageToBoard("昵称: " + nick_name);
    addMessageToBoard("XMPP账户: " + account);
    addMessageToBoard("用户ID: " + nationid);
    addMessageToBoard("配置加载成功:");

    window.current_position = current_position || {};

    if (map_type == "0") {
        if (typeof map !== 'undefined' && map !== null) {
            const googleCenter = new google.maps.LatLng(current_position.lat, current_position.lng);
            map.setCenter(googleCenter);
            console.log("Google地图中心点已更新:", current_position);
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
    // TODO: 实现加载更多项目的API
    console.log("loadMoreItems", init_flag);
}

async function loadMoreItemsChat() {
    // TODO: 实现加载更多聊天项目的API
    console.log("loadMoreItemsChat");
}

function open_url(url) {
    // 在 Electron 中打开链接
    if (typeof window.electron !== 'undefined') {
        window.electron.openUrl(url);
    } else {
        window.open(url, "_blank");
    }
}

function userInfo() {
    // TODO: 实现用户信息设置功能
    console.log("userInfo");
}

function advSetting() {
    // TODO: 实现高级设置功能
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

    if (typeof window.electron !== 'undefined') {
        window.electron.minimize();
    }
}

function userSetting() {
    // TODO: 实现用户设置功能
    console.log("userSetting");
}

function jobSetting() {
    // TODO: 实现职业设置功能
    console.log("jobSetting");
}

function showGameTarget() {
    // TODO: 实现游戏目标显示功能
    console.log("showGameTarget");
}

function mapcfgSetting() {
    // TODO: 实现地图配置功能
    console.log("mapcfgSetting");
}

function open_sns_profile(url) {
    // TODO: 实现打开社交资料功能
    console.log("open_sns_profile", url);
}

function close_sns_profile() {
    // TODO: 实现关闭社交资料功能
    console.log("close_sns_profile");
}

async function send_im(from, to, msg) {
    await jsonrpcRequest("send_map_chat_message", {
        from_user: from,
        to_user: to,
        content: msg
    });
}
