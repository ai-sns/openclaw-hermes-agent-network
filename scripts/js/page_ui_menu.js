//page ui menu
var current_screen_type = "AI";

try {
    if (typeof window !== 'undefined' && window) {
        window.__topInfoDisabled = window.__topInfoDisabled === true;
    }
} catch (e) {
}

function setTopInfoDisabled(disabled) {
    const next = !!disabled;
    try {
        if (typeof window !== 'undefined' && window) {
            window.__topInfoDisabled = next;
        }
    } catch (e) {
    }

    try {
        const btn = document.getElementById('top_info_btn');
        const icon = btn ? btn.querySelector('i') : null;
        if (btn) {
            btn.style.pointerEvents = next ? 'none' : '';
            btn.style.opacity = next ? '0.5' : '';
            btn.setAttribute('aria-disabled', next ? 'true' : 'false');
        }
        if (icon) {
            icon.style.pointerEvents = next ? 'none' : '';
        }
    } catch (e) {
    }
}

try {
    if (typeof window !== 'undefined' && window) {
        window.setTopInfoDisabled = setTopInfoDisabled;
    }
} catch (e) {
}

function __postInfoPanelStateToParent() {
    try {
        const info = document.getElementById('info');
        const visible = !!(info && info.style && info.style.display !== 'none');
        const payload = { type: 'infoPanelState', visible: visible, timestamp: Date.now() };
        if (window.parent && window.parent !== window) {
            window.parent.postMessage(payload, '*');
        }
    } catch (e) {
    }
}

function __syncTopInfoButtonActiveState() {
    try {
        const info = document.getElementById('info');
        const visible = !!(info && info.style && info.style.display !== 'none');
        const btn = document.getElementById('top_info_btn');
        if (btn) {
            if (visible) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }
    } catch (e) {
    }
}

function toggleTopInfoPanel() {
    try {
        if (typeof window !== 'undefined' && window && window.__topInfoDisabled) {
            return;
        }
    } catch (e) {
    }
    try {
        const info = document.getElementById('info');
        const visible = !!(info && info.style && info.style.display !== 'none');
        if (visible) {
            hideHistory();
        } else {
            showHistory();
        }
    } catch (e) {
    }
}

try {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            __syncTopInfoButtonActiveState();
        });
    } else {
        __syncTopInfoButtonActiveState();
    }
} catch (e) {
}

// Map button titles to click handlers
const buttonActions = {
    plaza: function () {
        goPlaza();
    },
    home: function () {
        initPos();
    },
    AI: function () {
        findHim();
    },
    move: function (btn) {
        toggleButtonActive(btn); // Toggle active state only for itself
        set_move_status();
    },
    activity: function (btn) {
        info_window_type = "";
        const isActive = btn.classList.contains('active');
        if (isActive) {
            btn.classList.remove('active');
            hideHistory();
            return;
        } else {
            btn.classList.add('active');
        }
        btn = document.getElementById("message_btn");
        btn.classList.remove('active');
        btn = document.getElementById("system_info_btn");
        btn.classList.remove('active');
        info_title = document.getElementById("info_title");
        if (info_title.textContent == "Notification" || info_title.textContent == "Chat message" || info_title.textContent == "All message") {
            info_title.textContent = "All message";
        } else {
            info_title.textContent = "Journey";
        }

        document.getElementById("info").style.display = "block";
        document.getElementById("info_chat").style.display = "none";
        __syncTopInfoButtonActiveState();
        __postInfoPanelStateToParent();
    }
};

// Toggle button active state
function toggleButtonActive(btn) {
    btn.classList.toggle('active');
}

// Handle button click events
function handleButtonClick(event) {
    const target = event.target instanceof Element ? event.target : event.target?.parentElement;
    if (!target) return;
    const btn = target.closest('.map-btn');
    if (btn) {
        const btnTitle = btn.dataset.title;

        // Handle mutual exclusivity for plaza/home/AI buttons
        if (['plaza', 'home', 'AI'].includes(btnTitle)) {
            document.querySelector('.map-btn.active')?.classList.remove('active');
            btn.classList.add('active');
            buttonActions[btnTitle]();
        } else if (['move', 'activity'].includes(btnTitle)) {
            buttonActions[btnTitle](btn);
        }
    }
}

