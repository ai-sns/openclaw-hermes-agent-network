/**
 * Custom Bubble InfoWindow for Baidu Maps (WebGL)
 *
 * Pure DOM overlay — does NOT use BMapGL.Overlay or map.addOverlay().
 * Positions a standalone DOM element via map.pointToPixel() and
 * tracks map movement/zoom through event listeners (indicator pattern).
 *
 * Public API (unchanged):
 *   openBaiduBubble(point, options, mapInstance) - Open a bubble at a map point
 *   closeBaiduBubble()                           - Close the currently open bubble
 *   buildBaiduBubbleHTML(options)                 - Build bubble HTML (for advanced use)
 */

/* global BMapGL */

// ── Internal state ──────────────────────────────────────────────────
var _bubbleState = {
    container: null,   // the fixed-position wrapper div (#baidu-bubble-container)
    point: null,       // BMapGL.Point anchor
    options: null,     // caller options
    map: null,         // BMapGL.Map reference
    isOpen: false,
    _boundUpdate: null // bound _updateBubblePosition for event removal
};

// ── HTML builder (same output as before) ────────────────────────────

/**
 * Build the HTML markup for the Baidu bubble content.
 *
 * @param {Object} options
 * @param {string}  [options.title]     - Header title text (HTML allowed)
 * @param {string}  [options.body]      - Body content (HTML allowed)
 * @param {boolean} [options.showClose] - Whether to show the close button (default true)
 * @param {string}  [options.extraClass]- Extra CSS class for the wrapper
 * @returns {string} HTML string
 */
function buildBaiduBubbleHTML(options) {
    var title = options.title || '';
    var body = options.body || '';
    var showClose = options.showClose !== false;
    var extraClass = options.extraClass || '';

    var hasHeader = !!(title || showClose);

    var headerHTML = '';
    if (hasHeader) {
        headerHTML =
            '<div class="bubble-header">' +
                '<div class="bubble-title">' + title + '</div>' +
                (showClose
                    ? '<button class="bubble-close" data-bubble-close="true" title="Close">&#10005;</button>'
                    : '') +
            '</div>';
    }

    var wrapperClass = 'bubble-infowindow' + (hasHeader ? '' : ' bubble-simple') + (extraClass ? ' ' + extraClass : '');

    return '<div class="' + wrapperClass + '">' +
        headerHTML +
        '<div class="bubble-body">' + body + '</div>' +
    '</div>';
}

// ── Container management ────────────────────────────────────────────

/**
 * Create or return the singleton fixed-position container.
 * It sits in document.body, above the map canvas.
 */
function _ensureBubbleContainer() {
    if (_bubbleState.container) return _bubbleState.container;

    var el = document.createElement('div');
    el.id = 'baidu-bubble-container';
    document.body.appendChild(el);
    _bubbleState.container = el;
    return el;
}

// ── Position calculation ────────────────────────────────────────────

/**
 * Recalculate screen position from the geo anchor point and apply.
 * Called on every map move / zoom / resize event.
 */
function _updateBubblePosition() {
    var s = _bubbleState;
    if (!s.isOpen || !s.container || !s.point || !s.map) return;

    var pixel;
    try {
        pixel = s.map.pointToPixel(s.point);
    } catch (e) {
        return;
    }
    if (!pixel) return;

    var offsetX = (s.options && s.options.offset && s.options.offset.x) || 0;
    var offsetY = (s.options && s.options.offset && s.options.offset.y) || 0;

    // Measure the inner bubble element
    var bubbleEl = s.container.querySelector('.bubble-infowindow');
    if (!bubbleEl) return;

    var bubbleWidth = bubbleEl.offsetWidth || 200;
    var bubbleHeight = bubbleEl.offsetHeight || 100;

    // Get the map container's bounding rect to translate map-pixel to page-pixel
    var mapDiv = s.map.getContainer();
    var mapRect = mapDiv ? mapDiv.getBoundingClientRect() : { left: 0, top: 0 };

    // Center horizontally on the point, position above the point
    // 12 = arrow height + small gap
    var left = mapRect.left + pixel.x - bubbleWidth / 2 + offsetX;
    var top = mapRect.top + pixel.y - bubbleHeight - 12 + offsetY;

    s.container.style.left = left + 'px';
    s.container.style.top = top + 'px';
}

