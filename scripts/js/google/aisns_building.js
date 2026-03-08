/**
 * Building model manager - integrates video screen
 * Improves performance, error handling, and code structure
 */

// ===== Global variables and config =====
let buildingGroup = null;
let screenContent = null;
let lastTime = 0;
let buildingBaseMesh = null;

let screenOverlayElement = null;
let screenMenuElement = null;
let screenOverlayBaseWidth = null;
let screenOverlayBaseHeight = null;

let overlayUiInitialized = false;

let projectionOverlayView = null;

const OVERLAY_SCREEN_MARGIN_PX = 28;
const OVERLAY_DEFAULT_VISIBLE = true;

const SCREEN_OVERLAY_ID = 'ai-sns-video-overlay';
const SCREEN_MENU_ID = 'ai-sns-video-overlay-menu';
const SOUND_STORAGE_KEY = 'aisns_video_sound_enabled';
let videoSoundGateEnabled = false;

// Performance config
const PERFORMANCE_CONFIG = {
    TARGET_FPS: 60,
    FRAME_INTERVAL: 1000 / 60, // ~16.67ms
    FONT_RETRY_COUNT: 3,
    FONT_RETRY_DELAY: 1000
};
const building_position = [-122.36195286954631, 37.729593622423355];
// Building config:
const BUILDING_CONFIG = {
    position: [-122.36195286954631, 37.729593622423355],
    dimensions: {
        width: 2,
        height: 3 * 1.25, // Increase height by 25%
        depth: 1.5
    },
    screen: {
        width: 1.75,
        height: 0.875,
        borderThickness: 0.05
    },
    window: {
        size: 0.15,
        spacing: 0.275,
        lightOnProbability: 0.6
    }
};

// Renderer initialization
const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: "high-performance"
});

renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Limit pixel ratio to improve performance
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap; // Better shadow quality
document.body.appendChild(renderer.domElement);

function getStoredSoundEnabled() {
    try {
        const raw = localStorage.getItem(SOUND_STORAGE_KEY);
        if (raw === null || raw === undefined) return false;
        return String(raw) === 'true';
    } catch (e) {
        return false;
    }
}

function setStoredSoundEnabled(enabled) {
    try {
        localStorage.setItem(SOUND_STORAGE_KEY, enabled ? 'true' : 'false');
    } catch (e) {
    }
}

function applyVideoSoundPolicy() {
    try {
        if (!screenContent || !screenContent.video) return;
        const soundEnabled = getStoredSoundEnabled();
        const shouldPlaySound = !!soundEnabled && !!videoSoundGateEnabled;
        screenContent.video.muted = !shouldPlaySound;
        if (shouldPlaySound) {
            screenContent.video.volume = 1;
            const p = screenContent.video.play();
            if (p && typeof p.catch === 'function') {
                p.catch(() => {
                    // Autoplay with sound may be blocked; ignore.
                });
            }
        }
    } catch (e) {
    }
}

window.setAisnsVideoSoundGate = function (enabled) {
    videoSoundGateEnabled = !!enabled;
    applyVideoSoundPolicy();
};

function createVideoOverlay() {
    if (screenOverlayElement || document.getElementById(SCREEN_OVERLAY_ID)) return;
    const overlay = document.createElement('div');
    overlay.id = SCREEN_OVERLAY_ID;
    overlay.textContent = 'More about the video';

    Object.assign(overlay.style, {
        position: 'absolute',
        left: '0px',
        top: '0px',
        transformOrigin: '0 0',
        transform: 'scale(1)',
        padding: '6px 14px',
        background: 'rgba(0, 0, 0, 0.65)',
        color: '#ffffff',
        fontSize: '14px',
        lineHeight: '1.4',
        borderRadius: '6px',
        cursor: 'pointer',
        zIndex: 2147483647,
        pointerEvents: 'auto',
        display: 'none',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        boxShadow: '0 2px 6px rgba(0, 0, 0, 0.25)'
    });

    overlay.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleVideoMenu();
    });
    document.body.appendChild(overlay);
    screenOverlayElement = overlay;
    ensureOverlayBaseSize();
}