// Event delegation: attach click handler to .bottom-left-buttons
document.querySelector('.bottom-left-buttons').addEventListener('click', handleButtonClick);

const topButtons = document.querySelector('.top-buttons');
if (topButtons) {
    topButtons.addEventListener('click', function (e) {
        const target = e.target instanceof Element ? e.target : e.target?.parentElement;
        if (!target) return;
        const btn = target.closest('.top-btn');
        if (!btn) return;
        try {
            if (btn.id === 'top_info_btn' && typeof window !== 'undefined' && window && window.__topInfoDisabled) {
                return;
            }
        } catch (e2) {
        }
        const icon = btn.querySelector('i');
        if (!icon) return;
        if (target === icon) return;
        if (typeof icon.onclick === 'function') {
            icon.onclick.call(icon, e);
        }
    });
}

const rightMenuClickRoot = document.querySelector('.right-menu');
if (rightMenuClickRoot) {
    rightMenuClickRoot.addEventListener('click', function (e) {
        const target = e.target instanceof Element ? e.target : e.target?.parentElement;
        if (!target) return;
        const menuItem = target.closest('.menu-item');
        if (!menuItem) return;
        if (target.closest('span[onclick], a[onclick]')) return;
        const clickable = menuItem.querySelector('span[onclick], a[onclick]');
        if (clickable && typeof clickable.onclick === 'function') {
            clickable.onclick.call(clickable, e);
        }
    });
}


document.querySelectorAll('.menu-section').forEach(section => {
    section.addEventListener('click', function (e) {
        const target = e.target instanceof Element ? e.target : e.target?.parentElement;
        if (!target) return;
        const item = target.closest('.menu-item');
        if (item && !item.classList.contains('active')) {
            const activeItem = section.querySelector('.menu-item.active');
            activeItem && activeItem.classList.remove('active');
            item.classList.add('active');
        }
    });
});

// Right menu collapse/expand
const rightMenuToggle = document.querySelector('.right-menu .menu-toggle');
const rightMenu = document.querySelector('.right-menu');

rightMenuToggle.addEventListener('click', function () {
    rightMenu.classList.toggle('collapsed');

    // Toggle icon direction
    const icon = this.querySelector('i');
    icon.classList.toggle('fa-angle-double-right');
    icon.classList.toggle('fa-angle-double-left');
});

// Top bar collapse/expand
const topBarToggle = document.querySelector('.top-bar-toggle');
const topBar = document.querySelector('.top-bar');

topBarToggle.addEventListener('click', function () {
    topBar.classList.toggle('collapsed');

    // Toggle icon direction
    const icon = this.querySelector('i');
    icon.classList.toggle('fa-angle-double-up');
    icon.classList.toggle('fa-angle-double-down');
});

// Show custom confirm dialog
function showConfirmDialog(title, message, onConfirm, onCancel) {
    document.getElementById("dialogTitle").innerText = title; // Set title
    document.getElementById("dialogMessage").innerText = message; // Set message
    document.getElementById("confirmDialog").style.display = "flex"; // Show dialog

    // Confirm button handler
    document.getElementById("confirmButton").onclick = function () {
        onConfirm(); // Invoke confirm callback
        closeDialog();
    };

    // Cancel button handler
    document.getElementById("cancelButton").onclick = function () {
        onCancel(); // Invoke cancel callback
        closeDialog();
    };
}

// Close dialog
function closeDialog() {
    document.getElementById("confirmDialog").style.display = "none"; // Hide dialog
}

function initPos() {
    current_screen_type = "home";
    set_map_center(home_position?.lng, home_position?.lat);
    // Hide plaza-related menu items
    menu_div = document.getElementById('menu-plaza-top');
    if (menu_div) menu_div.style.display = 'none';
    menu_div = document.getElementById('menu-plaza-middle');
    if (menu_div) menu_div.style.display = 'none';
    menu_div = document.getElementById('menu-plaza');
    if (menu_div) menu_div.style.display = 'none';

    // Show AI-related menu items
    menu_div = document.getElementById('menu-ai-top');
    if (menu_div) menu_div.style.display = 'block';
    menu_div = document.getElementById('menu-ai-middle');
    if (menu_div) menu_div.style.display = 'block';
    menu_div = document.getElementById('menu-ai');
    if (menu_div) menu_div.style.display = 'block';

    // Set right menu width to 180px
    const rightMenu = document.querySelector('.right-menu');
    if (rightMenu) {
        rightMenu.style.width = '180px';
    }

    stop_plaza_message();
    aimodel_status.setVisible(true);
}

