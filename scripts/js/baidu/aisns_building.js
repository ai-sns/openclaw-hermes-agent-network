/**
 * Building model manager - integrates video screen
 * Improves performance, error handling, and code structure
 */

// ===== Global variables and config =====
let buildingGroup = null;
let screenContent = null;
let lastTime = 0;
let videoScreenMesh = null;
let buildingBaseMesh = null;
let videoElement = null;
let videoScreenClickHandlerAttached = false;
const SCREEN_OVERLAY_ID = 'ai-sns-video-overlay';
const SCREEN_MENU_ID = 'ai-sns-video-overlay-menu';
let screenOverlayElement = null;
let screenMenuElement = null;
let screenOverlayBaseWidth = null;
let screenOverlayBaseHeight = null;

const SOUND_STORAGE_KEY = 'aisns_video_sound_enabled';
let videoSoundGateEnabled = false;

const screenRaycaster = new THREE.Raycaster();
const screenClickPointer = new THREE.Vector2();
const overlayWorldTarget = new THREE.Vector3();
const overlayProjectedPosition = new THREE.Vector3();
const overlayWorldLeft = new THREE.Vector3();
const overlayWorldRight = new THREE.Vector3();
const overlayProjectedLeft = new THREE.Vector3();
const overlayProjectedRight = new THREE.Vector3();
const OVERLAY_SCALE_RANGE = { min: 0.6, max: 1.8 };
const OVERLAY_VERTICAL_MARGIN = 28;

// Performance config
const PERFORMANCE_CONFIG = {
    TARGET_FPS: 60,
    FRAME_INTERVAL: 1000 / 60 // ~16.67ms
};

const building_position = [121.51810835402695, 31.34035307935309];

// Building config:
const BUILDING_CONFIG = {
    position: [121.51810835402695, 31.34035307935309],
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
        zIndex: 10000,
        boxShadow: '0 6px 18px rgba(0, 0, 0, 0.35)'
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
    about.addEventListener('click', () => {
        try {
            if (typeof open_url === 'function') {
                open_url('https://www.ai-sns.org');
            } else if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                window.electronAPI.openUrl('https://www.ai-sns.org');
            } else {
                window.open('https://www.ai-sns.org', '_blank');
            }
        } catch (e) {
        }
        hideVideoMenu();
    });

    const sound = mkItem('');
    sound.id = `${SCREEN_MENU_ID}-sound`;
    sound.addEventListener('click', () => {
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

// Renderer initialization
const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: "high-performance"
});

renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
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
    if (!videoElement) return;
    const soundEnabled = getStoredSoundEnabled();
    const shouldPlaySound = !!soundEnabled && !!videoSoundGateEnabled;

    try {
        videoElement.muted = !shouldPlaySound;
        if (shouldPlaySound) {
            videoElement.volume = 1;
            const p = videoElement.play();
            if (p && typeof p.catch === 'function') {
                p.catch(() => {
                    // Autoplay with sound may be blocked; ignore here.
                });
            }
        }
    } catch (e) {
    }
}

// Called by map action handler (Square/plaza => true, others => false)
window.setAisnsVideoSoundGate = function (enabled) {
    videoSoundGateEnabled = !!enabled;
    applyVideoSoundPolicy();
};

// ===== Utility class: VideoScreen =====
class VideoScreen extends THREE.Group {
    constructor(width, height, videoSrc) {
        super();

        this.width = width;
        this.height = height;
        this.videoTexture = new THREE.VideoTexture(this._createVideoElement(videoSrc));
        this._createScreen();
        this._createFrame();
    }

    /**
     * Initialize video element
     * @private
     * @param {string} videoSrc - video source
     * @returns {HTMLVideoElement} video element
     */
    _createVideoElement(videoSrc) {
        const video = document.createElement('video');
        Object.assign(video, {
            src: videoSrc,
            loop: true,
            muted: true,
            autoplay: true,
            playsInline: true,
            preload: 'auto',
            crossOrigin: 'anonymous'
        });

        videoElement = video;
        applyVideoSoundPolicy();

        video.addEventListener('canplay', () => {
            video.play().catch(error => {
                console.warn('Video playback failed, waiting for user interaction:', error.message);
                document.addEventListener('click', () => video.play().catch(e => console.error('Video playback still failed after user interaction:', e)), { once: true });
                document.addEventListener('touchstart', () => video.play().catch(e => console.error('Video playback still failed after user interaction:', e)), { once: true });
            });
        });

        return video;
    }

    /**
     * Create screen
     * @private
     */
    _createScreen() {
        const screenGeometry = new THREE.PlaneGeometry(this.width, this.height);
        const screenMaterial = new THREE.MeshBasicMaterial({
            map: this.videoTexture,
            side: THREE.FrontSide
        });

        const screen = new THREE.Mesh(screenGeometry, screenMaterial);
        screen.name = 'video-screen';
        screen.userData.isInteractiveVideoScreen = true;
        videoScreenMesh = screen;
        this.add(screen);
        setupVideoScreenInteraction();
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

        const border = new THREE.Mesh(borderGeometry, borderMaterial);
        border.position.z = -0.0375;
        this.add(border);
    }

