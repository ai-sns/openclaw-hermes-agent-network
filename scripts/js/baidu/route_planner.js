var route_status = "stopped";
var track;
var trackData = [];
var colorOffset = [];
var trackLine;
var movePoint;
var is_route_move_action = false;
var currentDistance = 0;
var move_duration = 600;

var __routeTotalDistanceM = 0;
var __routeMoveTargetProcess = null;
var __routeMoveMonitorTimer = null;
var __routeCurrentProcess = 0;
var __routeCurrentDistanceM = 0;

function __snsHaversineDistanceM(lng1, lat1, lng2, lat2) {
    const r = 6371000.0;
    const phi1 = lat1 * Math.PI / 180;
    const phi2 = lat2 * Math.PI / 180;
    const dphi = (lat2 - lat1) * Math.PI / 180;
    const dlambda = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dphi / 2) * Math.sin(dphi / 2) +
        Math.cos(phi1) * Math.cos(phi2) *
        Math.sin(dlambda / 2) * Math.sin(dlambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return r * c;
}

function __snsComputeRouteTotalDistanceM(points) {
    try {
        if (!Array.isArray(points) || points.length < 2) return 0;
        let total = 0;
        for (let i = 1; i < points.length; i++) {
            const p1 = points[i - 1];
            const p2 = points[i];
            const lng1 = Number(p1 && p1.lng);
            const lat1 = Number(p1 && p1.lat);
            const lng2 = Number(p2 && p2.lng);
            const lat2 = Number(p2 && p2.lat);
            if (!Number.isFinite(lng1) || !Number.isFinite(lat1) || !Number.isFinite(lng2) || !Number.isFinite(lat2)) continue;
            total += __snsHaversineDistanceM(lng1, lat1, lng2, lat2);
        }
        return Number.isFinite(total) ? total : 0;
    } catch (e) {
        return 0;
    }
}

function __snsClearRouteMoveMonitor() {
    try {
        if (__routeMoveMonitorTimer) {
            clearInterval(__routeMoveMonitorTimer);
            __routeMoveMonitorTimer = null;
        }
    } catch (e) {
    }
}

// Flag: whether the route planning is initiated by the user
var isUserInitiatedRoutePlanning = false;

// Coordinate capture related variables
var coordinateCaptureMode = false;
var targetInputField = null;
var lastClickPoint = null;

// Rebuild the route directly from cached points.
// points: [{lng:number, lat:number}, ...]
function loadRouteFromPoints(points) {
    try {
        if (!Array.isArray(points) || points.length < 2) {
            throw new Error('Invalid route points');
        }

        // Clear existing route/animation before rebuilding.
        stopTrack();

        const pointArray = points
            .map(p => {
                const lng = Number(p && p.lng);
                const lat = Number(p && p.lat);
                if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
                return new BMapGL.Point(lng, lat);
            })
            .filter(Boolean);

        __routeTotalDistanceM = __snsComputeRouteTotalDistanceM(points);
        __routeCurrentDistanceM = 0;
        __routeCurrentProcess = 0;
        currentDistance = 0;

        if (pointArray.length < 2) {
            throw new Error('Route points are empty after normalization');
        }

        // Draw route polyline.
        try {
            currentRoute = new BMapGL.Polyline(pointArray, {
                strokeColor: "blue",
                strokeWeight: 2,
                strokeOpacity: 0.5
            });
            map.addOverlay(currentRoute);
        } catch (e) {
        }

        // Build Track data.
        track = new Track.View(map, {
            lineLayerOptions: {
                style: {
                    strokeWeight: 8,
                    strokeLineJoin: 'round',
                    strokeLineCap: 'round'
                }
            }
        });

        trackData = [];
        colorOffset = [];

        for (var item of pointArray) {
            var trackPoint = new Track.TrackPoint(item);
            trackData.push(trackPoint);
            var choose = [0.9, 0.5, 0.1];
            var color = choose[Math.floor(Math.random() * choose.length)];
            colorOffset.push(color);
        }

        trackLine = new Track.LocalTrack({
            trackPath: trackData,
            duration: move_duration,
            style: {
                sequence: true,
                marginLength: 32,
                arrowColor: '#fff',
                strokeTextureUrl: 'https://mapopen-pub-jsapi.bj.bcebos.com/jsapiGlgeo/img/down.png',
                strokeTextureWidth: 64,
                strokeTextureHeight: 32,
                traceColor: [27, 142, 236]
            },
            linearTexture: [[0, '#f45e0c'], [0.5, '#f6cd0e'], [1, '#2ad61d']],
            gradientColor: colorOffset
        });

        track.addTrackLine(trackLine);

        // Create move point model.
        movePoint = new Track.ModelPoint({ point: trackData[0].getPoint(), style:{
            url: 'https://mapopen-pub-jsapi.bj.bcebos.com/jsapiGlgeo/img/bus.glb',
            scale: 9,
            level: 18,
            rotationX: 90,
            rotationY: 90,
            rotationZ: 0
        } });

        trackLine.setMovePoint(movePoint);

        try {
            const initD = Number((typeof init_route_distance !== 'undefined') ? init_route_distance : 0);
            if (Number.isFinite(initD) && initD > 0 && __routeTotalDistanceM > 0) {
                const p = Math.min(1, Math.max(0, initD / __routeTotalDistanceM));
                __routeCurrentProcess = p;
                __routeCurrentDistanceM = initD;
                currentDistance = initD;
                trackLine.setProcess(p);
            }
        } catch (e) {
        }

        // Fit map to route.
        try {
            const box = trackLine.getBBox();
            if (box) {
                var bounds = [new BMapGL.Point(box[0], box[1]), new BMapGL.Point(box[2], box[3])];
                map.setViewport(bounds);
            }
        } catch (e) {
        }

        try {
            route_status = 'playing';
            update_map_setting('route_status', route_status);
        } catch (e) {
        }

        try {
            update_map_setting('route_points', JSON.stringify({ provider: 'baidu', points: points }));
        } catch (e) {
        }
    } catch (e) {
        console.error('loadRouteFromPoints failed:', e);
        try {
            showAlert('Failed to replay cached route. Re-planning is required.', true);
        } catch (e2) {
        }
    }
}