// Max menu item text length
const MAX_MENU_ITEM_LENGTH = 30;

// Fetch news data from the network and update menu items
async function fetchAndCreateMenuItems() {
    try {
        const resolvedBaseUrl = (typeof API_BASE_URL !== 'undefined' && API_BASE_URL)
            ? API_BASE_URL
            : ((typeof window !== 'undefined' && window.__AGENT_SERVER__) ? window.__AGENT_SERVER__ : '');
        const normalizedBaseUrl = (resolvedBaseUrl || '').replace(/\/+$/, '');
        const response = await fetch(`${normalizedBaseUrl}/api/get_news_list/`);
        const data = await response.json();

        // Update pinned menu items (menu-plaza-top)
        const topMenu = document.getElementById('menu-plaza-top');
        if (topMenu) {
            // Clear existing menu items (except the title)
            const titleElement = topMenu.querySelector('.menu-title');
            topMenu.innerHTML = '';
            if (titleElement) {
                topMenu.appendChild(titleElement);
            }

            // Add new menu items
            data.top.forEach((item, index) => {
                const menuItem = document.createElement('div');
                menuItem.className = 'menu-item';
                menuItem.innerHTML = `<span onclick="open_url('${item.url}')" title="${item.title}">${index + 1}. ${item.title}</span>`;
                topMenu.appendChild(menuItem);
            });
        }

        // Update hot menu items (menu-plaza-middle)
        const middleMenu = document.getElementById('menu-plaza-middle');
        if (middleMenu) {
            // Clear existing menu items (except the title)
            const titleElement = middleMenu.querySelector('.menu-title');
            middleMenu.innerHTML = '';
            if (titleElement) {
                middleMenu.appendChild(titleElement);
            }

            // Add new menu items
            data.hot.forEach((item, index) => {
                const menuItem = document.createElement('div');
                menuItem.className = 'menu-item';
                menuItem.innerHTML = `<span onclick="open_url('${item.url}')" title="${item.title}">${index + 1}. ${item.title}</span>`;
                middleMenu.appendChild(menuItem);
            });
        }

        // Update latest menu items (menu-plaza)
        const plazaMenu = document.getElementById('menu-plaza');
        if (plazaMenu) {
            // Clear existing menu items (except the title)
            const titleElement = plazaMenu.querySelector('.menu-title');
            plazaMenu.innerHTML = '';
            if (titleElement) {
                plazaMenu.appendChild(titleElement);
            }

            // Add new menu items
            data.latest.forEach((item, index) => {
                const menuItem = document.createElement('div');
                menuItem.className = 'menu-item';
                menuItem.innerHTML = `<span onclick="open_url('${item.url}')" title="${item.title}">${index + 1}. ${item.title}</span>`;
                plazaMenu.appendChild(menuItem);
            });
        }
    } catch (error) {
        console.error('Failed to fetch news data:', error);
    }
}

function goPlaza() {
    if (current_screen_type != "plaza") {
        play_plaza_message();
    }
    current_screen_type = "plaza";
    if (plaza_position) {
        set_map_center(plaza_position?.lng, plaza_position?.lat, [0, 0], [17, 20]);
    } else {
        set_map_center(building_position[0], building_position[1]), [0, 0], [17, 20];
    }

    // Fetch and create menu items
    fetchAndCreateMenuItems();

    // Show plaza-related menu items
    menu_div = document.getElementById('menu-plaza-top');
    if (menu_div) menu_div.style.display = 'block';
    menu_div = document.getElementById('menu-plaza-middle');
    if (menu_div) menu_div.style.display = 'block';
    menu_div = document.getElementById('menu-plaza');
    if (menu_div) menu_div.style.display = 'block';

    // Hide AI-related menu items
    menu_div = document.getElementById('menu-ai-top');
    if (menu_div) menu_div.style.display = 'none';
    menu_div = document.getElementById('menu-ai-middle');
    if (menu_div) menu_div.style.display = 'none';
    menu_div = document.getElementById('menu-ai');
    if (menu_div) menu_div.style.display = 'none';

    // Set right menu width to 240px
    const rightMenu = document.querySelector('.right-menu');
    if (rightMenu) {
        rightMenu.style.width = '240px';
    }

    aimodel_status.setVisible(false);
    close_info_list();
}

