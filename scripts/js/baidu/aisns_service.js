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
        }
    ];
}

/* 3. Reusable model loader */
const facility_gltfLoader = new mapvgl.THREELoader.GLTFLoader();

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