try {
    if (typeof window !== 'undefined') {
        window.loadRouteFromPoints = loadRouteFromPoints;
    }
} catch (e) {
}

// Geocode address to coordinate (Promise wrapper)
function geocodeAddressbakok(address, city) {
    return new Promise((resolve, reject) => {
        new BMapGL.Geocoder().getPoint(address, point => {
            if (point) resolve(point);
            else reject(`Address resolution failed: ${address}`);
        }, city);
    });
}

/**
 * Geocode address to coordinate (Promise wrapper)
 * @param {string} address - address to resolve
 * @param {string} [city] - optional city constraint
 * @returns {Promise<BMapGL.Point>} Promise that resolves to a coordinate point
 */
function geocodeAddress(address, city) {
    return new Promise((resolve, reject) => {
        try {
            let resolvedAddress = String(address || '').trim();
            let resolvedCity = (city === undefined || city === null) ? '' : String(city).trim();

            if (!resolvedCity) {
                const commaIdx = resolvedAddress.lastIndexOf(',');
                const cnCommaIdx = resolvedAddress.lastIndexOf('，');
                const idx = Math.max(commaIdx, cnCommaIdx);
                if (idx > 0 && idx < resolvedAddress.length - 1) {
                    const inferredCity = resolvedAddress.slice(idx + 1).trim();
                    const inferredAddr = resolvedAddress.slice(0, idx).trim();
                    if (inferredCity) {
                        resolvedCity = inferredCity;
                        if (inferredAddr) {
                            resolvedAddress = inferredAddr;
                        }
                    }
                }
                if (!resolvedCity) {
                    resolvedCity = '北京市';
                }
            }

            // Create geocoder instance
            const geocoder = new BMapGL.Geocoder();

            // Execute geocoding
            geocoder.getPoint(
                resolvedAddress,
                (point) => {
                    // Success callback
                    if (point) {
                        resolve(point);
                        return;
                    }
                    reject(new Error(`Address resolution failed: "${resolvedAddress}"`));
                },
                resolvedCity,
                (errorCode) => {  // Baidu map error callback
                    alert(`Geocoding error [${errorCode}]: ${getGeocodeErrorMsg(errorCode)}`);
                    reject(new Error(`Geocoding error [${errorCode}]: ${getGeocodeErrorMsg(errorCode)}`));
                }
            );
        } catch (error) {
            // Catch sync errors (e.g. constructor exceptions)
            reject(new Error(`Failed to initialize geocoding: ${error.message}`));
        }
    });
}

function __withTimeout(promise, timeoutMs) {
    return new Promise((resolve, reject) => {
        let settled = false;
        const timer = setTimeout(() => {
            if (settled) return;
            settled = true;
            reject(new Error('timeout'));
        }, Math.max(0, Number(timeoutMs) || 0));

        Promise.resolve(promise)
            .then((v) => {
                if (settled) return;
                settled = true;
                clearTimeout(timer);
                resolve(v);
            })
            .catch((e) => {
                if (settled) return;
                settled = true;
                clearTimeout(timer);
                reject(e);
            });
    });
}

async function __geocodeAddressWithRetry(address, city, timeoutMs = 1000, maxRetries = 10, label = '') {
    let lastErr = null;
    const retries = Math.max(1, Number(maxRetries) || 1);
    const __labelText = String(label || '').trim();
    const __progressTitle = __labelText ? `Geocoding ${__labelText} Address...` : 'Geocoding address...';
    for (let i = 0; i < retries; i++) {
        try {
            console.log(`[geocode retry] attempt ${i + 1}/${retries}, timeout=${timeoutMs}ms, address=${String(address || '')}, city=${String(city || '')}`);
        } catch (e0) {
        }
        try {
            if (i > 0 && typeof setAlertProgress === 'function') {
                setAlertProgress(__progressTitle, i + 1, retries, timeoutMs, '');
            }
        } catch (e0) {
        }
        try {
            const point = await __withTimeout(geocodeAddress(address, city), timeoutMs);
            try {
                if (typeof clearAlertProgress === 'function') {
                    clearAlertProgress();
                }
            } catch (e0) {
            }
            return point;
        } catch (e) {
            lastErr = e;
            try {
                const isTimeout = !!(e && (String(e.message || '').toLowerCase().includes('timeout')));
                if (isTimeout) {
                    console.log(`[geocode retry] timeout on attempt ${i + 1}/${retries} after ${timeoutMs}ms`);
                    try {
                        if (i > 0 && typeof setAlertProgress === 'function') {
                            setAlertProgress(__progressTitle, i + 1, retries, timeoutMs, 'timeout');
                        }
                    } catch (e2) {
                    }
                } else {
                    console.log(`[geocode retry] failed on attempt ${i + 1}/${retries}: ${String(e && (e.message || e))}`);
                    try {
                        if (i > 0 && typeof setAlertProgress === 'function') {
                            setAlertProgress(__progressTitle, i + 1, retries, timeoutMs, 'failed');
                        }
                    } catch (e2) {
                    }
                }
            } catch (e1) {
            }
        }
    }
    try {
        if (typeof clearAlertProgress === 'function') {
            clearAlertProgress();
        }
    } catch (e0) {
    }
    throw lastErr || new Error('geocode failed');
}