function check_place(address, lng, lat) {
    set_map_center(lng, lat, [0, 0], [17, 19]);
    msg = address + "\n" + lng + "," + lat;
    alert(msg)
}

function findHim() {

    current_screen_type = "AI";

    let user_current_point;
    if (typeof nation_id_me !== 'undefined' && nation_id_me) {
        user_current_point = getPersonPointByNationId(nation_id_me);
    } else {
        console.error("nation_id_me is undefined or invalid");
        user_current_point = new BMapGL.Point(116.397428, 39.90923); // Fallback to default location
    }

    // Auto-compat for Baidu (properties) and Google (methods)
    const lng = typeof user_current_point.lng === 'function'
        ? user_current_point.lng()
        : user_current_point.lng;

    const lat = typeof user_current_point.lat === 'function'
        ? user_current_point.lat()
        : user_current_point.lat;

    set_map_center(lng, lat);

    // Hide plaza-related menu items
    menu_div = document.getElementById('menu-plaza-top');
    if (menu_div) menu_div.style.display = 'none';
    menu_div = document.getElementById('menu-plaza-middle');
    if (menu_div) menu_div.style.display = 'none';
    menu_div = document.getElementById('menu-plaza');
    if (menu_div) menu_div.style.display = 'none';

    // Show AI-related menu items
    menu_div = document.getElementById('menu-ai-top');
    if (menu_div) menu_div.style.display = 'block';
    menu_div = document.getElementById('menu-ai-middle');
    if (menu_div) menu_div.style.display = 'block';
    menu_div = document.getElementById('menu-ai');
    if (menu_div) menu_div.style.display = 'block';

    // Set right menu width to 180px
    const rightMenu = document.querySelector('.right-menu');
    if (rightMenu) {
        rightMenu.style.width = '180px';
    }

    stop_plaza_message();
    aimodel_status.setVisible(true);
}

function hideHistory() {
    document.getElementById("info").style.display = "none";
    __syncTopInfoButtonActiveState();
    __postInfoPanelStateToParent();
}

function showHistory() {
    info_window_type = "";
    btn = document.getElementById("process_btn");
    btn.classList.add('active');
    btn = document.getElementById("system_info_btn");
    btn.classList.remove('active');
    btn = document.getElementById("message_btn");
    btn.classList.remove('active');
    info_title = document.getElementById("info_title");
    info_title.textContent = lt("Information", "Information");
    document.getElementById("info").style.display = "block";
    __syncTopInfoButtonActiveState();
    __postInfoPanelStateToParent();
}

function clear_chat_history() {
    const infoList = document.getElementById('info_list');
    while (infoList.firstChild) {
        infoList.removeChild(infoList.firstChild); // Remove first child until none remain
    }
}

function clear_chat_list() {
    const infoList = document.getElementById('info_list_chat');
    while (infoList.firstChild) {
        infoList.removeChild(infoList.firstChild); // Remove first child until none remain
    }
}

function show_inform_message_in_info_list() {
    info_window_type = "2";
    btn = document.getElementById("system_info_btn");
    const isActive = btn.classList.contains('active');
    if (isActive) {
        btn.classList.remove('active');
        hideHistory();
        return;
    } else {
        btn.classList.add('active');
    }
    btn = document.getElementById("message_btn");
    btn.classList.remove('active');
    btn = document.getElementById("process_btn");
    btn.classList.remove('active');
    info_title = document.getElementById("info_title");
    info_title.textContent = lt("Notification", "Notifications");
    document.getElementById("info").style.display = "block";
    __syncTopInfoButtonActiveState();
    __postInfoPanelStateToParent();
}