function ensureOverlayBaseSize() {
    if (!screenOverlayElement) return;
    if (screenOverlayBaseWidth && screenOverlayBaseHeight && screenOverlayBaseWidth > 1 && screenOverlayBaseHeight > 1) return;

    const el = screenOverlayElement;
    const prevDisplay = el.style.display;
    const prevVisibility = el.style.visibility;
    const prevLeft = el.style.left;
    const prevTop = el.style.top;

    try {
        el.style.visibility = 'hidden';
        el.style.display = 'block';
        el.style.left = '-10000px';
        el.style.top = '-10000px';
        const rect = el.getBoundingClientRect();
        const w = (rect.width && rect.width > 0) ? rect.width : (el.offsetWidth || 1);
        const h = (rect.height && rect.height > 0) ? rect.height : (el.offsetHeight || 1);
        screenOverlayBaseWidth = w;
        screenOverlayBaseHeight = h;
    } catch (e) {
    } finally {
        el.style.display = prevDisplay;
        el.style.visibility = prevVisibility;
        el.style.left = prevLeft;
        el.style.top = prevTop;
    }
}

function createVideoMenu() {
    if (screenMenuElement || document.getElementById(SCREEN_MENU_ID)) return;
    const menu = document.createElement('div');
    menu.id = SCREEN_MENU_ID;
    Object.assign(menu.style, {
        position: 'absolute',
        left: '0px',
        top: '0px',
        display: 'none',
        minWidth: '180px',
        padding: '6px',
        background: 'rgba(0, 0, 0, 0.80)',
        color: '#ffffff',
        borderRadius: '8px',
        zIndex: 2147483647,
        pointerEvents: 'auto',
        boxShadow: '0 6px 18px rgba(0, 0, 0, 0.35)'
    });

    menu.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    const mkItem = (label) => {
        const item = document.createElement('div');
        item.textContent = label;
        Object.assign(item.style, {
            padding: '8px 10px',
            borderRadius: '6px',
            cursor: 'pointer',
            userSelect: 'none'
        });
        item.addEventListener('mouseenter', () => {
            item.style.background = 'rgba(255,255,255,0.12)';
        });
        item.addEventListener('mouseleave', () => {
            item.style.background = 'transparent';
        });
        return item;
    };

    const about = mkItem('Video details');
    about.addEventListener('click', (e) => {
        e.stopPropagation();
        const url = 'https://www.ai-sns.org';
        let opened = false;

        try {
            if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                window.electronAPI.openUrl(url);
                opened = true;
            }
        } catch (err) {
        }

        if (!opened) {
            try {
                let parentApi = null;
                try {
                    parentApi = window.parent && window.parent.electronAPI;
                } catch (err) {
                    parentApi = null;
                }
                if (parentApi && typeof parentApi.openUrl === 'function') {
                    parentApi.openUrl(url);
                    opened = true;
                }
            } catch (err) {
            }
        }

        if (!opened) {
            try {
                if (typeof open_url === 'function') {
                    open_url(url);
                    opened = true;
                }
            } catch (err) {
            }
        }

        if (!opened) {
            try {
                window.open(url, '_blank', 'noopener,noreferrer');
                opened = true;
            } catch (err) {
            }
        }

        if (!opened) {
            try {
                window.location.href = url;
            } catch (err) {
            }
        }

        hideVideoMenu();
    });

    const sound = mkItem('');
    sound.id = `${SCREEN_MENU_ID}-sound`;
    sound.addEventListener('click', (e) => {
        e.stopPropagation();
        const next = !getStoredSoundEnabled();
        setStoredSoundEnabled(next);
        applyVideoSoundPolicy();
        updateVideoMenuLabels();
    });

    menu.appendChild(about);
    menu.appendChild(sound);
    document.body.appendChild(menu);
    screenMenuElement = menu;

    document.addEventListener('click', () => {
        hideVideoMenu();
    });

    updateVideoMenuLabels();
}

function updateVideoMenuLabels() {
    const soundItem = document.getElementById(`${SCREEN_MENU_ID}-sound`);
    if (!soundItem) return;
    soundItem.textContent = getStoredSoundEnabled() ? 'Turn sound off' : 'Turn sound on';
}