async function __drivingSearchWithRetry(startPoint, endPoint, timeoutMs = 1000, maxRetries = 10) {
    let lastErr = null;
    const retries = Math.max(1, Number(maxRetries) || 1);
    for (let i = 0; i < retries; i++) {
        try {
            console.log(`[driving.search retry] attempt ${i + 1}/${retries}, timeout=${timeoutMs}ms`);
        } catch (e0) {
        }
        try {
            if (i > 0 && typeof setAlertProgress === 'function') {
                setAlertProgress('Planning route...', i + 1, retries, timeoutMs, '');
            }
        } catch (e0) {
        }
        try {
            let prevHook = undefined;
            let hook = null;
            const restoreHook = () => {
                try {
                    if (typeof window !== 'undefined' && window.__baiduDrivingSearchHook === hook) {
                        window.__baiduDrivingSearchHook = prevHook;
                    }
                } catch (e) {
                }
            };

            const attemptPromise = new Promise((resolve, reject) => {
                prevHook = (typeof window !== 'undefined') ? window.__baiduDrivingSearchHook : undefined;
                hook = (status, result) => {
                    restoreHook();
                    resolve({ status: status, result: result });
                };

                try {
                    if (typeof window !== 'undefined') {
                        window.__baiduDrivingSearchHook = hook;
                    }
                } catch (e) {
                }

                try {
                    driving.search(startPoint, endPoint);
                } catch (e) {
                    restoreHook();
                    reject(e);
                }
            });

            const res = await __withTimeout(attemptPromise, timeoutMs).catch((e) => {
                restoreHook();
                throw e;
            });

            const status = res && typeof res.status !== 'undefined' ? res.status : null;
            const ok = (status === 5) || (typeof BMAP_STATUS_SUCCESS !== 'undefined' && status === BMAP_STATUS_SUCCESS);
            if (ok) {
                try {
                    console.log(`[driving.search retry] success on attempt ${i + 1}/${retries}, status=${String(status)}`);
                } catch (e0) {
                }
                try {
                    if (typeof clearAlertProgress === 'function') {
                        clearAlertProgress();
                    }
                    if (typeof hideAlert === 'function') {
                        hideAlert();
                    }
                } catch (e0) {
                }
                return res.result;
            }

            try {
                console.log(`[driving.search retry] completed but not success on attempt ${i + 1}/${retries}, status=${String(status)}`);
            } catch (e0) {
            }
            try {
                if (i > 0 && typeof setAlertProgress === 'function') {
                    setAlertProgress('Planning route...', i + 1, retries, timeoutMs, `status=${String(status)}`);
                }
            } catch (e0) {
            }
            lastErr = new Error('route search failed');
        } catch (e) {
            lastErr = e;
            try {
                const isTimeout = !!(e && (String(e.message || '').toLowerCase().includes('timeout')));
                if (isTimeout) {
                    console.log(`[driving.search retry] timeout on attempt ${i + 1}/${retries} after ${timeoutMs}ms`);
                    try {
                        if (i > 0 && typeof setAlertProgress === 'function') {
                            setAlertProgress('Planning route...', i + 1, retries, timeoutMs, 'timeout');
                        }
                    } catch (e2) {
                    }
                } else {
                    console.log(`[driving.search retry] failed on attempt ${i + 1}/${retries}: ${String(e && (e.message || e))}`);
                    try {
                        if (i > 0 && typeof setAlertProgress === 'function') {
                            setAlertProgress('Planning route...', i + 1, retries, timeoutMs, 'failed');
                        }
                    } catch (e2) {
                    }
                }
            } catch (e1) {
            }
        }
    }
    try {
        if (typeof clearAlertProgress === 'function') {
            clearAlertProgress();
        }
    } catch (e0) {
    }
    throw lastErr || new Error('route search failed');
}

/**
 * Baidu map error code mapping (extend per official docs)
 * @param {number} code - error code
 * @returns {string} human-readable message
 */
function getGeocodeErrorMsg(code) {
    const errors = {
        1: 'Internal server error',
        2: 'Invalid request parameters',
        3: 'Permission verification failed',
        4: 'Quota verification failed',
        5: 'AK does not exist or is invalid',
        101: 'Service disabled',
        102: 'Not in allowlist or security code mismatch',
        200: 'App does not exist (AK might be incorrect)',
        // Add more codes as needed
    };
    return errors[code] || `Unknown error (${code})`;
}