function show_talk_message_in_info_list() {
    info_window_type = "3";
    btn = document.getElementById("message_btn");
    const isActive = btn.classList.contains('active');
    if (isActive) {
        btn.classList.remove('active');
        hideHistory();
        return;
    } else {
        btn.classList.add('active');
    }
    btn = document.getElementById("system_info_btn");
    btn.classList.remove('active');
    btn = document.getElementById("process_btn");
    btn.classList.remove('active');
    info_title = document.getElementById("info_title");
    info_title.textContent = lt("Chat message", "Chat messages");
    document.getElementById("info").style.display = "block";
    __syncTopInfoButtonActiveState();
    __postInfoPanelStateToParent();
}

function close_info_list() {

    info_window_type = "";
    hideHistory();
    btn = document.getElementById("message_btn");
    btn.classList.remove('active');
    btn = document.getElementById("system_info_btn");
    btn.classList.remove('active');
    btn = document.getElementById("process_btn");
    btn.classList.remove('active');

}

function close_info_list_chat() {

    document.getElementById("info_chat").style.display = "none";

}

function addMessageToBoard(message) {
    // Get info list reference
    const infoList = document.getElementById('info_list');

    // Create new list item
    const newListItem = document.createElement('li');

    // Set list item class
    newListItem.className = 'info_list_li';

    // Set list item text content
    // newListItem.textContent = message;

    newListItem.innerHTML = message;
    // Insert new item at the top
    infoList.insertBefore(newListItem, infoList.firstChild);
}

function appendMessageToBoard(message) {
    // Get info list reference
    const infoList = document.getElementById('info_list');

    // Create new list item
    const newListItem = document.createElement('li');

    // Set list item class
    newListItem.className = 'info_list_li';

    // Set list item text content
    // newListItem.textContent = message;

    newListItem.innerHTML = message;
    // Insert new item at the top
    // infoList.insertBefore(newListItem, infoList.firstChild);
    infoList.append(newListItem);

}

function appendMessageToBoardChat(message) {

    close_info_list()

    document.getElementById('info_chat').style.display = "block";
    const infoListChat = document.getElementById('info_list_chat');


    // Create new list item
    const newListItem = document.createElement('li');

    // Set list item class
    newListItem.className = 'info_list_li';

    // Set list item text content
    // newListItem.textContent = message;
    newListItem.innerHTML = message;

    // Insert new item at the top
    // infoListChat.insertBefore(newListItem, infoList.firstChild);
    infoListChat.append(newListItem);


}

// Get info list elements
const infoList = document.getElementById('info_list');
const infoListChat = document.getElementById('info_list_chat');

// Listen for scroll events; load more when near bottom
infoList.addEventListener('scroll', function () {
    // Set a threshold to load more near the bottom
    const threshold = 5; // 5px threshold

    // Check whether scrolled near bottom
    if (infoList.scrollTop + infoList.clientHeight >= infoList.scrollHeight - threshold) {
        loadMoreItems(false);
    }
});

infoListChat.addEventListener('scroll', function () {
    // Set a threshold to load more near the bottom
    const threshold = 5; // 5px threshold

    // Check whether scrolled near bottom
    if (infoListChat.scrollTop + infoListChat.clientHeight >= infoListChat.scrollHeight - threshold) {
        loadMoreItemsChat(false);
    }
});




function setHomePosition() {
    msgdiv = document.getElementById("sethomeposition");
    msgdiv.style.display = "inline";

    // Focus the address input
    const addressInput = document.getElementById('home_address');
    addressInput.focus();

    // Ensure coordinate link click handler is correctly bound
    const coordLinkElement = document.getElementById("home_address_coord_link_element");
    if (coordLinkElement) {
        coordLinkElement.textContent = "Click to get coordinates";
        coordLinkElement.onclick = function() { startCoordinateCapture('home_address'); };
    }
}