function toggleVideoMenu() {
    if (!screenMenuElement) return;
    const isVisible = screenMenuElement.style.display === 'block';
    screenMenuElement.style.display = isVisible ? 'none' : 'block';
    if (!isVisible) {
        updateVideoMenuLabels();
        updateVideoMenuPosition();
    }
}

function hideVideoMenu() {
    if (!screenMenuElement) return;
    screenMenuElement.style.display = 'none';
}

function updateVideoMenuPosition() {
    if (!screenMenuElement || !screenOverlayElement) return;
    const overlayRect = screenOverlayElement.getBoundingClientRect();
    screenMenuElement.style.left = `${overlayRect.left}px`;
    screenMenuElement.style.top = `${overlayRect.bottom + 6}px`;
}

function getBuildingBottomRightPixels(projection) {
    try {
        const base = new google.maps.LatLng(BUILDING_CONFIG.position[1], BUILDING_CONFIG.position[0]);
        if (google.maps.geometry && google.maps.geometry.spherical && typeof google.maps.geometry.spherical.computeOffset === 'function') {
            const east = google.maps.geometry.spherical.computeOffset(base, 20, 90);
            const south = google.maps.geometry.spherical.computeOffset(base, 20, 180);
            const se = google.maps.geometry.spherical.computeOffset(base, 28, 135);

            const p0 = projection.fromLatLngToDivPixel(base);
            const p1 = projection.fromLatLngToDivPixel(east);
            const p2 = projection.fromLatLngToDivPixel(south);
            const p3 = projection.fromLatLngToDivPixel(se);

            const xs = [p0, p1, p2, p3].filter(Boolean).map(p => p.x);
            const ys = [p0, p1, p2, p3].filter(Boolean).map(p => p.y);
            if (xs.length && ys.length) {
                return { x: Math.max(...xs), y: Math.max(...ys) };
            }
        }

        const p = projection.fromLatLngToDivPixel(base);
        if (!p) return null;
        return { x: p.x, y: p.y };
    } catch (e) {
        return null;
    }
}

function getOverlayCameraSafe() {
    try {
        if (typeof overlay === 'undefined' || !overlay) return null;

        const candidates = [
            overlay.camera,
            overlay._camera,
            overlay.three && overlay.three.camera,
            overlay.renderer && overlay.renderer.camera,
            overlay.scene && overlay.scene.camera
        ];

        for (const c of candidates) {
            if (c && typeof c === 'object' && (c.isCamera || (c.type && String(c.type).toLowerCase().includes('camera')))) {
                return c;
            }
        }

        if (typeof overlay.getCamera === 'function') {
            const c = overlay.getCamera();
            if (c && (c.isCamera || (c.type && String(c.type).toLowerCase().includes('camera')))) return c;
        }
    } catch (e) {
        return null;
    }

    return null;
}

