/**
 * Custom Bubble InfoWindow for Google Maps (3D)
 *
 * Pure DOM overlay — does NOT use google.maps.InfoWindow.
 * Positions a standalone DOM element via
 * projectionOverlayView.getProjection().fromLatLngToDivPixel()
 * and tracks map movement/zoom through event listeners (indicator pattern).
 *
 * Public API (unchanged):
 *   openBubble(options, mapInstance)  - Open a bubble at a map position
 *   closeBubble()                    - Close the currently open bubble
 *   buildBubbleHTML(options)          - Build bubble HTML string (for advanced use)
 */

/* global google, projectionOverlayView */

// ── Internal state ──────────────────────────────────────────────────
var _gBubbleState = {
    container: null,      // the fixed-position wrapper div (#google-bubble-container)
    position: null,       // google.maps.LatLng or {lat, lng} anchor
    options: null,        // caller options
    map: null,            // google.maps.Map reference
    isOpen: false,
    _projOverlay: null,   // OverlayView used for projection
    _listeners: [],       // google.maps.MapsEventListener handles
};

// ── HTML builder (same output as before) ────────────────────────────

/**
 * Build the HTML markup for the bubble content.
 *
 * @param {Object} options
 * @param {string}  [options.title]       - Header title text (HTML allowed)
 * @param {string}  [options.body]        - Body content (HTML allowed)
 * @param {boolean} [options.showClose]   - Whether to show the close button (default true)
 * @param {string}  [options.closeAction] - onclick JS string for close button
 * @param {string}  [options.extraClass]  - Extra CSS class for the wrapper
 * @returns {string} HTML string
 */
function buildBubbleHTML(options) {
    var title = options.title || '';
    var body = options.body || '';
    var showClose = options.showClose !== false;
    var closeAction = options.closeAction || 'closeBubble()';
    var extraClass = options.extraClass || '';

    // Determine whether we need a header row
    var hasHeader = !!(title || showClose);

    var headerHTML = '';
    if (hasHeader) {
        headerHTML =
            '<div class="bubble-header">' +
                '<div class="bubble-title">' + title + '</div>' +
                (showClose
                    ? '<button class="bubble-close" onclick="' + closeAction + '" title="Close">&#10005;</button>'
                    : '') +
            '</div>';
    }

    // If there is no title and no close button, use the compact "simple" variant
    var wrapperClass = 'bubble-infowindow' + (hasHeader ? '' : ' bubble-simple') + (extraClass ? ' ' + extraClass : '');

    return '<div class="' + wrapperClass + '">' +
        headerHTML +
        '<div class="bubble-body">' + body + '</div>' +
    '</div>';
}

// ── Container management ────────────────────────────────────────────

/**
 * Create or return the singleton fixed-position container.
 */
function _ensureGoogleBubbleContainer() {
    if (_gBubbleState.container) return _gBubbleState.container;

    var el = document.createElement('div');
    el.id = 'google-bubble-container';
    document.body.appendChild(el);
    _gBubbleState.container = el;
    return el;
}

// ── Projection helper ───────────────────────────────────────────────

/**
 * Ensure we have an OverlayView for lat/lng → pixel projection.
 * Reuses the global projectionOverlayView from aisns_building.js if available,
 * otherwise creates a lightweight one.
 */
function _ensureProjectionOverlay(mapInstance) {
    // Prefer the global one already set up by aisns_building.js
    if (typeof projectionOverlayView !== 'undefined' && projectionOverlayView) {
        _gBubbleState._projOverlay = projectionOverlayView;
        return;
    }
    // Already created our own
    if (_gBubbleState._projOverlay) return;

    try {
        var ov = new google.maps.OverlayView();
        ov.onAdd = function () {};
        ov.draw = function () {};
        ov.onRemove = function () {};
        ov.setMap(mapInstance);
        _gBubbleState._projOverlay = ov;
    } catch (e) {
        console.warn('[GoogleBubble] Failed to create projection overlay:', e);
    }
}

// ── Position calculation ────────────────────────────────────────────

/**
 * Recalculate screen position from the geo anchor and apply.
 */