function updateHomePosition() {
    // Get input values
    const addressInput = document.getElementById('home_address');
    const scaleInput = document.getElementById('home_scale');
    const rotationInput = document.getElementById('home_rotation');

    const address = addressInput.value;
    const scale = scaleInput.value;
    const rotation = rotationInput.value;

    // If address is in coordinate format, parse it
    let homePosition = {};
    if (address && address.includes(',')) {
        // Assume coordinate format is "lng,lat" or "lng,lat,altitude"
        const coords = address.split(',');
        homePosition.lng = parseFloat(coords[0]);
        homePosition.lat = parseFloat(coords[1]);
        homePosition.altitude = coords[2] ? parseFloat(coords[2]) : 0;
    } else {
        return false;
    }

    // Set scale, default to 20
    homePosition.scale = scale ? parseFloat(scale) : 20;

    // Sync to Python backend
    update_map_setting("home_position", JSON.stringify(homePosition));

    // Handle rotation
    let rotationValues = { x: 0, y: 0, z: 0 };
    if (rotation) {
        const rotations = rotation.split(',');
        rotationValues.x = parseFloat(rotations[0]) || 0;
        rotationValues.y = parseFloat(rotations[1]) || 0;
        rotationValues.z = parseFloat(rotations[2]) || 0;

        update_map_setting("positionx", rotationValues.x);
        update_map_setting("positiony", rotationValues.y);
        update_map_setting("positionz", rotationValues.z);
    }

    // Close settings panel
    closeHomePositionSetting();

    // Show toast
    showAlert("Home location updated successfully");

    // Update house_red.glb model parameters
    updateHouseModel(homePosition, homePosition.scale, rotationValues);
}


function closeHomePositionSetting() {
    msgdiv = document.getElementById("sethomeposition");
    msgdiv.style.display = "none";

    // Reset coordinate link state
    resetCoordinateLinks();
}

function setRoute() {
    // Note: even if currently on specified route (route_status === "playing"), still run
    // to correctly set UI element states

    msgdiv = document.getElementById("setroute");
    msgdiv.style.display = "inline";

    // Get start/end input elements
    const startInput = document.getElementById('start');
    const endInput = document.getElementById('end');
    // Get position_type select
    const positionTypeSelect = document.getElementById('position_type');
    // Get coordinate link elements
    const startCoordLink = document.getElementById("start_coord_link");
    const endCoordLink = document.getElementById("end_coord_link");

    // Set inputs and buttons based on current route status
    if (route_status === "playing") {
        // Already in specified-route state
        // Make inputs read-only
        startInput.setAttribute('readonly', 'readonly');
        endInput.setAttribute('readonly', 'readonly');

        // Hide the confirm button; show view and reset buttons
        const buttons = msgdiv.getElementsByTagName('button');
        for (let i = 0; i < buttons.length; i++) {
            const button = buttons[i];
            const action = (button && button.dataset) ? String(button.dataset.action || '') : '';
            if (action === 'route-confirm') {
                button.style.display = 'none';
            } else if (action === 'route-view' || action === 'route-reset') {
                button.style.display = 'inline';
            }
        }

        // Hide the position_type select
        if (positionTypeSelect) {
            positionTypeSelect.style.display = 'none';
        }

        // When position_type is hidden, coordinate links should be hidden too
        if (startCoordLink) {
            startCoordLink.style.display = 'none';
        }
        if (endCoordLink) {
            endCoordLink.style.display = 'none';
        }

        showAlert("You are already in specified route mode");
    } else {
        // If not in specified-route state
        // Remove readonly attribute (ensure inputs are editable)
        startInput.removeAttribute('readonly');
        endInput.removeAttribute('readonly');

        // Show the confirm button; hide view and reset buttons
        const buttons = msgdiv.getElementsByTagName('button');
        for (let i = 0; i < buttons.length; i++) {
            const button = buttons[i];
            const action = (button && button.dataset) ? String(button.dataset.action || '') : '';
            if (action === 'route-confirm') {
                button.style.display = 'inline';
            } else if (action === 'route-view' || action === 'route-reset') {
                button.style.display = 'none';
            }
        }

        // Show the position_type select
        if (positionTypeSelect) {
            positionTypeSelect.style.display = 'inline-block';
        }

        // Show/hide coordinate links based on position_type
        const positionType = document.getElementById("position_type").value;
        if (positionType === "coordinates") {
            if (startCoordLink) {
                startCoordLink.style.display = 'block';
            }
            if (endCoordLink) {
                endCoordLink.style.display = 'block';
            }
        } else {
            if (startCoordLink) {
                startCoordLink.style.display = 'none';
            }
            if (endCoordLink) {
                endCoordLink.style.display = 'none';
            }
        }
    }

    startInput.focus();

    // Note: do not update the menu checkmark here
    // Only add ✓ after planRoute() successfully plans a route
}

