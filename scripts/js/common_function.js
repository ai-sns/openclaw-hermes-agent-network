function lt(...args) {
  // Convert map_type to language index
  const lang = (map_type === "baidu") ? 1 : 0;

  let txt;
  if (args.length === 1) {
    txt = args[0].split("|")[lang];
  } else {
    txt = args[lang];
  }

  return txt;
}

// Baidu map.flyTo — sets center, zoom, heading, tilt in one atomic call
// Falls back to centerAndZoom + setHeading + setTilt if flyTo fails
function _baiduFlyTo(point, zoom, heading, tilt, noAnimation) {
    if (noAnimation === undefined) noAnimation = false;


    var targetPoint = null;
    if (point && !isNaN(parseFloat(point.lng)) && !isNaN(parseFloat(point.lat))) {
        targetPoint = new BMapGL.Point(parseFloat(point.lng), parseFloat(point.lat));
    } else {
        console.error('[_baiduFlyTo] Invalid point data:', point);
        return;
    }

    try {

        var opts = {
            center: targetPoint,
            zoom: zoom,
            noAnimation: noAnimation
        };


        if (heading !== undefined && heading !== null) opts.heading = heading;
        if (tilt !== undefined && tilt !== null) opts.tilt = tilt;


        map.flyTo(opts);

    } catch (e) {
        console.warn('[_baiduFlyTo] flyTo failed, falling back to centerAndZoom:', e);


        map.centerAndZoom(targetPoint, zoom);

        setTimeout(function() {
             if (heading !== undefined && heading !== null) map.setHeading(heading);
             if (tilt !== undefined && tilt !== null) map.setTilt(tilt);
        }, 100);
    }
}
function set_map_center(lng, lat, alt = [0, 0], zm = [17, 17]) {
  // Determine index by map_type: google -> 0, baidu -> 1
  const idx = (map_type === "google") ? 0 : 1;
  // Default centers (google / baidu)
  const defaultCenters = [
    { lng: 121.5064029910149, lat: 31.29900523154034, altitude: 0 }, // google
    { lng: 121.51252475315053, lat: 31.304782366270285, altitude: 0 } // baidu
  ];

  // Use passed-in values or defaults
  const center = {
    lng: lng ?? defaultCenters[idx].lng,
    lat: lat ?? defaultCenters[idx].lat,
    altitude: alt[idx] ?? defaultCenters[idx].altitude
  };

  const zoom = zm[idx];

  // Execute map-specific logic
  if (map_type === "google") {
    map.setCenter(center);
    map.setZoom(zoom);
  } else if (map_type === "baidu") {

    map.centerAndZoom(new BMapGL.Point(center.lng, center.lat), zoom);
  } else {
    console.warn("Unknown map_type:", map_type);
  }
}


const alertBox = document.getElementById('myAlert');

const alertMessage = document.getElementById('alertMessage');

let timeoutId; // Store the timeout ID

let __alertProgressContainer = null;
let __alertProgressBar = null;
let __alertProgressText = null;
let __alertProgressActive = false;
let __alertProgressPrevMessage = '';
let __alertProgressPrevShown = false;
let __alertProgressPrevManualClose = false;
let __alertProgressLastMessage = '';
let __alertProgressClearing = false;

let __lastAlertManualClose = false;
let __lastAlertMessage = '';

function __ensureAlertProgressElements() {
    try {
        if (!alertBox) return false;
        if (__alertProgressContainer && __alertProgressBar && __alertProgressText) return true;

        __alertProgressContainer = document.getElementById('alertProgressContainer');
        __alertProgressBar = document.getElementById('alertProgressBar');
        __alertProgressText = document.getElementById('alertProgressText');

        if (__alertProgressContainer && __alertProgressBar && __alertProgressText) return true;

        __alertProgressContainer = document.createElement('div');
        __alertProgressContainer.id = 'alertProgressContainer';
        __alertProgressContainer.style.marginTop = '10px';
        __alertProgressContainer.style.width = '100%';
        __alertProgressContainer.style.display = 'none';

        const track = document.createElement('div');
        track.style.width = '100%';
        track.style.height = '8px';
        track.style.background = 'rgba(0,0,0,0.12)';
        track.style.borderRadius = '6px';
        track.style.overflow = 'hidden';

        __alertProgressBar = document.createElement('div');
        __alertProgressBar.id = 'alertProgressBar';
        __alertProgressBar.style.height = '100%';
        __alertProgressBar.style.width = '0%';
        __alertProgressBar.style.background = '#409EFF';
        __alertProgressBar.style.transition = 'width 120ms linear';
        track.appendChild(__alertProgressBar);

        __alertProgressText = document.createElement('div');
        __alertProgressText.id = 'alertProgressText';
        __alertProgressText.style.marginTop = '6px';
        __alertProgressText.style.fontSize = '12px';
        __alertProgressText.style.color = '#333';
        __alertProgressText.style.textAlign = 'center';
        __alertProgressText.style.whiteSpace = 'nowrap';

        __alertProgressContainer.appendChild(track);
        __alertProgressContainer.appendChild(__alertProgressText);

        alertBox.appendChild(__alertProgressContainer);
        return true;
    } catch (e) {
        return false;
    }
}