function updateVideoOverlayPosition() {
    if (!screenOverlayElement) return;
    if (!buildingGroup) {
        screenOverlayElement.style.display = 'none';
        if (screenMenuElement) screenMenuElement.style.display = 'none';
        return;
    }

    if (!map || !window.google || !google.maps) {
        screenOverlayElement.style.display = 'none';
        return;
    }

    if (!projectionOverlayView) {
        try {
            projectionOverlayView = new google.maps.OverlayView();
            projectionOverlayView.onAdd = () => {
            };
            projectionOverlayView.draw = () => {
            };
            projectionOverlayView.onRemove = () => {
            };
            projectionOverlayView.setMap(map);
        } catch (e) {
            projectionOverlayView = null;
        }
    }

    const projection = projectionOverlayView && typeof projectionOverlayView.getProjection === 'function'
        ? projectionOverlayView.getProjection()
        : null;
    if (!projection || typeof projection.fromLatLngToDivPixel !== 'function') {
        // Projection not ready yet.
        return;
    }

    const mapDiv = map.getDiv && map.getDiv();
    const mapRect = mapDiv && mapDiv.getBoundingClientRect ? mapDiv.getBoundingClientRect() : null;
    if (!mapRect) return;

    ensureOverlayBaseSize();

    const camera = getOverlayCameraSafe();
    if (camera && typeof THREE !== 'undefined' && THREE.Box3) {
        try {
            const anchorObject = buildingBaseMesh || buildingGroup;
            const box = new THREE.Box3().setFromObject(anchorObject);
            if (!box || (typeof box.isEmpty === 'function' && box.isEmpty())) {
                screenOverlayElement.style.display = 'none';
                return;
            }

            const center = new THREE.Vector3();
            box.getCenter(center);
            const worldAnchor = new THREE.Vector3(center.x, box.max.y, center.z);

            const projected = worldAnchor.clone().project(camera);
            if (typeof projected.z === 'number' && projected.z >= 1) {
                screenOverlayElement.style.display = 'none';
                return;
            }

            ensureOverlayBaseSize();

            const w = mapRect.width || (mapDiv && mapDiv.clientWidth) || window.innerWidth;
            const h = mapRect.height || (mapDiv && mapDiv.clientHeight) || window.innerHeight;

            const screenX = (projected.x * 0.5 + 0.5) * w;
            const screenY = (-projected.y * 0.5 + 0.5) * h;

            const left = mapRect.left + screenX - (screenOverlayBaseWidth / 2);
            const top = mapRect.top + screenY - screenOverlayBaseHeight - OVERLAY_SCREEN_MARGIN_PX;

            screenOverlayElement.style.display = OVERLAY_DEFAULT_VISIBLE ? 'block' : 'none';
            screenOverlayElement.style.left = `${left}px`;
            screenOverlayElement.style.top = `${top}px`;

            if (screenMenuElement && screenMenuElement.style.display === 'block') {
                updateVideoMenuPosition();
            }

            return;
        } catch (e) {
            // Fall back to 2D projection
        }
    }

    const pixel = getBuildingBottomRightPixels(projection);
    if (!pixel) return;

    ensureOverlayBaseSize();

    // Bottom-right of the building
    const offsetX = 6;
    const offsetY = 6;
    let left = mapRect.left + pixel.x + offsetX;
    let top = mapRect.top + pixel.y + offsetY;

    screenOverlayElement.style.display = 'block';
    screenOverlayElement.style.left = `${left}px`;
    screenOverlayElement.style.top = `${top}px`;

    if (screenMenuElement && screenMenuElement.style.display === 'block') {
        updateVideoMenuPosition();
    }
}

// ===== Utility class: VideoScreen =====
class VideoScreen extends THREE.Group {
    /**
     * Constructor
     * @param {number} width - screen width
     * @param {number} height - screen height
     * @param {string} videoSrc - video source URL
     */
    constructor(width, height, videoSrc) {
        super();

        this.width = width;
        this.height = height;
        this.video = null;
        this.videoTexture = null;

        this._initializeVideo(videoSrc);
        this._createScreen();
        this._createFrame();
    }

    /**
     * Initialize video element
     * @private
     */
    _initializeVideo(videoSrc) {
        this.video = document.createElement('video');

        // Video configuration
        Object.assign(this.video, {
            src: videoSrc,
            loop: true,
            muted: true,
            autoplay: true,
            playsInline: true,
            preload: 'auto',
            crossOrigin: 'anonymous'
        });

        // Create video texture
        this.videoTexture = new THREE.VideoTexture(this.video);
        this.videoTexture.minFilter = THREE.LinearFilter;
        this.videoTexture.magFilter = THREE.LinearFilter;
        this.videoTexture.format = THREE.RGBFormat;
        this.videoTexture.flipY = true; // Fix upside-down video

        // Handle video playback
        this._handleVideoPlayback();
    }

    /**
     * Handle video playback logic
     * @private
     */
    async _handleVideoPlayback() {
        try {
            // Wait for video metadata
            await new Promise((resolve, reject) => {
                this.video.addEventListener('loadedmetadata', resolve);
                this.video.addEventListener('error', reject);
                this.video.load();
            });

            // Try autoplay
            await this.video.play();
            console.log('Video autoplay successful');

        } catch (error) {
            console.warn('Video autoplay failed, waiting for user interaction:', error.message);

            // Add user interaction listener
            this._addUserInteractionListener();
        }
    }