function setRouteRandom() {
    // Check whether it is already in random route mode
    if (route_status === "stopped") {
        showAlert("You are already in random route mode");
        return;
    }

    // Ask user to confirm switching to random route
    showConfirmDialog("Route Settings", "Switch to random route mode?", function() {
        try {
            // Clear existing route
            stopTrack();

            // Update status
            route_status = "stopped";

            // Sync route_status to Python backend
            update_map_setting("route_status", route_status);

            // Clear all route-related data in backend database
            update_map_setting("route_start", "");
            update_map_setting("route_end", "");
            update_map_setting("route_current_position", "");
            update_map_setting("route", "");

            // Reset route settings panel UI state
            const msgdiv = document.getElementById("setroute");
            if (msgdiv) {
                // Close settings panel
                msgdiv.style.display = "none";

                // Reset input states
                const startInput = document.getElementById('start');
                const endInput = document.getElementById('end');
                if (startInput) startInput.removeAttribute('readonly');
                if (endInput) endInput.removeAttribute('readonly');

                // Reset button visibility
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

                // Show the position_type select
                const positionTypeSelect = document.getElementById("position_type");
                if (positionTypeSelect) {
                    positionTypeSelect.style.display = 'inline-block';
                }
            }

            // Reset coordinate link state
            resetCoordinateLinks();

            // Only update menu checkmarks after all operations succeed
            const randomRouteItem = document.getElementById("random_route");
            const specifiedRouteItem = document.getElementById("specified_route");

            if (randomRouteItem && specifiedRouteItem) {
                // Remove ✓ from specified route
                specifiedRouteItem.textContent = specifiedRouteItem.textContent.replace(' ✓', '');
                // Add ✓ to random route
                if (!randomRouteItem.textContent.includes('✓')) {
                    randomRouteItem.textContent += ' ✓';
                }
            }

            showAlert("Switched to random route mode");
        } catch (error) {
            // If operation fails, show error but do not update UI
            showAlert("Failed to switch to random route mode: " + error.message);
            console.error("Failed to switch to random route mode:", error);
        }
    }, function() {
        // User cancelled; no action needed
        return;
    });
}



function closeRouteSetting() {
    //route_status = "stopped";
    msgdiv = document.getElementById("setroute");
    msgdiv.style.display = "none";

    // Reset coordinate links to initial state
    resetCoordinateLinks();
}

// Reset route
function resetRoute() {
    // Get start/end input elements
    const startInput = document.getElementById('start');
    const endInput = document.getElementById('end');
    const msgdiv = document.getElementById("setroute");
    // Get position_type select
    const positionTypeSelect = document.getElementById('position_type');
    // Get coordinate link elements
    const startCoordLink = document.getElementById("start_coord_link");
    const endCoordLink = document.getElementById("end_coord_link");

    // Remove readonly attribute
    startInput.removeAttribute('readonly');
    endInput.removeAttribute('readonly');

    // Show the confirm button; hide view and reset buttons
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

    // Show the position_type select
    if (positionTypeSelect) {
        positionTypeSelect.style.display = 'inline-block';
    }

    // Show/hide coordinate links based on position_type
    const positionType = document.getElementById("position_type").value;
    if (positionType === "coordinates") {
        if (startCoordLink) {
            startCoordLink.style.display = 'block';
        }
        if (endCoordLink) {
            endCoordLink.style.display = 'block';
        }
    } else {
        if (startCoordLink) {
            startCoordLink.style.display = 'none';
        }
        if (endCoordLink) {
            endCoordLink.style.display = 'none';
        }
    }

    // Clear input values
    startInput.value = '';
    endInput.value = '';

    // Focus the start input
    startInput.focus();
}