function setAlertProgress(message, current, total, timeoutMs, extraText) {
    try {
        const ok = __ensureAlertProgressElements();
        if (!ok) return;
        const cur = Math.max(0, Number(current) || 0);
        const tot = Math.max(1, Number(total) || 1);
        const pct = Math.min(100, Math.max(0, (cur / tot) * 100));

        if (!__alertProgressActive) {
            try {
                __alertProgressPrevMessage = alertMessage ? String(alertMessage.textContent || '') : '';
                __alertProgressPrevShown = !!(alertBox && alertBox.classList && alertBox.classList.contains('show'));
                __alertProgressPrevManualClose = !!__lastAlertManualClose;
            } catch (e) {
                __alertProgressPrevMessage = '';
                __alertProgressPrevShown = false;
                __alertProgressPrevManualClose = false;
            }
            __alertProgressActive = true;
        }

        __alertProgressLastMessage = String(message || '');
        showAlert(__alertProgressLastMessage, true);
        __alertProgressContainer.style.display = 'block';
        __alertProgressBar.style.width = pct + '%';
        const t = (timeoutMs !== undefined && timeoutMs !== null) ? `, timeout=${timeoutMs}ms` : '';
        const extra = extraText ? ` ${String(extraText)}` : '';
        __alertProgressText.textContent = `${cur}/${tot}${t}${extra}`;
    } catch (e) {
    }
}

function clearAlertProgress() {
    try {
        if (__alertProgressClearing) return;
        __alertProgressClearing = true;

        if (!__alertProgressContainer) {
            __alertProgressContainer = document.getElementById('alertProgressContainer');
        }
        if (__alertProgressContainer) {
            __alertProgressContainer.style.display = 'none';
        }
        if (__alertProgressBar) {
            __alertProgressBar.style.width = '0%';
        }
        if (__alertProgressText) {
            __alertProgressText.textContent = '';
        }

        if (__alertProgressActive) {
            const shouldHide = (!__alertProgressPrevShown) || (!__alertProgressPrevManualClose);
            const prevMsg = __alertProgressPrevMessage;
            __alertProgressActive = false;
            __alertProgressPrevMessage = '';
            __alertProgressPrevShown = false;
            __alertProgressPrevManualClose = false;
            __alertProgressLastMessage = '';

            try {
                if (shouldHide) {
                    if (typeof hideAlert === 'function') {
                        hideAlert();
                    }
                } else {
                    if (alertMessage) {
                        alertMessage.textContent = prevMsg;
                    }
                }
            } catch (e) {
            }
        }
    } catch (e) {
    } finally {
        __alertProgressClearing = false;
    }
}

function showAlert(message, manualClose = false, timeout = 1500) {
    __lastAlertManualClose = !!manualClose;
    __lastAlertMessage = String(message || '');
    alertMessage.textContent = message; // Set the message content
    alertBox.classList.add('show');

    // Clear any existing timeout to prevent issues with multiple clicks
    clearTimeout(timeoutId);

    // If manual close is not required, set a timer to auto-hide
    if (!manualClose) {
        // Set a new timeout to hide the alert after specified milliseconds
        timeoutId = setTimeout(hideAlert, timeout);
    }
}

function hideAlert() {
    alertBox.classList.remove('show');
    try {
        clearAlertProgress();
    } catch (e) {
    }
}

function refresh() {
    try {
        if (window.parent && window.parent !== window && typeof window.parent.postMessage === 'function') {
            try {
                if (typeof showAlert === 'function') {
                    showAlert('Reloading, please wait...', true);
                }
            } catch (e) {
            }
            window.parent.postMessage({ type: 'reloadMap', reason: 'mapRefresh' }, '*');
            return;
        }
    } catch (e) {
    }

    location.reload(true);
}