    /**
     * Add user interaction listener to start playback
     * @private
     */
    _addUserInteractionListener() {
        const playVideo = async () => {
            try {
                await this.video.play();
                console.log('User interaction successful, video playing');
                document.removeEventListener('click', playVideo);
                document.removeEventListener('touchstart', playVideo);
            } catch (error) {
                console.error('User interaction failed to play video:', error);
            }
        };

        document.addEventListener('click', playVideo, { once: true });
        document.addEventListener('touchstart', playVideo, { once: true });
    }

    /**
     * Create screen
     * @private
     */
    _createScreen() {
        const screenGeometry = new THREE.PlaneGeometry(this.width, this.height);
        const screenMaterial = new THREE.MeshBasicMaterial({
            map: this.videoTexture,
            side: THREE.FrontSide,
            transparent: false
        });

        this.screen = new THREE.Mesh(screenGeometry, screenMaterial);
        this.add(this.screen);
    }

    /**
     * Create screen frame
     * @private
     */
    _createFrame() {
        const borderThickness = BUILDING_CONFIG.screen.borderThickness;
        const borderGeometry = new THREE.BoxGeometry(
            this.width + borderThickness,
            this.height + borderThickness,
            0.025
        );

        const borderMaterial = new THREE.MeshStandardMaterial({
            color: 0x333333,
            roughness: 0.8,
            metalness: 0.2
        });

        this.border = new THREE.Mesh(borderGeometry, borderMaterial);
        this.border.position.z = -0.0375;
        this.add(this.border);
    }

    /**
     * Update video texture (if needed)
     */
    update() {
        // VideoTexture updates automatically; keep this method for API consistency
        if (this.video && this.video.readyState >= this.video.HAVE_CURRENT_DATA) {
            this.videoTexture.needsUpdate = true;
        }
    }

    /**
     * Dispose resources
     */
    dispose() {
        if (this.video) {
            this.video.pause();
            this.video.src = '';
            this.video.load();
        }

        if (this.videoTexture) {
            this.videoTexture.dispose();
        }

        // Dispose geometry and materials
        this.traverse((child) => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(material => material.dispose());
                } else {
                    child.material.dispose();
                }
            }
        });
    }
}

// ===== Font loader =====
const fontLoader = new THREE.FontLoader();

/**
 * Font loader with retry
 * @param {string} url - font file URL
 * @param {number} retries - retry count
 * @param {number} delay - retry delay
 * @returns {Promise<THREE.Font>}
 */
const loadFontWithRetry = async (url, retries = PERFORMANCE_CONFIG.FONT_RETRY_COUNT, delay = PERFORMANCE_CONFIG.FONT_RETRY_DELAY) => {
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            return await new Promise((resolve, reject) => {
                fontLoader.load(
                    url,
                    resolve,
                    undefined, // onProgress
                    reject
                );
            });
        } catch (error) {
            const isLastAttempt = attempt === retries - 1;
            console.error(`Font loading failed (attempt ${attempt + 1}/${retries}):`, error.message);

            if (isLastAttempt) {
                throw new Error(`Font loading failed: ${url}`);
            }

            // Exponential backoff
            await new Promise(resolve => setTimeout(resolve, delay));
            delay *= 2;
        }
    }
};

// ===== Building creation =====
/**
 * Create building model
 * @param {THREE.Font} font - loaded font
 * @returns {THREE.Group} building group
 */
function createBuilding(font) {
    const group = new THREE.Group();
    console.log(1);

    // Create main building
    const building = createBuildingStructure();
    group.add(building);
    console.log(12);
    // Create windows
    const windows = createWindows();
    windows.forEach(window => group.add(window));
    console.log(13);
    // Create video screen (replaces the old billboard)
    const videoScreen = createVideoScreen();
    group.add(videoScreen);
    console.log(14);
    // Create building name
    const nameText = createBuildingName(font);
    group.add(nameText);
    console.log(15);
    return group;
}

/**
 * Create main building structure
 * @returns {THREE.Mesh}
 */
function createBuildingStructure() {
    const { width, height, depth } = BUILDING_CONFIG.dimensions;

    const geometry = new THREE.BoxGeometry(width, height, depth);
    const material = new THREE.MeshStandardMaterial({
        color: 0xe0e0e0,
        roughness: 0.5,
        metalness: 0.1
    });

    const building = new THREE.Mesh(geometry, material);
    buildingBaseMesh = building;
    building.position.y = height / 2;
    building.castShadow = true;
    building.receiveShadow = true;

    return building;
}