    /**
     * Update video texture (if needed)
     */
    update() {
        this.videoTexture.needsUpdate = true;
    }

    /**
     * Dispose resources
     */
    dispose() {
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
function setupVideoScreenInteraction() {
    if (videoScreenClickHandlerAttached || !videoScreenMesh) {
        return;
    }

    if (typeof threeLayer === 'undefined' || !threeLayer || typeof threeLayer.addEventListener !== 'function') {
        return;
    }

    const getMapDimensions = () => {
        if (typeof map !== 'undefined' && map) {
            if (typeof map.getSize === 'function') {
                const size = map.getSize();
                if (size && typeof size.width === 'number' && typeof size.height === 'number') {
                    return { width: size.width, height: size.height };
                }
            }
            if (typeof map.width === 'number' && typeof map.height === 'number') {
                return { width: map.width, height: map.height };
            }
        }

        const fallbackWidth = renderer && renderer.domElement ? renderer.domElement.clientWidth : window.innerWidth;
        const fallbackHeight = renderer && renderer.domElement ? renderer.domElement.clientHeight : window.innerHeight;

        return { width: fallbackWidth, height: fallbackHeight };
    };

    const handleClick = function (event) {
        if (!event || !event.pixel || !videoScreenMesh) {
            return;
        }

        const size = getMapDimensions();
        if (!size.width || !size.height) {
            return;
        }

        screenClickPointer.x = (event.pixel.x / size.width) * 2 - 1;
        screenClickPointer.y = -(event.pixel.y / size.height) * 2 + 1;

        const activeCamera = (this && this.camera) || (threeLayer && threeLayer.camera);
        if (!activeCamera) {
            return;
        }

        screenRaycaster.setFromCamera(screenClickPointer, activeCamera);

        const intersections = screenRaycaster.intersectObject(screenContent || videoScreenMesh, true);
        const hit = intersections.find(intersection => intersection.object && intersection.object.userData && intersection.object.userData.isInteractiveVideoScreen);

        if (hit) {
            alert(1);
        }
    };

    threeLayer.addEventListener('click', handleClick);
    videoScreenClickHandlerAttached = true;
    updateVideoOverlayPosition();
}

function createVideoOverlay() {
    if (screenOverlayElement || document.getElementById(SCREEN_OVERLAY_ID)) {
        return;
    }

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
    const prevTransform = el.style.transform;

    try {
        el.style.visibility = 'hidden';
        el.style.display = 'block';
        el.style.left = '-10000px';
        el.style.top = '-10000px';
        el.style.transform = 'scale(1)';

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
        el.style.transform = prevTransform;
    }
}

function getActiveCamera() {
    if (typeof threeLayer !== 'undefined' && threeLayer && threeLayer.camera) {
        return threeLayer.camera;
    }
    if (typeof camera !== 'undefined' && camera) {
        return camera;
    }
    return null;
}

function updateVideoOverlayPosition() {
    if (!screenOverlayElement) {
        return;
    }

    if (!buildingBaseMesh) {
        screenOverlayElement.style.display = 'none';
        if (screenMenuElement) screenMenuElement.style.display = 'none';
        return;
    }

    const activeCamera = getActiveCamera();
    if (!activeCamera || !renderer) {
        screenOverlayElement.style.display = 'none';
        return;
    }

    ensureOverlayBaseSize();

    const box = new THREE.Box3().setFromObject(buildingBaseMesh);
    if (!box || (typeof box.isEmpty === 'function' && box.isEmpty())) {
        screenOverlayElement.style.display = 'none';
        return;
    }

    const boxCenter = box.getCenter(overlayWorldTarget);
    overlayWorldTarget.set(boxCenter.x, box.max.y, boxCenter.z);
    overlayProjectedPosition.copy(overlayWorldTarget).project(activeCamera);
    if (overlayProjectedPosition.z >= 1) {
        screenOverlayElement.style.display = 'none';
        return;
    }

    const canvasWidth = renderer.domElement.clientWidth;
    const canvasHeight = renderer.domElement.clientHeight;

    const screenX = (overlayProjectedPosition.x * 0.5 + 0.5) * canvasWidth;
    const screenY = (-overlayProjectedPosition.y * 0.5 + 0.5) * canvasHeight;

    screenOverlayElement.style.display = 'block';
    screenOverlayElement.style.transform = 'scale(1)';
    screenOverlayElement.style.left = `${screenX - (screenOverlayBaseWidth / 2)}px`;
    screenOverlayElement.style.top = `${screenY - screenOverlayBaseHeight - OVERLAY_VERTICAL_MARGIN}px`;

    if (screenMenuElement && screenMenuElement.style.display === 'block') {
        updateVideoMenuPosition();
    }
}

const fontLoader = new THREE.FontLoader();

/**
 * Font loader with retry
 * @param {string} url - font file URL
 * @returns {Promise<THREE.Font>}
 */
const loadFontWithRetry = async (url) => {
    const retries = 3;
    const delay = 1000;
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            return await new Promise((resolve, reject) => {
                fontLoader.load(
                    url,
                    resolve,
                    undefined,
                    reject
                );
            });
        } catch (error) {
            console.error(`Font load failed (attempt ${attempt + 1}/${retries}):`, error.message);
            if (attempt === retries - 1) throw new Error(`Font load failed after all retries: ${url}`);
            await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt)));
        }
    }
};

