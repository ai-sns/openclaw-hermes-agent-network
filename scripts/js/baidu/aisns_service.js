if (!map) throw new Error('Baidu map instance is not initialized');

// Layer manager
const layerManager = {
    groundOverlay: null,
    threeLayers: new Map(),
    overlays: [],
    views: new Map()  // Store mapvgl.View instances
};

/* 1. Ground overlay initialization */
function initGroundOverlay() {
    // const pStart = new BMapGL.Point(116.22749734234506, 40.00624462450565);
    // const pEnd = new BMapGL.Point(116.24508640812037, 40.03867303424458);
    const pStart = new BMapGL.Point(-122.40210571869962, 37.55816843366316);
    const pEnd = new BMapGL.Point(-122.43508166111967, 37.57643015650198);
    const bounds = new BMapGL.Bounds(
        new BMapGL.Point(Math.min(pStart.lng, pEnd.lng), Math.min(pStart.lat, pEnd.lat)),
        new BMapGL.Point(Math.max(pStart.lng, pEnd.lng), Math.max(pStart.lat, pEnd.lat))
    );
    layerManager.groundOverlay = new BMapGL.GroundOverlay(bounds, {
        type: 'image',
        url: 'shouhuimap.png',
        opacity: 1
    });
    map.addOverlay(layerManager.groundOverlay);
    layerManager.overlays.push(layerManager.groundOverlay);
}

/* 2. Centralized 3D model configuration */
let modelConfigs;

function initModelConfigs() {
    modelConfigs = [
        {
            id: 'mainModel',
            layerId: 'mainLayer',
            position: [103.86335829551814, 1.2847964346121146],
            modelUrl: 'aisnsbuilding.glb',
            scale: 0.02,
            rotation: {x: Math.PI / 2}
        },
        {
            id: 'towerModel',
            layerId: 'mainLayer',
            position: [116.01984538680082, 40.35719706363071],
            modelUrl: 'chinese_tower.glb',
            scale: 24,
            rotation: {x: Math.PI / 2}
        }
    ];
}

/* 3. Reusable model loader */
const facility_gltfLoader = new mapvgl.THREELoader.GLTFLoader();

// Active place model (loaded from places.url_3d)
let __sns_active_place_model = null;
let __sns_active_place_model_url = '';

function __snsDisposeThreeObject(obj) {
    try {
        if (!obj) return;
        obj.traverse((child) => {
            if (!child) return;
            try {
                if (child.geometry && typeof child.geometry.dispose === 'function') {
                    child.geometry.dispose();
                }
            } catch (e) {
            }
            try {
                if (child.material) {
                    const mats = Array.isArray(child.material) ? child.material : [child.material];
                    mats.forEach((m) => {
                        if (!m) return;
                        try {
                            if (m.map && typeof m.map.dispose === 'function') m.map.dispose();
                        } catch (e) {
                        }
                        try {
                            if (typeof m.dispose === 'function') m.dispose();
                        } catch (e) {
                        }
                    });
                }
            } catch (e) {
            }
        });
    } catch (e) {
    }
}

function __snsRemoveActivePlaceModel() {
    try {
        if (__sns_active_place_model && typeof threeLayer !== 'undefined' && threeLayer) {
            try {
                threeLayer.remove(__sns_active_place_model);
            } catch (e) {
                // fallback: remove from scene directly
                try {
                    if (threeLayer.scene) {
                        threeLayer.scene.remove(__sns_active_place_model);
                    }
                } catch (e2) {
                }
            }
            __snsDisposeThreeObject(__sns_active_place_model);
            try {
                threeLayer.render();
            } catch (e) {
            }
        }
    } catch (e) {
    }
    __sns_active_place_model = null;
    __sns_active_place_model_url = '';
}