// Initialize route planning related features
function initialize_route() {
    // Bind position type selector

    const positionTypeSelect = document.getElementById("position_type");
    if (positionTypeSelect) {
        positionTypeSelect.addEventListener("change", function() {
            toggleCoordinateLink();
        });
    }

    // Bind map click for coordinate capture
    map.addEventListener('click', function(e) {
        if (coordinateCaptureMode && targetInputField) {
            handleMapClick(e);
        }
    });
}
initialize_route();
// Toggle coordinate link show/hide
function toggleCoordinateLink() {
    const positionType = document.getElementById("position_type").value;
    const startCoordLink = document.getElementById("start_coord_link");
    const endCoordLink = document.getElementById("end_coord_link");
    const positionTypeSelect = document.getElementById("position_type");

    if (positionType === "coordinates") {
        startCoordLink.style.display = "block";
        endCoordLink.style.display = "block";
    } else {
        startCoordLink.style.display = "none";
        endCoordLink.style.display = "none";

        // Exit coordinate capture mode
        if (coordinateCaptureMode) {
            stopCoordinateCapture();
        }
    }
}

// Start coordinate capture
function startCoordinateCapture(targetField) {
    coordinateCaptureMode = true;
    targetInputField = targetField;

    // Change map cursor
    map.setDefaultCursor("crosshair");

    // Update link text for current field
    const linkElement = document.getElementById(targetField + "_coord_link_element");
    if (linkElement) {
        linkElement.textContent = "Stop coordinate capture";
        linkElement.onclick = stopCoordinateCapture;
    }

    // Ensure other links reset to the initial "get coordinates" text
    const otherFields = ['start', 'end', 'home_address'];
    const currentFieldIndex = otherFields.indexOf(targetField);
    if (currentFieldIndex !== -1) {
        // Reset all other coordinate links
        otherFields.forEach(field => {
            if (field !== targetField) {
                const otherLinkElement = document.getElementById(field + "_coord_link_element");
                if (otherLinkElement) {
                    otherLinkElement.textContent = "Click to get coordinates";
                    otherLinkElement.onclick = function() { startCoordinateCapture(field); };
                }
            }
        });
    }

    showAlert("Click on the map to capture coordinates.");
}

// Stop coordinate capture
function stopCoordinateCapture() {
    coordinateCaptureMode = false;
    targetInputField = null;

    // Restore map cursor
    map.setDefaultCursor("url(http://webmap0.bdimg.com/image/api/openhand.cur) 8 8,default");

    // Restore link text and click handler
    const startLinkElement = document.getElementById("start_coord_link_element");
    if (startLinkElement) {
        startLinkElement.textContent = "Click to get coordinates";
        startLinkElement.onclick = function() { startCoordinateCapture('start'); };
    }

    const endLinkElement = document.getElementById("end_coord_link_element");
    if (endLinkElement) {
        endLinkElement.textContent = "Click to get coordinates";
        endLinkElement.onclick = function() { startCoordinateCapture('end'); };
    }

    // Restore home position link text and click handler
    const homeAddressLinkElement = document.getElementById("home_address_coord_link_element");
    if (homeAddressLinkElement) {
        homeAddressLinkElement.textContent = "Click to get coordinates";
        homeAddressLinkElement.onclick = function() { startCoordinateCapture('home_address'); };
    }
}

// Reset coordinate links to initial state
function resetCoordinateLinks() {
    coordinateCaptureMode = false;
    targetInputField = null;

    // Restore map cursor
    map.setDefaultCursor("url(http://webmap0.bdimg.com/image/api/openhand.cur) 8 8,default");

    // Restore start link text and click handler
    const startLinkElement = document.getElementById("start_coord_link_element");
    if (startLinkElement) {
        startLinkElement.textContent = "Click to get coordinates";
        startLinkElement.onclick = function() { startCoordinateCapture('start'); };
    }

    // Restore end link text and click handler
    const endLinkElement = document.getElementById("end_coord_link_element");
    if (endLinkElement) {
        endLinkElement.textContent = "Click to get coordinates";
        endLinkElement.onclick = function() { startCoordinateCapture('end'); };
    }

    // Restore home position link text and click handler
    const homeAddressLinkElement = document.getElementById("home_address_coord_link_element");
    if (homeAddressLinkElement) {
        homeAddressLinkElement.textContent = "Click to get coordinates";
        homeAddressLinkElement.onclick = function() { startCoordinateCapture('home_address'); };
    }
}

// Map click handler
function handleMapClick(e) {
    if (!coordinateCaptureMode || !targetInputField) return;

    // Fill coordinates into target input
    const inputElement = document.getElementById(targetInputField);
    if (inputElement) {
        // Ensure format: lng first, lat second
        inputElement.value = e.latlng.lng + "," + e.latlng.lat;
    }

    // Save last clicked point
    lastClickPoint = e.latlng;

    // Stop coordinate capture
    stopCoordinateCapture();
}