// ── Map event binding ───────────────────────────────────────────────

var _MAP_EVENTS = ['moving', 'zooming', 'zoomend', 'resize'];

function _bindMapEvents(mapInstance) {
    _bubbleState._boundUpdate = _updateBubblePosition;
    for (var i = 0; i < _MAP_EVENTS.length; i++) {
        mapInstance.addEventListener(_MAP_EVENTS[i], _bubbleState._boundUpdate);
    }
}

function _unbindMapEvents() {
    if (!_bubbleState.map || !_bubbleState._boundUpdate) return;
    for (var i = 0; i < _MAP_EVENTS.length; i++) {
        try {
            _bubbleState.map.removeEventListener(_MAP_EVENTS[i], _bubbleState._boundUpdate);
        } catch (e) {}
    }
    _bubbleState._boundUpdate = null;
}

// ── Public API ──────────────────────────────────────────────────────

/**
 * Open a custom bubble InfoWindow on the Baidu Map.
 *
 * @param {BMapGL.Point} point      - Map point to anchor to
 * @param {Object}       options
 * @param {string}  [options.title]
 * @param {string}  [options.body]
 * @param {boolean} [options.showClose]
 * @param {string}  [options.extraClass]
 * @param {Object}  [options.offset]    - {x, y} pixel offset from the anchor point
 * @param {Function}[options.onClose]   - Callback invoked when user clicks close button
 * @param {BMapGL.Map}   mapInstance - The Baidu map instance
 */
function openBaiduBubble(point, options, mapInstance) {
    // Close any previously open bubble
    closeBaiduBubble();

    // Also close any native BMapGL InfoWindow that might be open
    try {
        if (mapInstance && typeof mapInstance.closeInfoWindow === 'function') {
            mapInstance.closeInfoWindow();
        }
    } catch (e) {}

    var container = _ensureBubbleContainer();

    // Store state
    _bubbleState.point = point;
    _bubbleState.options = options || {};
    _bubbleState.map = mapInstance;
    _bubbleState.isOpen = true;

    // Render bubble HTML
    container.innerHTML = buildBaiduBubbleHTML(_bubbleState.options);
    container.style.display = 'block';

    // Attach close button handler
    var closeBtn = container.querySelector('[data-bubble-close]');
    if (closeBtn) {
        closeBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            // User-initiated close: fire onClose callback
            var onClose = _bubbleState.options && _bubbleState.options.onClose;
            closeBaiduBubble();
            if (onClose) {
                try { onClose(); } catch (err) {
                    console.warn('Error in bubble onClose callback:', err);
                }
            }
        });
    }

    // Prevent map interactions from bleeding through the bubble
    container.addEventListener('mousedown', function (e) { e.stopPropagation(); });
    container.addEventListener('dblclick', function (e) { e.stopPropagation(); });
    container.addEventListener('wheel', function (e) { e.stopPropagation(); });

    // Bind map events for live position tracking
    _bindMapEvents(mapInstance);

    // Initial position
    _updateBubblePosition();

    console.log('Baidu bubble opened');
}

/**
 * Close the currently open Baidu bubble InfoWindow.
 * Does NOT fire the onClose callback (programmatic close).
 */
function closeBaiduBubble() {
    if (!_bubbleState.isOpen) return;

    _bubbleState.isOpen = false;

    // Remove map event listeners
    _unbindMapEvents();

    // Hide container
    if (_bubbleState.container) {
        _bubbleState.container.style.display = 'none';
        _bubbleState.container.innerHTML = '';
    }

    // Clear state
    _bubbleState.point = null;
    _bubbleState.options = null;
    // Keep .map and .container references for reuse

    console.log('Baidu bubble closed');
}