function _updateGoogleBubblePosition() {
    var s = _gBubbleState;
    if (!s.isOpen || !s.container || !s.position || !s.map) return;

    // Get projection
    var proj = null;
    var ov = s._projOverlay ||
        (typeof projectionOverlayView !== 'undefined' ? projectionOverlayView : null);
    if (ov && typeof ov.getProjection === 'function') {
        proj = ov.getProjection();
    }
    if (!proj || typeof proj.fromLatLngToContainerPixel !== 'function') {
        console.warn('[GoogleBubble] projection not ready yet');
        return;
    }

    var pixel;
    try {
        pixel = proj.fromLatLngToContainerPixel(s.position);
    } catch (e) {
        console.warn('[GoogleBubble] fromLatLngToContainerPixel error:', e);
        return;
    }
    if (!pixel) {
        console.warn('[GoogleBubble] fromLatLngToContainerPixel returned null');
        return;
    }

    // Extract pixelOffset (google.maps.Size has .width and .height)
    var offsetX = 0, offsetY = 0;
    if (s.options && s.options.pixelOffset) {
        offsetX = s.options.pixelOffset.width || 0;
        offsetY = s.options.pixelOffset.height || 0;
    }

    // Measure the inner bubble element
    var bubbleEl = s.container.querySelector('.bubble-infowindow');
    if (!bubbleEl) return;

    var bubbleWidth = bubbleEl.offsetWidth || 200;
    var bubbleHeight = bubbleEl.offsetHeight || 100;

    // Get the map container's bounding rect
    var mapDiv = s.map.getDiv ? s.map.getDiv() : null;
    var mapRect = mapDiv ? mapDiv.getBoundingClientRect() : { left: 0, top: 0 };

    // Center horizontally on the point, position above the point
    // 12 = arrow height + small gap
    var left = mapRect.left + pixel.x - bubbleWidth / 2 + offsetX;
    var top = mapRect.top + pixel.y - bubbleHeight - 12 + offsetY;

    s.container.style.left = left + 'px';
    s.container.style.top = top + 'px';
    console.log('[GoogleBubble] position updated: left=' + left + ' top=' + top + ' pixel=(' + pixel.x + ',' + pixel.y + ')');
}

// ── Map event binding ───────────────────────────────────────────────

var _GOOGLE_MAP_EVENTS = ['bounds_changed', 'center_changed', 'zoom_changed', 'resize'];

function _bindGoogleMapEvents(mapInstance) {
    _gBubbleState._listeners = [];
    for (var i = 0; i < _GOOGLE_MAP_EVENTS.length; i++) {
        var listener = mapInstance.addListener(
            _GOOGLE_MAP_EVENTS[i],
            _updateGoogleBubblePosition
        );
        _gBubbleState._listeners.push(listener);
    }
}

function _unbindGoogleMapEvents() {
    for (var i = 0; i < _gBubbleState._listeners.length; i++) {
        try {
            google.maps.event.removeListener(_gBubbleState._listeners[i]);
        } catch (e) {}
    }
    _gBubbleState._listeners = [];
}

// ── Public API ──────────────────────────────────────────────────────

/**
 * Open a custom bubble on the Google Map.
 *
 * @param {Object} options
 * @param {string}  [options.title]       - Header title
 * @param {string}  [options.body]        - Body HTML
 * @param {Object}  options.position      - {lat, lng} or google.maps.LatLng for anchoring
 * @param {google.maps.Size} [options.pixelOffset] - Pixel offset from anchor
 * @param {boolean} [options.showClose]   - Show close button (default true)
 * @param {string}  [options.closeAction] - Custom close onclick code
 * @param {string}  [options.extraClass]  - Extra CSS class
 * @param {google.maps.Map} mapInstance   - The map to open on
 */
function openBubble(options, mapInstance) {
    // Close any previously open bubble
    closeBubble();

    var container = _ensureGoogleBubbleContainer();

    // Normalise position to google.maps.LatLng
    var pos = options.position;
    if (pos && !(pos instanceof google.maps.LatLng)) {
        pos = new google.maps.LatLng(pos.lat, pos.lng);
    }

    // Ensure projection overlay is available
    _ensureProjectionOverlay(mapInstance);

    // Store state
    _gBubbleState.position = pos;
    _gBubbleState.options = options || {};
    _gBubbleState.map = mapInstance;
    _gBubbleState.isOpen = true;

    // Render bubble HTML
    container.innerHTML = buildBubbleHTML(_gBubbleState.options);
    container.style.display = 'block';

    // Prevent map interactions from bleeding through the bubble
    container.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    container.addEventListener('dblclick', function (e) { e.stopPropagation(); });
    container.addEventListener('wheel', function (e) { e.stopPropagation(); });

    // Bind map events for live position tracking
    _bindGoogleMapEvents(mapInstance);

    // Initial position — projection may not be ready yet, so retry a few times
    _updateGoogleBubblePosition();
    // Retry positioning in case projection was not ready on first call
    setTimeout(_updateGoogleBubblePosition, 100);
    setTimeout(_updateGoogleBubblePosition, 300);
    setTimeout(_updateGoogleBubblePosition, 600);

    console.log('Bubble opened');
}

/**
 * Close the currently open bubble.
 * Does NOT fire the closeAction callback (programmatic close).
 */
function closeBubble() {
    if (!_gBubbleState.isOpen) return;

    _gBubbleState.isOpen = false;

    // Remove map event listeners
    _unbindGoogleMapEvents();

    // Hide container
    if (_gBubbleState.container) {
        _gBubbleState.container.style.display = 'none';
        _gBubbleState.container.innerHTML = '';
    }

    // Clear state
    _gBubbleState.position = null;
    _gBubbleState.options = null;
    // Keep .map, .container, ._projOverlay for reuse

    console.log('Bubble closed');
}