function __snsSetActivePlaceModel(url3d, placePosition) {
    const nextUrl = (url3d && typeof url3d === 'string') ? url3d.trim() : '';
    if (nextUrl === __sns_active_place_model_url) {
        return;
    }

    const modelParams = (typeof parseModelParamsFromWebUrl === 'function')
        ? (parseModelParamsFromWebUrl(nextUrl) || {
            rotationX: 0,
            rotationY: 0,
            rotationZ: 0,
            altitude: 0,
            scaleMultiplier: 1,
            animationIndex: 0
        })
        : {
            rotationX: 0,
            rotationY: 0,
            rotationZ: 0,
            altitude: 0,
            scaleMultiplier: 1,
            animationIndex: 0
        };

    __snsRemoveActivePlaceModel();

    if (!nextUrl) {
        return;
    }

    if (typeof threeLayer === 'undefined' || !threeLayer) {
        console.warn('[snsPlaceModel] threeLayer is not initialized; skip model load');
        return;
    }

    try {
        facility_gltfLoader.load(
            nextUrl,
            function (obj) {
                try {
                    const model = obj && obj.scene ? obj.scene : null;
                    if (!model) {
                        console.warn('[snsPlaceModel] GLTF loaded but scene is empty:', nextUrl);
                        return;
                    }

                    // Place at the place coordinates (fallback to current map center)
                    let centerLng = null;
                    let centerLat = null;
                    try {
                        const rawPos = (placePosition && placePosition.place_position) ? placePosition.place_position : placePosition;
                        if (Array.isArray(rawPos) && rawPos.length >= 2) {
                            centerLng = rawPos[0];
                            centerLat = rawPos[1];
                        } else if (rawPos && typeof rawPos === 'object') {
                            centerLng = (rawPos.lng !== undefined) ? rawPos.lng : ((rawPos.lon !== undefined) ? rawPos.lon : null);
                            centerLat = (rawPos.lat !== undefined) ? rawPos.lat : null;
                        }
                    } catch (e) {
                    }

                    if (!Number.isFinite(Number(centerLng)) || !Number.isFinite(Number(centerLat))) {
                        try {
                            const c = (typeof map !== 'undefined' && map && typeof map.getCenter === 'function') ? map.getCenter() : null;
                            if (c) {
                                centerLng = (c.lng !== undefined && c.lng !== null) ? c.lng : (typeof c.getLng === 'function' ? c.getLng() : null);
                                centerLat = (c.lat !== undefined && c.lat !== null) ? c.lat : (typeof c.getLat === 'function' ? c.getLat() : null);
                            }
                        } catch (e) {
                        }
                    }

                    if (!Number.isFinite(Number(centerLng)) || !Number.isFinite(Number(centerLat))) {
                        console.warn('[snsPlaceModel] map center not available; skip positioning');
                        return;
                    }

                    const mcpoint = convertCoords([Number(centerLng), Number(centerLat)]);

                    // Scale model to a reasonable size (best-effort)
                    try {
                        const box = new THREE.Box3().setFromObject(model);
                        const size = box.getSize(new THREE.Vector3());
                        const height = size && size.y ? size.y : 0;
                        if (height > 0) {
                            const desiredHeight = 120;
                            const scale = desiredHeight / height;
                            model.scale.set(scale, scale, scale);
                        }

                        if (modelParams && Number.isFinite(Number(modelParams.scaleMultiplier))) {
                            const k = Number(modelParams.scaleMultiplier) || 1;
                            model.scale.set(model.scale.x * k, model.scale.y * k, model.scale.z * k);
                        }
                    } catch (e) {
                    }

                    try {
                        if (modelParams) {
                            const rotX = Number(modelParams.rotationX);
                            model.rotation.x += THREE.MathUtils.degToRad((Number.isFinite(rotX) ? rotX : 0) + 90);
                            model.rotation.y += THREE.MathUtils.degToRad(Number(modelParams.rotationY) || 0);
                            model.rotation.z += THREE.MathUtils.degToRad(Number(modelParams.rotationZ) || 0);
                        }
                    } catch (e) {
                    }

                    const geoGroup = new THREE.Group();
                    geoGroup.add(model);

                    const altitude = (modelParams && Number.isFinite(Number(modelParams.altitude)))
                        ? Number(modelParams.altitude)
                        : 0;
                    geoGroup.position.set(mcpoint.lng, mcpoint.lat, altitude);
                    geoGroup.name = 'snsPlaceModel';

                    threeLayer.add(geoGroup);
                    threeLayer.render();

                    __sns_active_place_model = geoGroup;
                    __sns_active_place_model_url = nextUrl;
                } catch (e) {
                    console.warn('[snsPlaceModel] load callback failed:', e);
                }
            },
            undefined,
            function (error) {
                console.warn('[snsPlaceModel] Model load failed:', error);
            }
        );
    } catch (e) {
        console.warn('[snsPlaceModel] Model load failed:', e);
    }
}

try {
    if (typeof window !== 'undefined') {
        window.__snsSetActivePlaceModel = __snsSetActivePlaceModel;
    }
} catch (e) {
}

/**
 * Load facility model
 * @param {mapvgl.ThreeLayer} threeLayer - ThreeLayer instance
 * @param {Object} config - model config
 */