// ===== Building creation =====
function createBuilding(font) {
    const group = new THREE.Group();
    group.add(createBuildingStructure());
    createWindows().forEach(window => group.add(window));
    const videoScreen = createVideoScreen();
    group.add(videoScreen);
    group.add(createBuildingName(font));

    screenContent = videoScreen; // Save reference for later updates

    setupVideoScreenInteraction();

    return group;
}

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

function createWindows() {
    const windows = [];
    const { width, height, depth } = BUILDING_CONFIG.dimensions;
    const { size, spacing, lightOnProbability } = BUILDING_CONFIG.window;
    const windowGeometry = new THREE.PlaneGeometry(size, size);

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

    for (let y = 1; y < height - 0.5; y += spacing) {
        for (let x = -width / 2 + spacing; x < width / 2 - spacing; x += spacing) {
            const material = Math.random() > (1 - lightOnProbability) ? windowMaterials.on : windowMaterials.off;
            const window = new THREE.Mesh(windowGeometry, material);
            window.position.set(x, y, depth / 2 + 0.01);
            window.rotation.y = Math.PI;
            windows.push(window);
        }
    }

    return windows;
}

function createVideoScreen() {
    const { width, height } = BUILDING_CONFIG.screen;
    const { height: buildingHeight, depth } = BUILDING_CONFIG.dimensions;
    const { spacing } = BUILDING_CONFIG.window;

    const videoScreen = new VideoScreen(width, height, 'aisns.webm');
    videoScreen.position.set(0, buildingHeight - spacing - height / 2, depth / 2 + 0.125);

    return videoScreen;
}

function createBuildingName(font) {
    const textGeometry = new THREE.TextGeometry('AI-SNS', {
        font: font,
        size: 0.2,
        height: 0.05,
        curveSegments: 12,
        bevelEnabled: false
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
        setupVideoScreenInteraction();
    } catch (error) {
        console.error("Building model initialization failed:", error);
    }
};

// ===== Animation loop =====
function animatebak(time) {
    requestAnimationFrame(animate);

    const now = performance.now();
    if (now - lastTime > PERFORMANCE_CONFIG.FRAME_INTERVAL) {
        if (screenContent) {
            screenContent.update();
        }
        lastTime = now;
    }

    if (typeof clock !== 'undefined' && typeof mixers !== 'undefined') {
        const delta = clock.getDelta();
        mixers.forEach(mixer => mixer.update(delta));
    }

    if (typeof threeLayer !== 'undefined') {
        threeLayer.update();
    }

    updateVideoOverlayPosition();
}

function animate(time) {
    // alert("in ani");
    requestAnimationFrame(animate);

    const now = performance.now();

    if (now - lastTime > 16) { // Limit to ~60 FPS
        if (screenContent) {
            screenContent.update();
        }
        lastTime = now;
    }

    const delta = clock.getDelta();

    mixers.forEach(mixer => {
        if (mixer) mixer.update(delta);
    })

    threeLayer.update();

    updateVideoOverlayPosition();

    // Anchor status indicator to person_me 3D model head
    if (typeof aimodel_status !== 'undefined' && aimodel_status &&
        typeof aimodel_status.updatePosition === 'function') {
        aimodel_status.updatePosition();
    }

}


// ===== Building loading =====
function load_aisns_building() {
    if (!buildingGroup) {
        console.error("Building model not initialized");
        return;
    }

    try {
        const mesh = buildingGroup;
        const mcpoint = convertCoords(building_position);
        mesh.scale.set(20, 20, 20);
        mesh.rotation.set(Math.PI / 2, Math.PI / 2, 0);

        const geoGroup = new THREE.Group();
        geoGroup.add(mesh);
        geoGroup.position.set(mcpoint.lng, mcpoint.lat, 0);
        if (typeof threeLayer !== 'undefined') {
            threeLayer.add(geoGroup);
            threeLayer.render();
            setupVideoScreenInteraction();
        }

        createVideoOverlay();
        createVideoMenu();
        applyVideoSoundPolicy();

    } catch (error) {
        console.error("Building model loading failed:", error);
    }
}

// ===== Resource cleanup =====
function disposeBuildingResources() {
    if (screenContent) screenContent.dispose();
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
    if (screenOverlayElement) {
        screenOverlayElement.style.display = 'none';
    }
    if (screenMenuElement) {
        screenMenuElement.style.display = 'none';
    }
}

// ===== Window events =====
window.addEventListener('beforeunload', disposeBuildingResources);
window.addEventListener('resize', () => {
    renderer.setSize(window.innerWidth, window.innerHeight);
    updateVideoOverlayPosition();
});

// Start initialization
initializeBuilding();
setTimeout(load_aisns_building, 6000);

function convertCoords(pos) {
    const llPoint = new BMapGL.Point(pos[0], pos[1]);
    return BMapGL.Projection.convertLL2MC(llPoint);
}