// Plan route (async)
// isUserInitiated: whether initiated by user (default true)
async function planRoute(isUserInitiated = true) {
    const start = document.getElementById("start").value.trim();
    const end = document.getElementById("end").value.trim();
    const positionType = document.getElementById("position_type").value;

    const splitAddressCity = (value) => {
        const raw = String(value || '').trim();
        const firstComma = raw.indexOf(',');
        if (firstComma <= 0 || firstComma !== raw.lastIndexOf(',')) return null;
        const address = raw.slice(0, firstComma).trim();
        const city = raw.slice(firstComma + 1).trim();
        if (!address || !city) return null;
        return { address, city };
    };

    let startAddressForGeocode = start;
    let startCityForGeocode = '北京市';
    let endAddressForGeocode = end;
    let endCityForGeocode = '北京市';

    if (!start || !end) {
        try {
            showAlert('Please enter both start and end. Recommended format: "address, city".', true);
        } catch (e) {
            showAlert('Please enter both start and end. Recommended format: "address, city".', true);
        }
        return;
    }

    if (isUserInitiated && positionType === 'address') {
        const hasChinese = (s) => /[\u4e00-\u9fff]/.test(String(s || ''));
        const hasLatin = (s) => /[A-Za-z]/.test(String(s || ''));
        const validateAddressCity = (value) => {
            const parts = splitAddressCity(value);
            if (!parts) return null;
            if (!hasChinese(parts.address) || !hasChinese(parts.city)) return null;
            if (hasLatin(parts.address) || hasLatin(parts.city)) return null;
            return parts;
        };

        const startParts = validateAddressCity(start);
        if (!startParts) {
            try {
                showAlert('Start must include a city. Recommended format: "address, city".', true);
            } catch (e) {
                showAlert('Start must include a city. Recommended format: "address, city".', true);
            }
            return;
        }

        startAddressForGeocode = startParts.address;
        startCityForGeocode = startParts.city;

        const endParts = validateAddressCity(end);
        if (!endParts) {
            try {
                showAlert('End must include a city. Recommended format: "address, city".', true);
            } catch (e) {
                showAlert('End must include a city. Recommended format: "address, city".', true);
            }
            return;
        }

        endAddressForGeocode = endParts.address;
        endCityForGeocode = endParts.city;

        try {
            showAlert('Planning route...', false);
        } catch (e) {
            showAlert('Planning route...', false);
        }
    }

    try {
        // Clear existing route before planning a new one
        stopTrack();

        let startPoint, endPoint;

        function tryParseLngLat(value) {
            if (typeof value !== 'string') return null;
            const parts = value.split(',');
            if (parts.length !== 2) return null;
            const lng = parseFloat(String(parts[0]).trim());
            const lat = parseFloat(String(parts[1]).trim());
            if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
            return new BMapGL.Point(lng, lat);
        }

        // Parse start point
        if (positionType === 'coordinates') {
            const parsedStart = tryParseLngLat(start);
            if (!parsedStart) {
                throw new Error('Invalid coordinate format. Expected "lng,lat".');
            }
            startPoint = parsedStart;
        } else if (positionType === 'address') {
            const parts = splitAddressCity(start);
            if (parts) {
                startAddressForGeocode = parts.address;
                startCityForGeocode = parts.city;
            }
            console.log("getting start point");
            startPoint = await __geocodeAddressWithRetry(startAddressForGeocode, startCityForGeocode, 1000, 30, 'Start');
            console.log(startPoint);
        } else {
            const parsedStart = tryParseLngLat(start);
            console.log("getting start point");
            startPoint = parsedStart ? parsedStart : await __geocodeAddressWithRetry(start, "北京市", 1000, 30, 'Start');
            console.log(startPoint);
        }

        // Parse end point
        if (positionType === 'coordinates') {
            const parsedEnd = tryParseLngLat(end);
            if (!parsedEnd) {
                throw new Error('Invalid coordinate format. Expected "lng,lat".');
            }
            endPoint = parsedEnd;
        } else if (positionType === 'address') {
            const parts = splitAddressCity(end);
            if (parts) {
                endAddressForGeocode = parts.address;
                endCityForGeocode = parts.city;
            }
            console.log("getting end point");
            endPoint = await __geocodeAddressWithRetry(endAddressForGeocode, endCityForGeocode, 1000, 30, 'End');
            console.log(endPoint);
        } else {
            const parsedEnd = tryParseLngLat(end);
            console.log("getting end point");
            endPoint = parsedEnd ? parsedEnd : await __geocodeAddressWithRetry(end, "北京市", 1000, 30, 'End');
            console.log(endPoint);
        }

        // Step 3: plan route using coordinates
        // Set flag based on parameter: whether user initiated
        isUserInitiatedRoutePlanning = isUserInitiated;

        // Note: driving.search() is async; success triggers onSearchComplete
        // State/UI will be updated in onSearchComplete; no immediate update needed here
        console.log("Requesting route search and plan.");
        await __drivingSearchWithRetry(startPoint, endPoint, 1000, 40);

        try {
            if (typeof closeRouteSetting === 'function') {
                closeRouteSetting();
            } else {
                const routeDialog = document.getElementById('setroute');
                if (routeDialog) routeDialog.style.display = 'none';
            }
        } catch (e0) {
        }

        // Note: do not update state/UI here
        // Only update after confirming success in onSearchComplete
        // This avoids incorrect UI updates when planning fails
    } catch (error) {
        try {
            const detail = String((error && (error.message || error)) || '');
            showAlert('Route planning failed. Please resubmit and retry. ' + detail, true);
        } catch (e2) {
            const detail = String((error && (error.message || error)) || '');
            showAlert('Route planning failed. Please resubmit and retry. ' + detail, true);
        }
    }
}