//todo relationship with loadModel in map_common
function loadFacilityModel(threeLayer, config) {
    facility_gltfLoader.load(
        config.modelUrl,
        function (obj) {
            const model = obj.scene;
            const mcpoint = convertCoords(config.position);

            // Set model position/rotation/scale
            model.position.set(0, 0, 0);
            model.scale.set(config.scale, config.scale, config.scale);
            if (config.rotation) {
                model.rotation.x = config.rotation.x || 0;
                model.rotation.y = config.rotation.y || 0;
                model.rotation.z = config.rotation.z || 0;
            }

            const geoGroup = new THREE.Group();
            geoGroup.add(model);
            geoGroup.position.set(mcpoint.lng, mcpoint.lat, 0);
            geoGroup.name = config.id;

            threeLayer.add(geoGroup);
            threeLayer.render();
        },
        undefined,
        error => console.error(`Model load failed: ${config.modelUrl}`, error)
    );
}


/**
 * Load cube model
 * @param {mapvgl.ThreeLayer} threeLayer - ThreeLayer instance
 */
function loadCubeModel(threeLayer) {
    const texture = new THREE.TextureLoader().load(
        'aisnslayer3d.png',
        () => console.log('Cube texture loaded successfully'),
        undefined,
        error => console.error('Failed to load cube texture:', error)
    );
    texture.minFilter = THREE.LinearFilter;

    const material = new THREE.MeshPhongMaterial({
        transparent: true,
        depthTest: true,
        map: texture,
        opacity: 1
    });

    const geometry = new THREE.BoxGeometry(100, 100, 100);
    const cube = new THREE.Mesh(geometry, material);

    // const mcpoint = convertCoords([116.19042703542924, 39.97619992566233]);

    const mcpoint = convertCoords([-122.47283866789105, 37.530317234458025]);
    cube.position.set(mcpoint.lng, mcpoint.lat, 50);

    const group = new THREE.Group();
    group.add(cube);
    threeLayer.add(group);
    threeLayer.render();
}

/* 4. Main function to create ThreeLayer */
function load_all_facility(layerId) {
    if (layerManager.threeLayers.has(layerId)) return;

    // Ensure threeLayer and view are initialized
    if (typeof threeLayer === 'undefined' || !threeLayer) {
        console.error('threeLayer is not initialized');
        return;
    }
    if (typeof view === 'undefined' || !view) {
        console.error('view is not initialized');
        return;
    }

    loadCubeModel(threeLayer);
    initModelConfigs(); // Initialize model configs
    modelConfigs
        .filter(config => config.layerId === layerId)
        .forEach(config => loadFacilityModel(threeLayer, config));

    // Check whether threeLayer supports addEventListener
    if (typeof threeLayer.addEventListener === 'function') {
        threeLayer.addEventListener('click', function (e) {
            const raycaster = new THREE.Raycaster();
            const mouse = new THREE.Vector2();

            mouse.x = (e.pixel.x / map.width) * 2 - 1;
            mouse.y = -(e.pixel.y / map.height) * 2 + 1;

            raycaster.setFromCamera(mouse, threeLayer.camera);
            const intersects = raycaster.intersectObjects(threeLayer.scene.children, true);

            if (intersects.length > 0) {
                console.log('Click detected a model', intersects[0]);
                alert(`Model detected on click: ${intersects[0].object.name || 'Unnamed model'}`);
            }
        });
    } else {
        console.warn('threeLayer does not support addEventListener');
    }

    layerManager.threeLayers.set(layerId, threeLayer);
    layerManager.views.set(layerId, view);
    layerManager.overlays.push(threeLayer);
}

/* 6. Unified event binding */
function bindOverlayEvents() {
    const eventHandlers = {
        dblclick: e => alert(`${e.target} double-clicked`),
        rightclick: e => alert(`${e.target} right-clicked`)
    };

    layerManager.overlays.forEach(overlay => {
        if (typeof overlay.addEventListener !== 'function') {
            console.warn('Overlay does not support addEventListener, skipping:', overlay);
            return;
        }
        Object.entries(eventHandlers).forEach(([event, handler]) => {
            overlay.addEventListener(event, handler);
        });
    });
}

/* 7. Public API */
window.mapManager = {
    init() {
        initGroundOverlay();
        load_all_facility('mainLayer');
        bindOverlayEvents();
    },
    release() {
        layerManager.overlays.forEach(overlay => {
            map.removeOverlay(overlay);
            overlay.dispose?.();
        });
        layerManager.threeLayers.clear();
        layerManager.views.clear();
        layerManager.overlays = [];
    }
};

// Initialization
