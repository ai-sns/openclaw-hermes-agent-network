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
    const pStart = new BMapGL.Point(116.22971, 39.74441);
    const pEnd = new BMapGL.Point(116.25646, 39.76812);
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
            position: [116.36200604013413, 39.94527332861826],
            modelUrl: 'https://cdn.jsdelivr.net/gh/photonchen/photonchen.github.io/aisnsbuilding.glb',
            scale: 0.4,
            rotation: {x: Math.PI / 2}
        },
        {
            id: 'houseModel',
            layerId: 'mainLayer',
            position: home_position ? [home_position.lng, home_position.lat] : [121.51246021573293, 31.304969368085807],//todo
            modelUrl: 'house_red.glb',
            scale: 2,
            rotation: {x: Math.PI / 2, y: Math.PI / 10}
        },
        {
            id: 'playerModel',
            layerId: 'mainLayer',
            position: [116.30391532368695, 40.04931576869293],
            modelUrl: 'https://cdn.jsdelivr.net/gh/photonchen/photonchen.github.io/playergirl.glb',
            scale: 150,
            rotation: {x: Math.PI / 2}
        },
        {
            id: 'officeModel',
            layerId: 'mainLayer',
            position: [116.30873909340876, 40.063344012305905],
            modelUrl: 'https://cdn.jsdelivr.net/gh/photonchen/photonchen.github.io/officebuilding.glb',
            scale: 5,
            rotation: {x: Math.PI / 2}
        },
        {
            id: 'centerModel',
            layerId: 'mainLayer',
            position: [116.20683342989894, 39.96289480301391],
            modelUrl: 'http://www.ai-sns.cc/aigccentermap.glb',
            scale: 0.1,
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
        'https://i.ibb.co/PtWsXLY/three-Layer.png',
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

    const geometry = new THREE.BoxGeometry(500, 500, 500);
    const cube = new THREE.Mesh(geometry, material);

    const mcpoint = convertCoords([116.36270578593066, 39.931188733629675]);
    cube.position.set(mcpoint.lng, mcpoint.lat, 250);

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
        click: e => console.log(`${e.target} clicked`),
        dblclick: e => alert(`${e.target} double-clicked`),
        rightclick: e => alert(`${e.target} right-clicked`)
    };

    layerManager.overlays.forEach(overlay => {
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