function getAllGpsPositions(routeResult) {
    var positions = [];
    positions = routeResult.getPlan(0).getRoute(0).getPath();
    console.log(positions);

    // Draw route on the map
    const pointArray = positions.map(pos => new BMapGL.Point(pos.lng, pos.lat));

    try {
        const rawPoints = positions.map(p => ({ lng: Number(p.lng), lat: Number(p.lat) }))
            .filter(p => Number.isFinite(p.lng) && Number.isFinite(p.lat));
        __routeTotalDistanceM = __snsComputeRouteTotalDistanceM(rawPoints);
        __routeCurrentDistanceM = 0;
        __routeCurrentProcess = 0;
        currentDistance = 0;
    } catch (e) {
        __routeTotalDistanceM = 0;
    }
    currentRoute = new BMapGL.Polyline(pointArray, {
        strokeColor: "blue",
        strokeWeight: 2,
        strokeOpacity: 0.5
    });
    map.addOverlay(currentRoute)


    track = new Track.View(map, {
        lineLayerOptions: {
            style: {
                strokeWeight: 8,
                strokeLineJoin: 'round',
                strokeLineCap: 'round'
            }
        }
    });

    for (var item of pointArray) {
        var point = item;
        var trackPoint = new Track.TrackPoint(point);
        trackData.push(trackPoint);
        var choose = [0.9, 0.5, 0.1];
        var color = choose[Math.floor(Math.random() * choose.length)];
        colorOffset.push(color);
    }
    console.log('move_duration:', move_duration);

    trackLine = new Track.LocalTrack({
        trackPath: trackData,
        duration: move_duration,
        style: {
            sequence: true,
            marginLength: 32,
            arrowColor: '#fff',
            strokeTextureUrl: 'https://mapopen-pub-jsapi.bj.bcebos.com/jsapiGlgeo/img/down.png',
            strokeTextureWidth: 64,
            strokeTextureHeight: 32,
            traceColor: [27, 142, 236]
        },
        linearTexture: [[0, '#f45e0c'], [0.5, '#f6cd0e'], [1, '#2ad61d']],
        gradientColor: colorOffset
    });

    trackLine.on(Track.LineCodes.STATUS, (status) => {
        switch (status) {
            case Track.StatusCodes.PLAY:
                break;
            case Track.StatusCodes.RESUME:
                break;
            case Track.StatusCodes.INIT:
                break;
            case Track.StatusCodes.PAUSE:
                break;
            case Track.StatusCodes.STOP:
                break;
            case Track.StatusCodes.FINISH:
                var box = trackLine.getBBox();
                if (box) {
                    var bounds = [new BMapGL.Point(box[0], box[1]), new BMapGL.Point(box[2], box[3])];
                    map.setViewport(bounds);
                }
                break;
            default:
                break;
        }
    });

    track.addTrackLine(trackLine);
    // track.focusTrack(trackLine);
    console.log('init_route_current_position.lng:', init_route_current_position.lng);
    movePointbak = new Track.GroundPoint({
        point: (typeof init_route_current_position !== 'undefined' && init_route_current_position !== null)
               ? new BMapGL.Point(init_route_current_position.lng, init_route_current_position.lat)
               : trackData[0].getPoint(),
        style: {
            url: 'http://localhost:8900/scripts/car3.png',//https://mapopen-pub-jsapi.bj.bcebos.com/jsapiGlgeo/img/car.png
            level: 18,
            scale: 1,
            size: new BMapGL.Size(16, 32),
            anchor: new BMapGL.Size(0.5, 0.5),
        }
    });

    //  movePoint = new Track.ModelPoint({ point: trackData[5].getPoint(), style:{
    //     url: 'http://localhost:8900/scripts/3d/mario6.glb',//'https://mapopen-pub-jsapi.bj.bcebos.com/jsapiGlgeo/img/bus.glb''http://localhost:8900/scripts/ybot.glb'http://localhost:8900/scripts/3d/mario3.glb,http://localhost:8900/scripts/3d/mario10.glb 15
    //     scale: 0.08,//9
    //     level: 18,
    //     rotationX: 100,//90
    //     rotationY: 180,//90
    //     rotationZ: 0//0
    // } });

    movePoint = new Track.ModelPoint({ point: trackData[5].getPoint(), style:{
        url: 'https://mapopen-pub-jsapi.bj.bcebos.com/jsapiGlgeo/img/bus.glb',//'http://localhost:8900/scripts/ybot.glb'http://localhost:8900/scripts/3d/mario3.glb,http://localhost:8900/scripts/3d/mario10.glb 15
        scale: 9,
        level: 18,
        rotationX: 90,//90
        rotationY: 90,//90
        rotationZ: 0//0
    } });

    // movePoint.setPosition(new BMapGL.Point(init_route_current_position.lng, init_route_current_position.lat));
    movePoint.addEventListener(Track.MapCodes.CLICK, (e) => {
        console.log('Track.GroundPoint.click', e);
    })
    movePoint.addEventListener(Track.MapCodes.MOUSE_OVER, (e) => {
        console.log('Track.GroundPoint.MOUSE_OVER', e);
    })
    movePoint.addEventListener(Track.MapCodes.MOUSE_OUT, (e) => {
        console.log('Track.GroundPoint.MOUSE_OUT', e);
    })

    movePoint.addEventListener(Track.PointCodes.CHANGE_POINT, (e) => {
        // alert(e.point);
        // setPersonModelPointByNationId(nation_id_me, e);
    })
    //movePoint.show(map);  // Or track.addMovePoint(movePoint);
    // track.addMovePoint(movePoint);
    trackLine.setMovePoint(movePoint);


    return positions;
}