/**
 * Create windows
 * @returns {THREE.Mesh[]}
 */
function createWindows() {
    const windows = [];
    const { width, height, depth } = BUILDING_CONFIG.dimensions;
    const { size, spacing, lightOnProbability } = BUILDING_CONFIG.window;

    const windowGeometry = new THREE.PlaneGeometry(size, size);

    // Window materials
    const windowMaterials = {
        on: new THREE.MeshStandardMaterial({
            color: 0x333355,
            emissive: 0x111122,
            emissiveIntensity: 0.6,
            side: THREE.DoubleSide
        }),
        off: new THREE.MeshStandardMaterial({
            color: 0x334455,
            emissive: 0x000000,
            side: THREE.DoubleSide
        })
    };

    // Generate window grid
    for (let y = 1; y < height - 0.5; y += spacing) {
        for (let x = -width / 2 + spacing; x < width / 2 - spacing; x += spacing) {
            const isLightOn = Math.random() > (1 - lightOnProbability);
            const material = isLightOn ? windowMaterials.on : windowMaterials.off;

            const window = new THREE.Mesh(windowGeometry, material);
            window.position.set(x, y, depth / 2 + 0.01);
            window.rotation.y = Math.PI;

            windows.push(window);
        }
    }

    return windows;
}

/**
 * Create video screen
 * @returns {VideoScreen}
 */
function createVideoScreen() {
    const { width, height } = BUILDING_CONFIG.screen;
    const { height: buildingHeight, depth } = BUILDING_CONFIG.dimensions;
    const { spacing } = BUILDING_CONFIG.window;

    const videoScreen = new VideoScreen(width, height, 'cjrok2.webm');

    // Position the screen
    videoScreen.position.set(
        0,
        buildingHeight - spacing - height / 2,
        depth / 2 + 0.125
    );

    // Save reference for later updates
    screenContent = videoScreen;

    applyVideoSoundPolicy();

    return videoScreen;
}

/**
 * Create building name text
 * @param {THREE.Font} font - font
 * @returns {THREE.Mesh}
 */
function createBuildingName(font) {
    const textGeometry = new THREE.TextGeometry('AI-SNS', {
        font: font,
        size: 0.2,
        height: 0.05,
        curveSegments: 12,
        bevelEnabled: false // Disable bevel to improve performance
    });

    textGeometry.computeBoundingBox();
    const textWidth = textGeometry.boundingBox.max.x - textGeometry.boundingBox.min.x;

    const textMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color(20 / 255, 110 / 255, 190 / 255)
    });

    const textMesh = new THREE.Mesh(textGeometry, textMaterial);
    textMesh.position.set(
        -textWidth / 2,
        BUILDING_CONFIG.dimensions.height,
        BUILDING_CONFIG.dimensions.depth / 2 + 0.1
    );

    return textMesh;
}

// ===== Initialization =====
/**
 * Initialize building model
 */
const initializeBuilding = async () => {
    try {
        console.log('Loading building model...');

        const font = await loadFontWithRetry('js/helvetiker_bold.typeface.json');
        buildingGroup = createBuilding(font);

        console.log("AI-SNS building model initialized");

        // Update model load status
        if (typeof modelLoadStatus !== 'undefined') {
            modelLoadStatus.building = true;
            checkAnimationStart();
        }

    } catch (error) {
        console.error("Building model initialization failed:", error);
        // Error recovery logic can be added here
    }
};

// ===== Animation loop =====
/**
 * Optimized animation loop
 * @param {number} time - current timestamp
 */
function animate(time) {
    requestAnimationFrame(animate);

    // Check model load status (allow 'failed' status to pass through so
    // successfully loaded models still render when others fail to load)
    if (typeof modelLoadStatus !== 'undefined' &&
        (!modelLoadStatus.building || !modelLoadStatus.house ||
         !modelLoadStatus.girl || !modelLoadStatus.boy)) {
        return;
    }

    const now = performance.now();

    // FPS limiting
    if (now - lastTime > PERFORMANCE_CONFIG.FRAME_INTERVAL) {
        // Update video screen
        if (screenContent && typeof screenContent.update === 'function') {
            screenContent.update();
        }

        lastTime = now;
    }

    // Update animation mixers
    if (typeof clock !== 'undefined' && typeof mixers !== 'undefined') {
        const delta = clock.getDelta();

        mixers.forEach(mixer => {
            if (mixer && typeof mixer.update === 'function') {
                mixer.update(delta);
            }
        });
    }

    // Request redraw
    if (typeof overlay !== 'undefined' && overlay.requestRedraw) {
        overlay.requestRedraw();
    }

    if (overlayUiInitialized) {
        updateVideoOverlayPosition();
    }

    // Anchor status indicator to person_me 3D model head
    if (typeof aimodel_status !== 'undefined' && aimodel_status &&
        typeof aimodel_status.updatePosition === 'function') {
        aimodel_status.updatePosition();
    }
}

// ===== Building loading =====
/**
 * Load building model into the scene
 */
function load_aisns_building() {
    if (!buildingGroup) {
        console.error("Building model not initialized");
        return;
    }

    try {
        const mesh = buildingGroup;
        mesh.scale.setScalar(60); // setScalar is more concise

        // Set building position
        const coordinates = {
            lng: BUILDING_CONFIG.position[0],
            lat: BUILDING_CONFIG.position[1],
        };

        if (typeof overlay !== 'undefined' && overlay.latLngAltitudeToVector3) {
            overlay.latLngAltitudeToVector3(coordinates, mesh.position);
            console.log("Building model position:", mesh.position);

            overlay.scene.add(mesh);
            console.log("AI-SNS building model added to scene");

            try {
                if (!mesh.userData) mesh.userData = {};
                mesh.userData.geo = {
                    lat: Number(coordinates.lat),
                    lng: Number(coordinates.lng),
                    altitude: 0,
                };
                if (typeof geoBoundObjects !== 'undefined' && geoBoundObjects && typeof geoBoundObjects.add === 'function') {
                    geoBoundObjects.add(mesh);
                }
            } catch (e) {
            }

            try {
                if (map && window.google && google.maps && google.maps.event && typeof google.maps.event.addListenerOnce === 'function') {
                    google.maps.event.addListenerOnce(map, 'idle', () => {
                        if (overlayUiInitialized) {
                            updateVideoOverlayPosition();
                            return;
                        }
                        overlayUiInitialized = true;
                        createVideoOverlay();
                        createVideoMenu();
                        applyVideoSoundPolicy();
                        updateVideoOverlayPosition();

                        try {
                            map.addListener('idle', () => updateVideoOverlayPosition());
                            map.addListener('zoom_changed', () => updateVideoOverlayPosition());
                            map.addListener('drag', () => updateVideoOverlayPosition());
                            map.addListener('heading_changed', () => updateVideoOverlayPosition());
                            map.addListener('tilt_changed', () => updateVideoOverlayPosition());
                        } catch (e) {
                        }
                    });
                } else {
                    // Fallback: show overlay after a short delay.
                    if (!overlayUiInitialized) {
                        overlayUiInitialized = true;
                        setTimeout(() => {
                            createVideoOverlay();
                            createVideoMenu();
                            applyVideoSoundPolicy();
                            updateVideoOverlayPosition();
                        }, 800);
                    }
                }
            } catch (e) {
            }
        } else {
            console.error("Overlay object not defined or missing necessary method");
        }

    } catch (error) {
        console.error("Building model loading failed:", error);
    }
}

// ===== Resource cleanup =====
/**
 * Dispose building model resources
 */
function disposeBuildingResources() {
    if (screenContent && typeof screenContent.dispose === 'function') {
        screenContent.dispose();
    }

    if (buildingGroup) {
        buildingGroup.traverse((child) => {
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(material => material.dispose());
                } else {
                    child.material.dispose();
                }
            }
        });
    }
}

// ===== Window events =====
window.addEventListener('beforeunload', disposeBuildingResources);
window.addEventListener('resize', () => {
    renderer.setSize(window.innerWidth, window.innerHeight);
    updateVideoOverlayPosition();
});

// ===== Start =====
initializeBuilding();
setTimeout(load_aisns_building, 6000);