// Toggle track from python side
function route_move_action_from_python(allowedDistanceM){
    const n = Number(allowedDistanceM);
    const hasLimit = Number.isFinite(n) && n >= 0;

    __snsClearRouteMoveMonitor();

    if (hasLimit && __routeTotalDistanceM > 0) {
        const targetDistanceM = Math.min(__routeTotalDistanceM, __routeCurrentDistanceM + n);
        __routeMoveTargetProcess = Math.min(1, Math.max(0, targetDistanceM / __routeTotalDistanceM));
    } else {
        __routeMoveTargetProcess = null;
    }

    // Decide startTrack vs continueTrack based on current distance in meters
    if (__routeCurrentDistanceM === 0) {
        startTrack();
    } else {
        continueTrack();
    }

    if (!hasLimit || __routeMoveTargetProcess === null) {
        // Backward compatible: pause after 10s; set a ceiling so pauseTrack can clamp
        if (__routeTotalDistanceM > 0 && move_duration > 0) {
            // Expected progress after 10 seconds of animation
            __routeMoveTargetProcess = Math.min(1, 10 / move_duration + __routeCurrentProcess);
        }
        setTimeout(() => {
            pauseTrack();
        }, 10000);
        return;
    }

    __routeMoveMonitorTimer = setInterval(() => {
        try {
            if (!trackLine) return;
            const p = Number(trackLine.process);
            if (!Number.isFinite(p)) return;
            if (p >= __routeMoveTargetProcess - 1e-6) {
                __snsClearRouteMoveMonitor();
                pauseTrack();
            }
        } catch (e) {
        }
    }, 200);
}

function toggleTrack() {
    const span = document.getElementById('route_opr');
    const icon = document.getElementById('track_icon');

    function setTrackIcon(iconName) {
        try {
            if (!icon) return;
            const isSvg = icon instanceof SVGElement || (icon.classList && icon.classList.contains('ui-icon'));
            if (isSvg) {
                icon.setAttribute('data-icon', iconName);
                const useEl = icon.querySelector('use');
                const href = (typeof window !== 'undefined' && window && typeof window.__getUiIconHref === 'function')
                    ? window.__getUiIconHref(iconName)
                    : null;
                useEl && useEl.setAttribute('href', href);
                return;
            }
            icon.className = `fas fa-${iconName}`;
        } catch (e) {
        }
    }

    switch (route_status) {
        case 'stopped':
            startTrack();
            span.textContent = 'Pause route'; // Update text
            setTrackIcon('circle-pause'); // Update icon: pause
            route_status = 'playing'; // Update state
            break;
        case 'playing':
            pauseTrack();
            span.textContent = 'Resume route'; // Update text
            setTrackIcon('circle-play'); // Update icon: play
            route_status = 'paused'; // Update state
            break;
        case 'paused':
            continueTrack();
            span.textContent = 'Pause route'; // Update text
            setTrackIcon('circle-pause'); // Update icon: pause
            route_status = 'playing'; // Update state
            break;
        default:
            console.error('Unknown route status:', route_status);
    }
    update_map_setting("route_status", route_status);
}


function startTrack() {
        try {
        const persistedPos = (typeof init_route_current_position !== 'undefined' && init_route_current_position !== null)
            ? init_route_current_position
            : null;
        const fallbackPos = (movePoint && typeof movePoint.getPoint === 'function') ? movePoint.getPoint() : null;
        const pos = (persistedPos && Number.isFinite(Number(persistedPos.lng)) && Number.isFinite(Number(persistedPos.lat)))
            ? persistedPos
            : fallbackPos;

        if (map && pos) {
            const lng = Number(pos.lng);
            const lat = Number(pos.lat);
            if (Number.isFinite(lng) && Number.isFinite(lat)) {
                const p = new BMapGL.Point(lng, lat);
                if (typeof map.panTo === 'function') {
                    map.panTo(p);
                } else if (typeof map.setCenter === 'function') {
                    map.setCenter(p);
                }
            }
        }
    } catch (e) {
    }
    driving.clearResults();  // Clear route planning results
    trackLine.startAnimation();
}

function stopTrack() {
    try {
        // 1. Stop all animations
        if (trackLine) {
            try {
                trackLine.stopAnimation();
            } catch (e) {
                console.warn("Failed to stop animation:", e);
            }
        }

        // 2. Remove move point first (bus.glb model)
        if (movePoint && trackLine) {
            try {
                // Remove movePoint from trackLine
                trackLine.setMovePoint(null);
            } catch (e) {
                console.warn("Failed to remove movePoint:", e);
            }

            // If movePoint has hide(), call it
            if (movePoint && typeof movePoint.hide === 'function') {
                try {
                    movePoint.hide();
                } catch (e) {
                    console.warn("Failed to hide movePoint:", e);
                }
            }

            // Try removing movePoint overlay
            if (movePoint && movePoint.Yt && map) {
                try {
                    map.removeOverlay(movePoint.Yt);
                } catch (e) {
                    console.warn("Failed to remove movePoint overlay:", e);
                }
            }
        }

        // 3. Clear track points
        if (trackLine) {
            try {
                trackLine.clearTrackPoint();
            } catch (e) {
                console.warn("Failed to clear track points:", e);
            }
        }

        // 4. Remove track line from map
        if (trackLine && track) {
            try {
                // Remove track line from Track view system
                track.removeTrackLine(trackLine);
            } catch (e) {
                console.warn("Failed to remove track line:", e);
            }

            // Force redraw map
            if (map) {
                try {
                    map._drawFrame(); // Force redraw to ensure visual update
                } catch (e) {
                    console.warn("Failed to redraw map:", e);
                }
            }
        }

        // 5. Clear related data
        trackData = [];
        colorOffset = [];

        if (driving && typeof driving.clearResults === 'function') {
            try {
                driving.clearResults();
            } catch (e) {
                console.warn("Failed to clear route planning results:", e);
            }
        }

        // 7. Reset references
        trackLine = null;

        // 8. Check and remove any leftover polylines
        if (map) {
            try {
                const overlays = map.getOverlays();
                console.log("overlays", overlays);
                for (let overlay of overlays) {
                    // Remove all polyline overlays
                    if (overlay instanceof BMapGL.Polyline) {
                        console.log("Polyline", overlay);
                        map.removeOverlay(overlay);
                    }
                }
            } catch (e) {
                console.warn("Failed to clear polyline overlays:", e);
            }
        }

        console.log("Track and vehicle have been fully cleared");
    } catch (error) {
        console.error("stopTrack failed:", error);
        // Ensure references are cleared even on error
        trackLine = null;
        movePoint = null;
        trackData = [];
        colorOffset = [];
    }
}

function pauseTrack() {
    // FREEZE animation immediately to prevent delta-time accumulation
    trackLine.pauseAnimation();

    // Read progress AFTER pausing so it reflects the frozen state
    let progress = trackLine.process;

    // Clamp progress to target to prevent overshoot from rAF throttling / timing spikes
    if (__routeMoveTargetProcess !== null && Number.isFinite(__routeMoveTargetProcess) &&
        progress > __routeMoveTargetProcess) {
        progress = __routeMoveTargetProcess;
    }

    const currentPoint = movePoint.getPoint();

    // Compute an offset position about 50 meters away
    const offsetDegrees = 0.00090;
    const offsetPoint = new BMapGL.Point(
        currentPoint.lng + offsetDegrees,
        currentPoint.lat + offsetDegrees
    );

    setPersonModelPointByNationId(nation_id_me, offsetPoint);
    setPersonPointByNationId(nation_id_me, offsetPoint.lng, offsetPoint.lat);
    findHim();

    __routeCurrentProcess = Number(progress) || 0;
    __routeCurrentDistanceM = (__routeTotalDistanceM > 0) ? (__routeCurrentProcess * __routeTotalDistanceM) : 0;
    currentDistance = __routeCurrentDistanceM;

    const lng = Number(currentPoint.lng);
    const lat = Number(currentPoint.lat);
    const routeCurrentPos = { lng: lng, lat: lat };
    try {
        init_route_current_position = routeCurrentPos;
    } catch (e) {
    }
    update_map_setting("route_current_position", routeCurrentPos);
    update_map_setting("route", currentDistance);
    try {
        if (typeof sync_current_position === 'function') {
            sync_current_position(lng, lat, { throttleMs: 800 });
        } else {
            update_map_setting("current_position", routeCurrentPos);
        }
    } catch (e) {
        update_map_setting("current_position", routeCurrentPos);
    }
}

function continueTrack() {
    // trackLine.setProcess(0.1904666666666667);
    // findHim();
    try {
        const persistedPos = (typeof init_route_current_position !== 'undefined' && init_route_current_position !== null)
            ? init_route_current_position
            : null;
        const fallbackPos = (movePoint && typeof movePoint.getPoint === 'function') ? movePoint.getPoint() : null;
        const pos = (persistedPos && Number.isFinite(Number(persistedPos.lng)) && Number.isFinite(Number(persistedPos.lat)))
            ? persistedPos
            : fallbackPos;

        if (map && pos) {
            const lng = Number(pos.lng);
            const lat = Number(pos.lat);
            if (Number.isFinite(lng) && Number.isFinite(lat)) {
                const p = new BMapGL.Point(lng, lat);
                if (typeof map.panTo === 'function') {
                    map.panTo(p);
                } else if (typeof map.setCenter === 'function') {
                    map.setCenter(p);
                }
            }
        }
    } catch (e) {
    }
    trackLine.setMovePoint(movePoint);
    trackLine.setProcess(__routeCurrentProcess);
    trackLine.resumeAnimation();
}

function viewRoute() {
    // If a track line exists, fit the map viewport to it
    console.log('viewRoute');
    if (trackLine) {
        // Get track bounding box
        const box = trackLine.getBBox();
        if (box) {
            // Convert bbox to Baidu map Bounds
            const bounds = [
                new BMapGL.Point(box[0], box[1]),
                new BMapGL.Point(box[2], box[3])
            ];
            map.setViewport(bounds);
        }

        // If current position exists, move map center to it
        if (init_route_current_position && init_route_current_position.lng && init_route_current_position.lat) {
            console.log('viewRoute: centering on current position', init_route_current_position);
            const currentPoint = new BMapGL.Point(init_route_current_position.lng, init_route_current_position.lat);
            map.setCenter(currentPoint);
        } else if (trackData && trackData.length > 0) {
            // Otherwise move to route start
            console.log('viewRoute: centering on route start', trackData[0].getPoint());
            map.setCenter(trackData[0].getPoint());
        }
    }else{showAlert("Failed to load route. Check your network, refresh the page, or specify the route again.",true)}
}
