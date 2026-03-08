const FETCH_RETRIES = 30;

const INITIAL_RETRY_DELAY = 1000;

const REQUEST_TIMEOUT = 80000;



async function loadPersonsData(url, retries = FETCH_RETRIES, retryDelay = INITIAL_RETRY_DELAY) {

    // Validate input parameters

    if (typeof url !== 'string' || !url.trim()) {

        throw new Error('Invalid URL parameter');

    }



    // Inner function that performs the request

    async function fetchData(retriesLeft, delay) {

        const controller = new AbortController();

        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);



        try {



            console.log(`Retries left: ${retriesLeft}`);



            // Add random query param to avoid caching

            const fetchUrl = new URL(url);

            fetchUrl.searchParams.set('t', Date.now());



            const response = await fetch(fetchUrl.toString(), {

                signal: controller.signal,

                cache: 'no-cache'

            });





            clearTimeout(timeoutId);



            if (!response.ok) {

                throw new Error(`Request failed: ${response.status} ${response.statusText}`);

            }



            // Try parsing JSON response

            const data = await response.json();

            // showAlert(`Request succeeded, response data: ${data}`);

            return data;



        } catch (error) {

            clearTimeout(timeoutId);



            // Check whether it is a timeout error

            if (error.name === 'AbortError') {

                console.error('Request timed out and was aborted');

                showAlert('Request timed out and was aborted');

                throw new Error('Request timed out');

            }



            // Retry logic

            if (retriesLeft > 0) {

                console.warn(`Request failed: ${error.message}. Retries left: ${retriesLeft}. Retrying in ${delay}ms...`);

                showAlert(`Failed to fetch data. Retries left: ${retriesLeft}. Retrying in ${delay}ms...`);

                await new Promise(resolve => setTimeout(resolve, delay));

                return fetchData(retriesLeft - 1, delay * 1);

            }



            console.error('Final request failed:', error.message);

            showAlert(`Final request failed: ${error.message}`);

            throw error;

        }

    }



    return fetchData(retries, retryDelay);

}



// Wrap async operation loadPersonsData

async function load_persons_data_and_show() {

    const resolvedBaseUrl = (typeof API_BASE_URL !== 'undefined' && API_BASE_URL)

        ? API_BASE_URL

        : ((typeof window !== 'undefined' && window.__AGENT_SERVER__) ? window.__AGENT_SERVER__ : '');

    const normalizedBaseUrl = (resolvedBaseUrl || '').replace(/\/+$/, '');

    const dataUrl = `${normalizedBaseUrl}/api/get_people_list/`;

    const nation_id = nation_id_me;

    // alert("nation_id_me");

    // alert(nation_id_me);

    try {

        const data = await loadPersonsData(dataUrl); // Load person data

        console.log("Successfully loaded person data:", data);

        showAlert(`User data loaded successfully.`);



        // Filter out items whose nation_id equals the input value

        personsdata = data.filter(person => {

            const pid = (person && (person.nation_id || person.nationid)) ? String(person.nation_id || person.nationid).trim() : '';

            return pid !== String(nation_id || '').trim();

        });



        // Show updated data points

        showpoints();

    } catch (error) {

        console.error("Failed to load person data. Suggestion:",

            error.name === 'AbortError'

                ? 'Check your network connection or try again later'

                : 'Contact the system administrator');

    }

}





function findMeshes(object) {

    const meshes = [];

    object.traverse((child) => {

        if (child.isMesh) {

            meshes.push(child);

        }

    });

    return meshes;

}



var highlightedObject = null;

var highlightedObjectOriginalColors = null;

// Load 3D models

var all_model_meshes = [];

var geoBoundObjects = new Set();

var loader = new THREE.GLTFLoader();

var loader2 = new THREE.GLTFLoader();



// Model loading with retries

async function loadModelWithRetry(loaderInstance, url, retries = 3, retryDelay = 1000) {

    for (let attempt = 1; attempt <= retries; attempt++) {

        try {

            const controller = new AbortController();

            const timeoutId = setTimeout(() => controller.abort(), 15000);



            const gltf = await new Promise((resolve, reject) => {

                // Listen for load errors

                const errorHandler = (error) => {

                    clearTimeout(timeoutId);

                    reject(error);

                };

                // alert(url);



                // Load model

                loaderInstance.load(

                    url,

                    (gltf) => {

                        clearTimeout(timeoutId);

                        resolve(gltf);

                    },

                    undefined,

                    errorHandler

                );

            });



            return gltf;

        } catch (error) {

            console.error(`Model load failed (attempt ${attempt}/${retries}): ${error.message}`);



            if (attempt < retries) {

                console.log(`Retrying in ${retryDelay}ms...`);

                await new Promise(resolve => setTimeout(resolve, retryDelay));

                retryDelay *= 2; // Exponential backoff

            } else {

                throw new Error(`Model load failed after ${retries} retries: ${error.message}`);

            }

        }

    }

}



function initMap() {





    // Prefer window.current_position as the map center

    let center;

    if (typeof window.current_position !== 'undefined' && window.current_position !== null &&

        typeof window.current_position.lng !== 'undefined' && typeof window.current_position.lat !== 'undefined') {

        center = {lng: window.current_position.lng, lat: window.current_position.lat, altitude: 0};

        console.log("Initializing Google map with configured position:", window.current_position);

    } else {

        center = {lng: 116.27882, lat: 39.71164, altitude: 0};

        console.log("Initializing Google map with default position");

    }





    const DEFAULT_COLOR = 0xffffff;

    const HIGHLIGHT_COLOR = 0xff0000;

    const mapStyles = [

        // Hide all POIs

        {

            featureType: "poi",

            elementType: "all",

            stylers: [{visibility: "off"}]

        }

    ];

    const mapOptions = {

        center,

        // mapId: "7057886e21226ff7", // without road names and related labels

        mapId: "b8fc4b5a8471b933",

        // renderingType: google.maps.RenderingType.VECTOR,

        // styles: mapStyles,

        zoom: 17,

        draggableCursor: 'grab',

        draggingCursor: 'grabbing',

        tilt: 67.5,

        disableDefaultUI: true,

        backgroundColor: "transparent",

        gestureHandling: "greedy",

    };



    // // Create map and overlay

    // const map = new google.maps.Map(document.getElementById("map"), mapOptions);

    //

    // const overlay = new google.maps.plugins.three.ThreeJSOverlayView({map, anchor: center, upAxis: "Y"});

    map = new google.maps.Map(document.getElementById("map"), mapOptions);

    geocoder = new google.maps.Geocoder();

    marker = new google.maps.Marker({

        map,

        draggable: true

    });

    marker.addListener("dragend", (event) => {

        const position = marker.getPosition();

        console.log(position);

        var address_input = document.getElementById("address");

        const latlng = {

            lat: parseFloat(position.lat()),

            lng: parseFloat(position.lng()),

        };

        geocoder

            .geocode({location: latlng})

            .then((response) => {

                if (response.results[0]) {

                    address_input.value = response.results[0].formatted_address;



                    const location_result = latlng;

                    //location_result is readonly

                    home_position = {

                        lng: location_result.lng,

                        lat: location_result.lat,

                        altitude: 0,

                        scale: 20

                    };

                    const home_position_str = JSON.stringify(home_position);

                    update_map_setting("home_position", home_position_str)





                } else {

                    window.alert("No results found");

                }

            })

            .catch((e) => window.alert("Geocoder failed due to: " + e));



    });

    directionsService = new google.maps.DirectionsService();

    directionsRenderer = new google.maps.DirectionsRenderer({

        draggable: true,

        map,

        // panel: document.getElementById("panel"),

    });

    directionsRenderer.addListener("directions_changed", () => {



        const directions = directionsRenderer.getDirections();

        if (directions) {

            computeTotalDistance(directions);

        }

    });

    initialize_route();

    const tmpcenter = {lat: 39.71164, lng: 116.27882};

    // overlay = new google.maps.plugins.three.ThreeJSOverlayView({map, anchor: center, upAxis: "Y"});

    overlay = new google.maps.plugins.three.ThreeJSOverlayView({

        map,

        anchor: tmpcenter,

        upAxis: "Y"

    });



    let overlayAnchor = {

        lat: Number(tmpcenter.lat),

        lng: Number(tmpcenter.lng),

        altitude: 0,

    };



    const registerGeoBoundObject = (obj, geo) => {

        try {

            if (!obj) return;

            if (!obj.userData) obj.userData = {};

            if (geo && Number.isFinite(Number(geo.lat)) && Number.isFinite(Number(geo.lng))) {

                obj.userData.geo = {

                    lat: Number(geo.lat),

                    lng: Number(geo.lng),

                    altitude: Number(geo.altitude) || 0,

                };

            }

            geoBoundObjects.add(obj);

        } catch (e) {

        }

    };



    const getGeoFromObject = (obj) => {

        try {

            if (!obj) return null;

            const geo = (obj.userData && obj.userData.geo) ? obj.userData.geo : null;

            if (geo && Number.isFinite(Number(geo.lat)) && Number.isFinite(Number(geo.lng))) {

                return { lat: Number(geo.lat), lng: Number(geo.lng), altitude: Number(geo.altitude) || 0 };

            }



            const loc = (obj.userData && obj.userData.location) ? obj.userData.location : null;

            if (Array.isArray(loc) && loc.length >= 2) {

                const lat = Number(loc[1]);

                const lng = Number(loc[0]);

                if (Number.isFinite(lat) && Number.isFinite(lng)) {

                    return { lat, lng, altitude: 0 };

                }

            }

        } catch (e) {

        }

        return null;

    };



    const reprojectGeoBoundObjects = () => {

        try {

            if (!overlay || typeof overlay.latLngAltitudeToVector3 !== 'function') return;



            const objectsToReproject = new Set();



            if (model_loaded_list) {

                for (const nationId of Object.keys(model_loaded_list)) {

                    const m = model_loaded_list[nationId];

                    if (!m) continue;

                    objectsToReproject.add(m);

                    registerGeoBoundObject(m);

                }

            }



            for (const obj of geoBoundObjects) {

                if (obj) objectsToReproject.add(obj);

            }



            for (const obj of objectsToReproject) {

                const geo = getGeoFromObject(obj);

                if (!geo) continue;

                registerGeoBoundObject(obj, geo);

                overlay.latLngAltitudeToVector3(geo, obj.position);

            }



            if (typeof overlay.requestRedraw === 'function') {

                overlay.requestRedraw();

            }

        } catch (e) {

            console.warn('Failed to reproject geo-bound objects after anchor update:', e);

        }

    };



    let __preferPersonAnchorUntil = 0;

    let __preferPersonAnchorRevertTimer = null;

    let __overlayAnchorMode = 'map';



    const __getMyPersonGeo = () => {

        try {

            if (typeof nation_id_me !== 'undefined' && nation_id_me && model_loaded_list && model_loaded_list[nation_id_me]) {

                const m = model_loaded_list[nation_id_me];

                const geo = (m && m.userData && m.userData.geo) ? m.userData.geo : null;

                if (geo && Number.isFinite(Number(geo.lat)) && Number.isFinite(Number(geo.lng))) {

                    return { lat: Number(geo.lat), lng: Number(geo.lng), altitude: Number(geo.altitude) || 0 };

                }

            }

        } catch (e) {

        }



        try {

            if (typeof getPersonPointByNationId === 'function' && typeof nation_id_me !== 'undefined' && nation_id_me) {

                const p = getPersonPointByNationId(nation_id_me);

                if (p) {

                    const latVal = (typeof p.lat === 'function') ? p.lat() : p.lat;

                    const lngVal = (typeof p.lng === 'function') ? p.lng() : p.lng;

                    if (Number.isFinite(Number(latVal)) && Number.isFinite(Number(lngVal))) {

                        return { lat: Number(latVal), lng: Number(lngVal), altitude: 0 };

                    }

                }

            }

        } catch (e) {

        }



        try {

            if (typeof window !== 'undefined' && window.current_position) {

                const latVal = window.current_position.lat;

                const lngVal = window.current_position.lng;

                if (Number.isFinite(Number(latVal)) && Number.isFinite(Number(lngVal))) {

                    return { lat: Number(latVal), lng: Number(lngVal), altitude: 0 };

                }

            }

        } catch (e) {

        }



        return null;

    };



    const __isMyPersonNearViewportCenter = (centerLat, centerLng) => {

        try {

            const personGeo = __getMyPersonGeo();

            if (!personGeo) return false;



            const centerLatLng = new google.maps.LatLng(Number(centerLat), Number(centerLng));

            const personLatLng = new google.maps.LatLng(Number(personGeo.lat), Number(personGeo.lng));

            const d = google.maps.geometry.spherical.computeDistanceBetween(centerLatLng, personLatLng);



            let radius = 0;

            try {

                const b = map.getBounds && map.getBounds();

                const ne = b && b.getNorthEast ? b.getNorthEast() : null;

                if (ne) {

                    radius = google.maps.geometry.spherical.computeDistanceBetween(centerLatLng, ne);

                }

            } catch (e) {

            }



            if (!Number.isFinite(radius) || radius <= 0) {

                radius = 5000;

            }



            const threshold = Math.max(500, radius * 0.35);

            return Number.isFinite(d) && d <= threshold;

        } catch (e) {

            return false;

        }

    };



    const maybeUpdateOverlayAnchorToMapCenter = (opts = {}) => {

        try {

            if (!map || !overlay || typeof overlay.setAnchor !== 'function') return;



            const c = map.getCenter();

            if (!c) return;



            const centerLat = (typeof c.lat === 'function') ? c.lat() : c.lat;

            const centerLng = (typeof c.lng === 'function') ? c.lng() : c.lng;

            if (!Number.isFinite(Number(centerLat)) || !Number.isFinite(Number(centerLng))) return;



            let strategy = 'hybrid';

            try {

                if (typeof window !== 'undefined' && window.__overlayAnchorStrategy) {

                    strategy = String(window.__overlayAnchorStrategy || '').toLowerCase();

                }

            } catch (e) {

            }



            const allowPersonAnchor = strategy !== 'map';



            const now = Date.now();

            const preferPerson = allowPersonAnchor && Number.isFinite(__preferPersonAnchorUntil) && now < __preferPersonAnchorUntil;

            const personNearCenter = allowPersonAnchor && __isMyPersonNearViewportCenter(centerLat, centerLng);



            let desiredAnchor = { lat: Number(centerLat), lng: Number(centerLng), altitude: 0 };

            let desiredMode = 'map';

            if (preferPerson || personNearCenter) {

                const myGeo = __getMyPersonGeo();

                if (myGeo) {

                    desiredAnchor = myGeo;

                    desiredMode = 'person';

                }

            }



            const distM = google.maps.geometry.spherical.computeDistanceBetween(

                new google.maps.LatLng(Number(overlayAnchor.lat), Number(overlayAnchor.lng)),

                new google.maps.LatLng(Number(desiredAnchor.lat), Number(desiredAnchor.lng))

            );



            const force = !!opts.force;

            const modeSwitch = String(desiredMode) !== String(__overlayAnchorMode);



            const shouldUpdate = force

                ? (Number.isFinite(distM) && distM > 1)

                : (modeSwitch

                    ? (Number.isFinite(distM) && distM > 1)

                    : (Number.isFinite(distM) && distM > 100000));



            if (shouldUpdate) {

                overlayAnchor = { lat: Number(desiredAnchor.lat), lng: Number(desiredAnchor.lng), altitude: Number(desiredAnchor.altitude) || 0 };

                __overlayAnchorMode = desiredMode;

                overlay.setAnchor(overlayAnchor);

                reprojectGeoBoundObjects();

                try {

                    if (typeof requestAnimationFrame === 'function') {

                        requestAnimationFrame(() => {

                            reprojectGeoBoundObjects();

                        });

                    }

                } catch (e) {

                }

            }

        } catch (e) {

            console.warn('Failed to update overlay anchor:', e);

        }

    };



    try {

        window.__maybeUpdateOverlayAnchorToMapCenter = maybeUpdateOverlayAnchorToMapCenter;

        window.__reprojectGeoBoundObjects = reprojectGeoBoundObjects;

        window.__preferPersonAnchorForMs = (ms = 4500) => {

            try {

                const dur = Number(ms);

                const safeDur = (Number.isFinite(dur) ? Math.max(0, dur) : 4500);

                __preferPersonAnchorUntil = Date.now() + safeDur;



                if (__preferPersonAnchorRevertTimer) {

                    clearTimeout(__preferPersonAnchorRevertTimer);

                    __preferPersonAnchorRevertTimer = null;

                }



                maybeUpdateOverlayAnchorToMapCenter({ force: true });



                __preferPersonAnchorRevertTimer = setTimeout(() => {

                    try {

                        maybeUpdateOverlayAnchorToMapCenter({ force: true });

                    } catch (e) {

                    }

                }, safeDur + 50);

            } catch (e) {

            }

        };

    } catch (e) {

    }



    try {

        map.addListener('idle', () => {

            maybeUpdateOverlayAnchorToMapCenter();

        });

    } catch (e) {

    }



    try {

        let __anchorUpdateDebounceTimer = null;

        map.addListener('center_changed', () => {

            try {

                if (__anchorUpdateDebounceTimer) clearTimeout(__anchorUpdateDebounceTimer);

                __anchorUpdateDebounceTimer = setTimeout(() => {

                    maybeUpdateOverlayAnchorToMapCenter();

                }, 150);

            } catch (e) {

            }

        });

    } catch (e) {

    }



    try {

        maybeUpdateOverlayAnchorToMapCenter();

    } catch (e) {

    }



    const mapDiv = map.getDiv();

    const mousePosition = new THREE.Vector2();

    console.log("intimouseposition:", mousePosition);



    map.addListener("click", (e) => {

        // alert(1);

        last_click_point = e.latLng;

        center_point = getCenter();

        // alert("lastpoint:" + JSON.stringify(e.latLng.toJSON(), null, 2));

        // alert("center_point:" + JSON.stringify(center_point.toJSON(), null, 2));

        distance = getDistance(last_click_point, center_point);

        // alert(distance);

        // showinfo();

        // setTimeout(moveinfo, 1500);

        const domEvent = e.domEvent;

        const {left, top, width, height} = mapDiv.getBoundingClientRect();

        const x = domEvent.clientX - left;

        const y = domEvent.clientY - top;

        mousePosition.x = 2 * (x / width) - 1;

        mousePosition.y = 1 - 2 * (y / height);



        // Handle coordinate capture mode

        if (coordinateCaptureMode) {

            handleMapClick(e.latLng);

        }



        if (instruct_to_move_flag == true) {

            const tmpcenter = {lat: 39.71164, lng: 116.27882};

            // overlay = new google.maps.plugins.three.ThreeJSOverlayView({map, anchor: center, upAxis: "Y"});

            // overlay.setAnchor(tmpcenter);

            const coordinates = getLastClickPoint();

            // overlay.setAnchor(coordinates);

            try {

                if (typeof setPersonModelPointByNationId === 'function') {

                    setPersonModelPointByNationId(nation_id_me, coordinates);

                }

            } catch (err) {

                console.warn('Failed to move person model:', err);

            }



            try {

                if (typeof setPersonPointByNationId === 'function') {

                    const lngVal = (coordinates && typeof coordinates.lng === 'function') ? coordinates.lng() : null;

                    const latVal = (coordinates && typeof coordinates.lat === 'function') ? coordinates.lat() : null;

                    if (lngVal !== null && latVal !== null) {

                        setPersonPointByNationId(nation_id_me, lngVal, latVal);

                        window.current_position = { lng: lngVal, lat: latVal };

                    }

                }

            } catch (err) {

                console.warn('Failed to update person location:', err);

            }



            try {

                if (typeof update_location_and_open_nearest_place === 'function') {

                    const lngVal = (coordinates && typeof coordinates.lng === 'function') ? coordinates.lng() : null;

                    const latVal = (coordinates && typeof coordinates.lat === 'function') ? coordinates.lat() : null;

                    if (lngVal !== null && latVal !== null) {

                        update_location_and_open_nearest_place(lngVal, latVal, { maxDistanceM: 1000, throttleMs: 800 });

                    }

                }

            } catch (err) {

                console.warn('Failed to sync location to backend:', err);

            }

        }



        overlay.requestRedraw();

    });

    map.addListener("zoom_changed", () => {

        const zoomLevel = map.getZoom();

        console.log("Current zoom level:", zoomLevel);

    });



    const uluru = {lat: 40.76971146231474, lng: -73.97265643012797};

    const latLngAltitudeLiteral2 = {

        lat: 40.76726879657253,

        lng: -73.97383222939642,

        altitude: 80,

    };



    // Show initial greeting bubble

    function showinfo() {

        openBubble({

            body: "Hello, I'm CBot. Nice to meet you.",

            showClose: false,

            position: {

                lat: 40.76971146231474,

                lng: -73.97265643012797,

                altitude: 520

            },

            pixelOffset: new google.maps.Size(20, -150),

        }, map);

    }



    // Show second greeting bubble then auto-close

    function moveinfo() {

        closeBubble();

        openBubble({

            body: "Nice to meet you. How can I go to AI-SNS Center.",

            showClose: false,

            position: {

                lat: 40.76971146231474,

                lng: -73.97265643012797,

                altitude: 520

            },

            pixelOffset: new google.maps.Size(-140, -150),

        }, map);

        setTimeout(() => {

            closeBubble();

            console.log("Bubble closed"); // For debugging

        }, 2000);

    }



// Use async/await for async loading to ensure models are fully loaded before continuing

    const loadBuilding = async () => {

        try {

            const buildingLatLng = { lat: 1.2847964346121146, lng: 103.8627787698048, altitude: 0 };



            // Load model with retry

            const gltf = await loadModelWithRetry(loader2, 'aisnsbuilding.glb');

            const modelBuilding = gltf.scene;



            // Compute bounding box for scaling / ground alignment

            const box = new THREE.Box3().setFromObject(modelBuilding);

            const size = box.getSize(new THREE.Vector3());

            const height = size.y;

            console.log("Building model height:", height);



            // Scale model to a target height (ThreeJSOverlayView uses meters as world units)

            const desiredHeight = 300;

            const scale = (height && height > 0) ? (desiredHeight / height) : 1;

            console.log("buildign scale",scale);

            modelBuilding.scale.set(scale, scale, scale);



            // Align base of model to ground

            const box2 = new THREE.Box3().setFromObject(modelBuilding);

            if (box2 && box2.min && Number.isFinite(box2.min.y)) {

                modelBuilding.position.y -= box2.min.y;

            }



            // Position model

            const position3 = overlay.latLngAltitudeToVector3(buildingLatLng, modelBuilding.position);

            modelBuilding.position.copy(position3);



            registerGeoBoundObject(modelBuilding, buildingLatLng);



            overlay.scene.add(modelBuilding);

            console.log("Building model loaded successfully");



            try {

                modelLoadStatus.building = true;

            } catch (e) {

            }



            try {

                overlay.requestRedraw();

            } catch (e) {

            }



            checkAnimationStart();

        } catch (error) {

            console.error('Failed to load building model:', error);

        }

    };



    const loadHouse = async () => {

        try {

            // Load model with retry

            const gltf = await loadModelWithRetry(loader, 'house_red.glb');

            modelhouse = gltf.scene;

            // Add ambient light

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);

            //overlay.scene.add(ambientLight);

            // Add directional light

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.25);

            directionalLight.position.set(-1, -1, -1); // Place the light behind the model

            // overlay.scene.add(directionalLight);

            // Compute model bounding box

            const box = new THREE.Box3().setFromObject(modelhouse);

            const size = box.getSize(new THREE.Vector3());

            const height = size.y; // Model height

            console.log("House model height:", height);

            // Set model scale/rotation/position

            // Adjust scale based on height

            const desiredHeight = 150; // Desired height

            const scale = desiredHeight / height;

            // Set model scale/rotation/position

            // modelhouse.scale.set(scale, scale, scale);

            modelhouse.scale.set(1, 1, 1);

            modelhouse.rotation.x = (Math.PI / 15) * 0;

            modelhouse.rotation.y = (Math.PI / 15) * 1.6;

            const position3 = overlay.latLngAltitudeToVector3(home_position, modelhouse.position);

            try {

                if (home_position && home_position.lat !== undefined && home_position.lng !== undefined) {

                    registerGeoBoundObject(modelhouse, { lat: Number(home_position.lat), lng: Number(home_position.lng), altitude: Number(home_position.altitude) || 0 });

                }

            } catch (e) {

            }

            // Add model to scene

            overlay.scene.add(modelhouse);

            console.log("House model loaded successfully");

            modelLoadStatus.house = true;

            checkAnimationStart();

        } catch (error) {

            console.error('Failed to load house model:', error);

        }

    };

    loadBuilding();

    loadHouse();

    const loadModel = async () => {

        try {

            // Load model with retry

            const gltf = await loadModelWithRetry(loader, 'avatar3d/tshirtgirl_0_0_0_0_1_0.glb');

            model = gltf.scene;

            // Add ambient light

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);

            //overlay.scene.add(ambientLight);

            // Add directional light

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.25);

            directionalLight.position.set(-1, -1, -1); // Place the light behind the model

            // overlay.scene.add(directionalLight);

            // Compute model bounding box

            const box = new THREE.Box3().setFromObject(model);

            const size = box.getSize(new THREE.Vector3());

            const height = size.y; // Model height

            console.log("Girl model height:", height);

            // Adjust scale based on height

            const desiredHeight = 150; // Desired height

            const scale = desiredHeight / height;

            // Set model scale/rotation/position

            model.scale.set(scale, scale, scale);

            model.rotation.x = Math.PI / 30;

            model.rotation.y = Math.PI / 1.5;

            try {

                const base = (home_position && home_position.lat !== undefined && home_position.lng !== undefined)

                    ? { lat: Number(home_position.lat), lng: Number(home_position.lng) }

                    : (() => {

                        const c = map && typeof map.getCenter === 'function' ? map.getCenter() : null;

                        const lat = c ? ((typeof c.lat === 'function') ? c.lat() : c.lat) : null;

                        const lng = c ? ((typeof c.lng === 'function') ? c.lng() : c.lng) : null;

                        return { lat: Number(lat), lng: Number(lng) };

                    })();



                if (Number.isFinite(base.lat) && Number.isFinite(base.lng)) {

                    const baseLatLng = new google.maps.LatLng(base.lat, base.lng);

                    const pEast = google.maps.geometry.spherical.computeOffset(baseLatLng, 60, 90);

                    const pFinal = google.maps.geometry.spherical.computeOffset(pEast, 250, 180);

                    const geo = { lat: pFinal.lat(), lng: pFinal.lng(), altitude: 0 };

                    registerGeoBoundObject(model, geo);

                    overlay.latLngAltitudeToVector3(geo, model.position);

                } else {

                    model.position.set(60, 0, -250);

                }

            } catch (e) {

                model.position.set(60, 0, -250);

            }

            // Add model to scene

            overlay.scene.add(model);

            // Find all meshes in the scene

            const modelMeshes_found = findMeshes(gltf.scene);

            // Add found meshes to global array

            all_model_meshes.push(...modelMeshes_found);

            // Mark meshes as clickable

            model.traverse((child) => {

                if (child.isMesh) {

                    child.cursor = 'pointer';

                    child.userData.isClickable = true;

                }

            });

            // Create animation mixer and play animation

            if (gltf.animations && gltf.animations.length > 0) {

                const mixer = new THREE.AnimationMixer(gltf.scene);

                const action = mixer.clipAction(gltf.animations[0]);

                mixer.timeScale = 0.5;

                action.setDuration(1).play();

                mixers.push(mixer);

                console.log("Girl model animation started");

            }

            console.log("Girl model loaded successfully");

            modelLoadStatus.girl = true;

            checkAnimationStart();

        } catch (error) {

            console.error('Failed to load girl model:', error);

        }

    };

// Call loadModel

    loadModel();

    // Load AI-SNS building model (assumes similar logic)



    //load_aisns_building();

    const loadModel2 = async () => {

        try {

            // Load model with retry

            const gltf = await loadModelWithRetry(loader, 'avatar3d/ctgirlschool_0_0_0_0_02_0.glb');

            model2 = gltf.scene;

            // Add ambient light

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);

            //overlay.scene.add(ambientLight);

            // Add directional light

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.25);



            directionalLight.position.set(-1, -1, -1); // Place the light behind the model

            // overlay.scene.add(directionalLight);

            // Compute model bounding box

            const box = new THREE.Box3().setFromObject(model2);

            const size = box.getSize(new THREE.Vector3());

            const height = size.y; // Model height

            console.log("Boy model height:", height);

            // Adjust scale based on height

            const desiredHeight = 150; // Desired height

            const scale = desiredHeight / height;

            model2.scale.set(scale, scale, scale);

            // Set model rotation and position

            // model2.rotation.x = Math.PI / 30;

            model2.rotation.x = THREE.MathUtils.degToRad(6);  // 6 degrees -> radians

            model2.rotation.z = THREE.MathUtils.degToRad(0);  // 0 degrees -> radians

            model2.rotation.y = Math.PI / 1.5;

            try {

                const base = (home_position && home_position.lat !== undefined && home_position.lng !== undefined)

                    ? { lat: Number(home_position.lat), lng: Number(home_position.lng) }

                    : (() => {

                        const c = map && typeof map.getCenter === 'function' ? map.getCenter() : null;

                        const lat = c ? ((typeof c.lat === 'function') ? c.lat() : c.lat) : null;

                        const lng = c ? ((typeof c.lng === 'function') ? c.lng() : c.lng) : null;

                        return { lat: Number(lat), lng: Number(lng) };

                    })();



                if (Number.isFinite(base.lat) && Number.isFinite(base.lng)) {

                    const baseLatLng = new google.maps.LatLng(base.lat, base.lng);

                    const pEast = google.maps.geometry.spherical.computeOffset(baseLatLng, 130, 90);

                    const pFinal = google.maps.geometry.spherical.computeOffset(pEast, 250, 180);

                    const geo = { lat: pFinal.lat(), lng: pFinal.lng(), altitude: -100 };

                    registerGeoBoundObject(model2, geo);

                    overlay.latLngAltitudeToVector3(geo, model2.position);

                } else {

                    model2.position.set(130, 0, -250);

                }

            } catch (e) {

                model2.position.set(130, 0, -250);

            }

            // Add model to scene

            overlay.scene.add(model2);

            // Find all meshes in the scene

            const modelMeshes_found = findMeshes(gltf.scene);

            // Add found meshes to global array

            all_model_meshes.push(...modelMeshes_found);

            // Mark meshes as clickable

            model2.traverse((child) => {

                if (child.isMesh) {

                    child.cursor = 'pointer';

                    child.userData.isClickable = true;

                }

            });

            // Create animation mixer and play animation

            if (gltf.animations && gltf.animations.length > 0) {

                const mixer = new THREE.AnimationMixer(gltf.scene);

                const action = mixer.clipAction(gltf.animations[0]);

                mixer.timeScale = 0.5;

                action.setDuration(10).play();

                mixers.push(mixer);

                console.log("Boy model animation started");

            }

            console.log("Boy model loaded successfully");

            modelLoadStatus.boy = true;

            checkAnimationStart();

        } catch (error) {

            console.error('Failed to load boy model:', error);

        }

    };

    loadModel2();





    //set ground overlay

    const imageBounds = {

        // north: 40.773941,

        // south: 40.712216,

        // east: -74.12544,

        // west: -74.22655,

        // north: 40.03867303424458,

        // south: 40.00624462450565,

        // east: 116.24508640812037,

        // west: 116.22749734234506,

        north: 37.57643015650198,

        south: 37.55816843366316,

        east: -122.40210571869962,

        west: -122.43508166111967,

    };



    playGroundOverlay = new google.maps.GroundOverlay(

        "shouhuimap.png",//"https://storage.googleapis.com/geo-devrel-public-buckets/newark_nj_1922-661x516.jpeg",

        imageBounds,

    );

    playGroundOverlay.setMap(map);





    //loadcube

    const webglOverlay = new google.maps.WebGLOverlayView();

    // const cubePosition = { lat: 39.97619992566233, lng: 116.19042703542924 };

    const cubePosition = { lat: 37.530317234458025, lng: -122.47283866789105 };





    let scene, camera, renderer, cube;



    webglOverlay.onAdd = () => {

        scene = new THREE.Scene();

        camera = new THREE.PerspectiveCamera();



        // Add lights

        const light = new THREE.DirectionalLight(0xffffff, 0.5);

        light.position.set(0, 50, 100);

        scene.add(light);



        const ambient = new THREE.AmbientLight(0xffffff, 0.8);

        scene.add(ambient);



        // Load texture

        const textureLoader = new THREE.TextureLoader();

        const texture = textureLoader.load(

            'https://i.ibb.co/PtWsXLY/three-Layer.png',

            () => console.log("Cube texture loaded successfully"),

            undefined,

            (err) => console.error("Failed to load texture", err)

        );



        // Create cube (units: meters)

        const geometry = new THREE.BoxGeometry(30, 30, 30);

        const material = new THREE.MeshPhongMaterial({

            map: texture,

            transparent: true,

        });



        cube = new THREE.Mesh(geometry, material);

        scene.add(cube);

    };



    webglOverlay.onContextRestored = ({gl}) => {

        renderer = new THREE.WebGLRenderer({

            canvas: gl.canvas,

            context: gl,

            ...gl.getContextAttributes(),

        });

        renderer.autoClear = false;

    };



    webglOverlay.onDraw = ({gl, transformer}) => {

        if (!cube) return;



        // Bind cube position to geographic coordinates (ground level altitude=0)

        const matrix = transformer.fromLatLngAltitude({

            lat: cubePosition.lat,

            lng: cubePosition.lng,

            altitude: 0,

        });



        camera.projectionMatrix = new THREE.Matrix4().fromArray(matrix);



        // Do not rotate the cube

        renderer.render(scene, camera);

        renderer.resetState();

    };



    webglOverlay.setMap(map);





    overlay.onBeforeDraw = () => {

        // --- Raycasting first (needs the original projectionMatrix) ---

        if (mousePosition.x != 0 && mousePosition.y != 0) {

            var intersections = overlay.raycast(mousePosition, all_model_meshes, {

                recursive: false,

            });

            if (highlightedObject) {

                console.log("Highlight cleared");

                console.log("Mouse position:", mousePosition);

            }

            if (intersections.length === 0) {

                try {

                    if (highlightedObject && highlightedObject.material && highlightedObjectOriginalColors) {

                        const mats = Array.isArray(highlightedObject.material) ? highlightedObject.material : [highlightedObject.material];

                        for (let i = 0; i < mats.length; i++) {

                            const m = mats[i];

                            if (m && m.color && highlightedObjectOriginalColors[i] !== null && highlightedObjectOriginalColors[i] !== undefined) {

                                m.color.setHex(highlightedObjectOriginalColors[i]);

                            }

                        }

                    }

                } catch (e) {

                }

                highlightedObject = null;

                highlightedObjectOriginalColors = null;

            } else {

                try {

                    if (highlightedObject && highlightedObject !== intersections[0].object && highlightedObject.material && highlightedObjectOriginalColors) {

                        const mats = Array.isArray(highlightedObject.material) ? highlightedObject.material : [highlightedObject.material];

                        for (let i = 0; i < mats.length; i++) {

                            const m = mats[i];

                            if (m && m.color && highlightedObjectOriginalColors[i] !== null && highlightedObjectOriginalColors[i] !== undefined) {

                                m.color.setHex(highlightedObjectOriginalColors[i]);

                            }

                        }

                    }

                } catch (e) {

                }



                highlightedObject = intersections[0].object;

                try {

                    const mats = (highlightedObject && highlightedObject.material)

                        ? (Array.isArray(highlightedObject.material) ? highlightedObject.material : [highlightedObject.material])

                        : [];

                    highlightedObjectOriginalColors = mats.map(m => (m && m.color) ? m.color.getHex() : null);

                    for (const m of mats) {

                        if (m && m.color) {

                            m.color.setHex(HIGHLIGHT_COLOR);

                        }

                    }

                } catch (e) {

                }

                if (highlightedObject.userData) {

                    if (highlightedObject.userData.nation_id) {

                        console.log("Detected nation ID:", highlightedObject.userData.nation_id);

                        nation_id = highlightedObject.userData.nation_id;

                        currentModel = getPersonModelByNationId(nation_id);

                        mousePosition.x = 0;

                        mousePosition.y = 0;

                        showprofile3d(currentModel);

                    }

                }

            }

        }



        // --- Camera position fix (runs AFTER raycasting, BEFORE render) ---

        // ThreeJSOverlayView sets projectionMatrix to the full MVP but leaves

        // camera.position at (0,0,0). Three.js uses cameraPosition for PBR

        // specular/reflection calculations, so objects far from the anchor get

        // incorrect specular highlights (one side bright, one side dark).

        // We estimate the real camera position from the map API, set it on the

        // camera, then compensate projectionMatrix so vertex positions are

        // unaffected while the cameraPosition uniform becomes correct.

        try {

            const cam = overlay.camera;

            if (cam && map) {

                const c = map.getCenter();

                if (c) {

                    const cLat = (typeof c.lat === 'function') ? c.lat() : c.lat;

                    const cLng = (typeof c.lng === 'function') ? c.lng() : c.lng;

                    const zoom = map.getZoom() || 15;

                    const tiltDeg = map.getTilt() || 0;

                    const headDeg = map.getHeading() || 0;



                    // Estimate camera altitude from zoom level (meters)

                    const altitudeM = 35200000 / Math.pow(2, Math.max(zoom - 1, 0));



                    // Tilt & heading in radians

                    const tiltR = tiltDeg * Math.PI / 180;

                    const headR = headDeg * Math.PI / 180;



                    // Camera is elevated above the look-at point (map center) and

                    // offset horizontally opposite to heading by tilt amount.

                    // In Y-up scene coords (ThreeJSOverlayView with upAxis "Y"):

                    //   Y = up,  X ~ east,  Z ~ south at anchor

                    const camAlt = altitudeM * Math.cos(tiltR);

                    const camHoriz = altitudeM * Math.sin(tiltR);



                    // Convert map center to scene coordinates (ground level)

                    const centerVec = overlay.latLngAltitudeToVector3(

                        { lat: Number(cLat), lng: Number(cLng), altitude: 0 }

                    );



                    // Horizontal offset direction (opposite of heading in scene XZ)

                    const offX = -camHoriz * Math.sin(headR);

                    const offZ =  camHoriz * Math.cos(headR);



                    cam.position.set(

                        centerVec.x + offX,

                        centerVec.y + camAlt,

                        centerVec.z + offZ

                    );

                    cam.updateMatrixWorld(true);



                    // Compensate projectionMatrix so vertex positions stay correct:

                    // new_proj = original_MVP * cam.matrixWorld

                    // gl_Position = new_proj * (matrixWorldInverse * objectWorld) * v

                    //             = MVP * mW * mWInv * objectWorld * v

                    //             = MVP * objectWorld * v  (unchanged)

                    cam.projectionMatrix.multiply(cam.matrixWorld);

                }

            }

        } catch (e) {

        }

    };





}





function checkAnimationStart() {

    if (animationStarted) return;



    if (modelLoadStatus.building &&

        modelLoadStatus.house &&

        modelLoadStatus.girl &&

        modelLoadStatus.boy) {



        animate(0);

        animationStarted = true;

        console.log("All models loaded. Starting animation");

    }

}



/**

 * Parse model parameters from filename

 * Filename format: EnglishName_xRot_yRot_zRot_altitude_scale_animationIndex.glb

 * Example: ctboyblue_0_0_0_0_1_0.glb

 * @param {string} filename - filename

 * @returns {object|null} Parsed params; returns null if parsing fails

 */

function parseModelFilename(filename) {

    // Strip path and keep only the filename

    const baseName = filename.split('/').pop().split('\\').pop();

    // Strip extension

    const nameWithoutExt = baseName.replace(/\.[^/.]+$/, '');



    // Match: starts with letters, followed by underscore-separated numbers

    const match = nameWithoutExt.match(/^[a-zA-Z]+(.*)$/);

    if (!match || !match[1]) {

        return null;

    }



    // Parse underscore-separated numeric params after the letter prefix

    const paramString = match[1];

    const params = paramString.split('_').filter(s => s !== '');



    if (params.length < 6) {

        console.warn(`Filename has fewer than 6 params: ${filename}. Found ${params.length} params`);

        return null;

    }



    // Parse scale parameter (5th number, index 4)

    // If it starts with 0, treat as decimal, e.g. 05 => 0.5

    let scaleMultiplier = 1;

    const scaleParam = params[4];

    if (scaleParam.startsWith('0') && scaleParam.length > 1) {

        // Starts with 0: convert to decimal

        scaleMultiplier = parseFloat('0.' + scaleParam.substring(1));

    } else {

        scaleMultiplier = parseFloat(scaleParam);

    }



    return {

        rotationX: parseFloat(params[0]) || 0,      // 1st number: X rotation (degrees)

        rotationY: parseFloat(params[1]) || 0,      // 2nd number: Y rotation (degrees)

        rotationZ: parseFloat(params[2]) || 0,      // 3rd number: Z rotation (degrees)

        altitude: parseFloat(params[3]) || 0,       // 4th number: altitude

        scaleMultiplier: scaleMultiplier,           // 5th number: scale multiplier

        animationIndex: parseInt(params[5]) || 0    // 6th number: animation index

    };

}



/**

 * Check whether URL is a web URL

 * @param {string} url - URL string

 * @returns {boolean} True if it's a web URL

 */

function isWebUrl(url) {

    return url.startsWith('http://') || url.startsWith('https://') || url.startsWith('//');

}



var person_model_loading_promises = {};

var person_model_meshes_by_nation = {};



function showPersonModelByNationId(nation_id) {

    try {

        const model = model_loaded_list && model_loaded_list[nation_id] ? model_loaded_list[nation_id] : null;

        if (!model) return;

        model.visible = true;



        const meshes = person_model_meshes_by_nation[nation_id] || [];

        if (Array.isArray(meshes) && meshes.length) {

            const existing = new Set(all_model_meshes || []);

            for (const m of meshes) {

                if (!existing.has(m)) {

                    all_model_meshes.push(m);

                }

            }

        }

    } catch (e) {

        console.warn('Failed to show person model:', e);

    }

}



function hidePersonModelByNationId(nation_id) {

    try {

        const model = model_loaded_list && model_loaded_list[nation_id] ? model_loaded_list[nation_id] : null;

        if (!model) return;

        model.visible = false;



        const meshes = person_model_meshes_by_nation[nation_id] || [];

        if (Array.isArray(meshes) && meshes.length && Array.isArray(all_model_meshes)) {

            const toRemove = new Set(meshes);

            all_model_meshes = all_model_meshes.filter(m => !toRemove.has(m));

        }

    } catch (e) {

        console.warn('Failed to hide person model:', e);

    }

}



function rotateMyModel180AfterTalkMove(targetNationId, options = {}) {

    const meNationId = (typeof nation_id_me !== 'undefined' && nation_id_me) ? String(nation_id_me).trim() : '';

    if (!meNationId) return;



    const targetId = String(targetNationId || '').trim();

    const maxRetries = (options && options.maxRetries !== undefined) ? Number(options.maxRetries) : 40;

    const retryDelayMs = (options && options.retryDelayMs !== undefined) ? Number(options.retryDelayMs) : 200;



    let model = null;

    try {

        model = (model_loaded_list && model_loaded_list[meNationId]) ? model_loaded_list[meNationId] : null;

    } catch (e) {

        model = null;

    }



    if (!model) {

        try {

            if (typeof overlay !== 'undefined' && overlay && overlay.scene && typeof overlay.scene.getObjectByName === 'function') {

                model = overlay.scene.getObjectByName(meNationId);

            }

        } catch (e) {

            model = null;

        }

    }



    if (!model) {

        if (maxRetries > 0) {

            setTimeout(() => rotateMyModel180AfterTalkMove(targetId, { maxRetries: maxRetries - 1, retryDelayMs }), retryDelayMs);

        }

        return;

    }



    try {

        if (!model.userData) model.userData = {};

        if (model.userData.__talk_original_rotation_y === undefined || model.userData.__talk_original_rotation_y === null) {

            model.userData.__talk_original_rotation_y = (model.rotation && typeof model.rotation.y === 'number') ? model.rotation.y : 0;

        }

        model.userData.__talk_face_target_last_nation_id = targetId;

        model.userData.__talk_is_active = true;

    } catch (e) {

    }



    try {

        // Google Maps 3D overlay: rotation.y is yaw.
        // Face north: rotation.y = PI
        const desiredY = Math.PI;

        const currentY = (model.rotation && typeof model.rotation.y === 'number') ? model.rotation.y : 0;

        if (Math.abs(currentY - desiredY) > 1e-6) {

            model.rotation.y = desiredY;

        }

    } catch (e) {

        console.warn('Failed to rotate my model after talk move:', e);

        return;

    }



    try {

        if (typeof overlay !== 'undefined' && overlay && typeof overlay.requestRedraw === 'function') {

            overlay.requestRedraw();

        }

    } catch (e) {

    }

}



function resetMyModelRotationAfterTalk(options = {}) {

    const meNationId = (typeof nation_id_me !== 'undefined' && nation_id_me) ? String(nation_id_me).trim() : '';

    if (!meNationId) return;



    const maxRetries = (options && options.maxRetries !== undefined) ? Number(options.maxRetries) : 40;

    const retryDelayMs = (options && options.retryDelayMs !== undefined) ? Number(options.retryDelayMs) : 200;



    let model = null;

    try {

        model = (model_loaded_list && model_loaded_list[meNationId]) ? model_loaded_list[meNationId] : null;

    } catch (e) {

        model = null;

    }



    if (!model) {

        try {

            if (typeof overlay !== 'undefined' && overlay && overlay.scene && typeof overlay.scene.getObjectByName === 'function') {

                model = overlay.scene.getObjectByName(meNationId);

            }

        } catch (e) {

            model = null;

        }

    }



    if (!model) {

        if (maxRetries > 0) {

            setTimeout(() => resetMyModelRotationAfterTalk({ maxRetries: maxRetries - 1, retryDelayMs }), retryDelayMs);

        }

        return;

    }



    try {

        // Face south: rotation.y = 0
        const desiredY = 0;

        const currentY = (model.rotation && typeof model.rotation.y === 'number') ? model.rotation.y : 0;

        if (Math.abs(currentY - desiredY) > 1e-6) {

            model.rotation.y = desiredY;

        }

        if (model.userData) {

            model.userData.__talk_is_active = false;

            model.userData.__talk_face_target_last_nation_id = '';

            model.userData.__talk_original_rotation_y = desiredY;

        }

    } catch (e) {

        console.warn('Failed to reset my model rotation after talk:', e);

        return;

    }



    try {

        if (typeof overlay !== 'undefined' && overlay && typeof overlay.requestRedraw === 'function') {

            overlay.requestRedraw();

        }

    } catch (e) {

    }

}



// Rotate the person model to face a given geographic bearing after movement.
// bearingDeg: geographic bearing in degrees (0=N, 90=E, 180=S, 270=W).
// Google Maps 3D overlay: Y is the up-axis; yaw rotation is around Y.
// The model default forward direction in the overlay points south (~+Z),
// so bearing 180 (south) needs no extra offset. Formula:
//   rotation.y = bearingRad  (bearing measured CW from north)
function rotateMyModelTowardDirection(bearingDeg, options) {
    options = options || {};
    var meNationId = (typeof nation_id_me !== 'undefined' && nation_id_me) ? String(nation_id_me).trim() : '';
    if (!meNationId) return;

    var maxRetries = (options.maxRetries !== undefined) ? Number(options.maxRetries) : 40;
    var retryDelayMs = (options.retryDelayMs !== undefined) ? Number(options.retryDelayMs) : 200;

    var mdl = null;
    try {
        mdl = (model_loaded_list && model_loaded_list[meNationId]) ? model_loaded_list[meNationId] : null;
    } catch (e) {
        mdl = null;
    }

    if (!mdl) {
        try {
            if (typeof overlay !== 'undefined' && overlay && overlay.scene && typeof overlay.scene.getObjectByName === 'function') {
                mdl = overlay.scene.getObjectByName(meNationId);
            }
        } catch (e) {
            mdl = null;
        }
    }

    if (!mdl) {
        if (maxRetries > 0) {
            setTimeout(function () { rotateMyModelTowardDirection(bearingDeg, { maxRetries: maxRetries - 1, retryDelayMs: retryDelayMs }); }, retryDelayMs);
        }
        return;
    }

    try {
        // Convert geographic bearing to radians and set rotation.y
        // In the Google Maps WebGL overlay the model faces south (+Z) by default,
        // so a bearing of 180 deg (south) corresponds to rotation.y = 0.
        // We offset by PI so that bearing 0 (north) produces rotation.y = PI.
        var bearingRad = bearingDeg * Math.PI / 180;
        mdl.rotation.y = Math.PI - bearingRad;

        // Update stored original rotation so talk-rotation logic stays consistent
        if (!mdl.userData) mdl.userData = {};
        mdl.userData.__talk_original_rotation_y = mdl.rotation.y;
    } catch (e) {
        console.warn('Failed to rotate model toward movement direction (google):', e);
        return;
    }

    try {
        if (typeof overlay !== 'undefined' && overlay && typeof overlay.requestRedraw === 'function') {
            overlay.requestRedraw();
        }
    } catch (e) {
    }
}

function loadModel(persondata) {

    const nationId = (persondata && persondata["nation_id"]) ? String(persondata["nation_id"]).trim() : '';

    if (!nationId) {

        console.warn('loadModel skipped: missing nation_id');

        return;

    }



    if (model_loaded_list && model_loaded_list[nationId]) {

        try {

            showPersonModelByNationId(nationId);

            if (typeof setPersonModelPointByNationId === 'function' && typeof getPersonPointByNationId === 'function') {

                setPersonModelPointByNationId(nationId, getPersonPointByNationId(nationId));

            }

        } catch (e) {

            console.warn('Failed to reuse loaded model:', e);

        }

        return;

    }



    if (person_model_loading_promises[nationId]) {

        return;

    }



    let url = persondata["avatar_3d"];

    let pos = persondata["location"];

    const coordinates = {

        lat: parseFloat(pos[1]),

        lng: parseFloat(pos[0]),

    };



    // Parse filename params

    let modelParams = null;



    // If not a web URL, add directory prefix and parse filename params

    if (!isWebUrl(url)) {

        // Parse params from filename

        modelParams = parseModelFilename(url);

        if (modelParams) {

            console.log(`Parsed model params:`, modelParams);

        }

        // Add directory prefix

        url = '/scripts/avatar3d/' + url;

        console.log(`Full model path: ${url}`);

    }



    // Create a new loader instance to avoid conflicts

    const personalLoader = new THREE.GLTFLoader();



    // Wrap loading process

    const loadPersonalModel = async () => {

        try {

            // Load model with retry

            const gltf = await loadModelWithRetry(personalLoader, url);

            model = gltf.scene;



            // Add lights

            const ambientLight = new THREE.AmbientLight(0xffffff, 0.1);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.1);

            directionalLight.position.set(-1, -1, -1);



            // Set model metadata

            model.name = persondata["nation_id"];

            model.userData = persondata;



            // Compute model size and scale

            const box = new THREE.Box3().setFromObject(model);

            const size = box.getSize(new THREE.Vector3());

            const height = size.y;

            console.log(`Person model height (${persondata.name}):`, height);

// alert(height);

            const desiredHeight = 150;

            let scale = desiredHeight / height;



            // If filename params exist, apply scale multiplier

            if (modelParams && modelParams.scaleMultiplier) {

                scale = scale * modelParams.scaleMultiplier;

                console.log(`Applied scale multiplier ${modelParams.scaleMultiplier}. Final scale: ${scale}`);

            } else {

                console.log("Scale:", scale);

            }



            model.scale.set(scale, scale, scale);



            // Set rotation

            if (modelParams) {

                // Use rotation params parsed from filename (convert to radians)

                model.rotation.x = THREE.MathUtils.degToRad(modelParams.rotationX);

                model.rotation.y = THREE.MathUtils.degToRad(modelParams.rotationY);

                model.rotation.z = THREE.MathUtils.degToRad(modelParams.rotationZ);

                console.log(`Applied rotation: x=${modelParams.rotationX}°, y=${modelParams.rotationY}°, z=${modelParams.rotationZ}°`);

            } else {

                // Use default rotation

                model.rotation.x = Math.PI / 30;

                model.rotation.y = (Math.PI / 1.5);

            }



            // Position model and account for altitude

            let altitudeCoordinates = coordinates;

            if (modelParams && modelParams.altitude) {

                altitudeCoordinates = {

                    lat: coordinates.lat,

                    lng: coordinates.lng,

                    altitude: modelParams.altitude

                };

                console.log(`Applied altitude: ${modelParams.altitude}`);

            }

            try {

                if (!model.userData) model.userData = {};

                model.userData.geo = {

                    lat: Number(altitudeCoordinates.lat),

                    lng: Number(altitudeCoordinates.lng),

                    altitude: Number(altitudeCoordinates.altitude) || 0,

                };

            } catch (e) {

            }

            const position2 = overlay.latLngAltitudeToVector3(altitudeCoordinates, model.position);

            console.log("Model position:", position2);



            // Add to scene

            overlay.scene.add(model);

            model_loaded_list[persondata["nation_id"]] = model;



            // Process meshes

            let modelMeshes = findMeshes(gltf.scene);

            person_model_meshes_by_nation[nationId] = modelMeshes;

            model.traverse((child) => {

                if (child.isMesh) {

                    child.cursor = 'pointer';

                    child.userData.isClickable = true;

                }

            });



            modelMeshes.forEach(mesh => {

                mesh.userData = persondata;

            });



            all_model_meshes.push(...modelMeshes);



            showPersonModelByNationId(nationId);



            // Process animations

            if (gltf.animations && gltf.animations.length > 0) {

                let mixer = new THREE.AnimationMixer(gltf.scene);



                // Determine which animation index to play

                let animIndex = 0;

                if (modelParams && modelParams.animationIndex !== undefined) {

                    animIndex = modelParams.animationIndex;

                    // Ensure index is within bounds

                    if (animIndex >= gltf.animations.length) {

                        console.warn(`Animation index ${animIndex} out of range. Using index 0`);

                        animIndex = 0;

                    }

                }



                const action = mixer.clipAction(gltf.animations[animIndex]);

                mixer.timeScale = 1;

                const duration = gltf.animations[animIndex].duration;

                action.setDuration(duration).play();

                mixers.push(mixer);

                console.log(`Person model animation started (${persondata.name}). Playing animation index: ${animIndex}`);

            }



            console.log(`Person model loaded successfully: ${persondata.name}`);

        } catch (error) {

            console.error(`Failed to load person model (${persondata.name}):`, error);

        } finally {

            try {

                delete person_model_loading_promises[nationId];

            } catch (e) {

            }

        }

    };



    person_model_loading_promises[nationId] = loadPersonalModel();

}



function removeModel(nation_id) {

    if (model_loaded_list[nation_id]) {

        model = model_loaded_list[nation_id];

        overlay.scene.remove(model);

        delete model_loaded_list[nation_id];



        try {

            geoBoundObjects.delete(model);

        } catch (e) {

        }



        const meshes = person_model_meshes_by_nation[nation_id] || [];

        if (Array.isArray(meshes) && meshes.length && Array.isArray(all_model_meshes)) {

            const toRemove = new Set(meshes);

            all_model_meshes = all_model_meshes.filter(m => !toRemove.has(m));

        }

        delete person_model_meshes_by_nation[nation_id];

        delete person_model_loading_promises[nation_id];



        console.log(`Model removed: ${nation_id}`);

    } else {

        console.warn(`Tried to remove a non-existent model: ${nation_id}`);

    }

}



function getLastClickPoint() {

    return last_click_point;

}



function getDistance(start_point, end_point) {

    return google.maps.geometry.spherical.computeDistanceBetween(start_point, end_point);

}



function getCenter() {

    return map.getCenter();

}





function updateHouseModel(position, scale, rotation) {

    // Check whether overlay and modelhouse exist

    if (typeof overlay === 'undefined' || !overlay.scene) {

        console.warn('overlay is not initialized; cannot update model');

        return;

    }



    if (typeof modelhouse === 'undefined') {

        console.warn('modelhouse is not initialized; cannot update model');

        return;

    }



    try {

        // Update model position

        const coordinates = {

            lat: parseFloat(position.lat),

            lng: parseFloat(position.lng)

        };



        try {

            if (!modelhouse.userData) modelhouse.userData = {};

            modelhouse.userData.geo = { lat: Number(coordinates.lat), lng: Number(coordinates.lng), altitude: 0 };

            geoBoundObjects.add(modelhouse);

        } catch (e) {

        }



        // Convert lat/lng to 3D scene coordinates

        const position3 = overlay.latLngAltitudeToVector3(coordinates, modelhouse.position);

        modelhouse.position.copy(position3);



        // Update model scale

        modelhouse.scale.set(scale, scale, scale);



        // Update model rotation

        modelhouse.rotation.x = rotation.x || 0;

        modelhouse.rotation.y = rotation.y || 0;

        modelhouse.rotation.z = rotation.z || 0;



        // Request redraw

        overlay.requestRedraw();



        console.log('House model updated:', {

            position: coordinates,

            scale: scale,

            rotation: rotation

        });

    } catch (error) {

        console.error('Error while updating house model:', error);

    }

}



function queryAddress() {

    // Create geocoder instance

    var address = document.getElementById("address").value;

    geocoder

        .geocode({address: address})

        .then((result) => {

            const {results} = result;

            map.setCenter(results[0].geometry.location);

            marker.setPosition(results[0].geometry.location);

            marker.setMap(map);

            init_address = address;

            const location_result = results[0].geometry.location;

            //location_result is readonly

            home_position = {

                lng: location_result.lng(),

                lat: location_result.lat(),

                altitude: 0,

                scale: 20

            };

            const home_position_str = JSON.stringify(home_position);

            update_map_setting("home_position", home_position_str)

            return results;

        })

        .catch((e) => {

            alert("Geocode was not successful for the following reason: " + e);

        });

}





function set_move_status() {



    if (instruct_to_move_flag) {

        instruct_to_move_flag = false;

        map.setOptions({

            draggableCursor: 'grab', // open hand

            draggingCursor: 'grabbing', // closed hand



        });

    } else {

        instruct_to_move_flag = true;

        map.setOptions({

            draggableCursor: 'crosshair', // default cursor

            draggingCursor: 'crosshair', // cursor while dragging

        });

        showAlert("Please click on the map to select the target position to move to.");

    }

}



var infowindow;



function __snsPostJson(path, payload) {

    try {

        const resolvedBaseUrl = (typeof API_BASE_URL !== 'undefined' && API_BASE_URL)

            ? API_BASE_URL

            : ((typeof window !== 'undefined' && window.__AGENT_SERVER__) ? window.__AGENT_SERVER__ : '');

        const normalizedBaseUrl = (resolvedBaseUrl || '').replace(/\/+$/, '');

        const url = `${normalizedBaseUrl}${path}`;

        return fetch(url, {

            method: 'POST',

            headers: {

                'Content-Type': 'application/json'

            },

            body: JSON.stringify(payload || {})

        });

    } catch (e) {

        return null;

    }

}



function __snsHumanMessage(message) {

    return __snsPostJson('/api/sns/human-message', { message: String(message || '') });

}



function __snsSendMessage(to_account, content) {

    return __snsPostJson('/api/sns/send-message', {

        to_account: String(to_account || ''),

        content: String(content || '')

    });

}



function start_talk_to_it(nation_id, content) {


    let marker = hiddenMarkers[nation_id];

    hideMarker(marker);



    // alert(map.getZoom());

    person_target_point = getPersonPointByNationId(nation_id);

    person_data_me = getPersonDataByNationId(nation_id_me);

    person_target = getPersonDataByNationId(nation_id);


    setTimeout(function () {
        map.setCenter(new google.maps.LatLng(person_target_point.lat() - 0.0025, person_target_point.lng()- 0.0025));
        showAlert("Moving to talk.");

    }, 100);
    setTimeout(function () {

        map.setZoom(16.9);

    }, 2000);
    setTimeout(function () {

        map.setTilt(90);

    }, 2500);
    setTimeout(function () {

        map.setHeading(270);

    }, 2800);



    loadModel(person_target);


    console.log("the user point:");

    console.log(person_target_point);

    console.log(person_target_point.lng);

    console.log(person_target_point.lat);

    console.log(person_target_point.lng);

    console.log(person_target_point.lat);





    my_new_point = new google.maps.LatLng(person_target_point.lat() - 0.005, person_target_point.lng());

    // alert("newpoint");

    // alert(person_target_point.lng());

    // alert(person_target_point.lat() - 0.005);

    console.log("person_target_point.lat", person_target_point.lat());

    console.log("person_target_point.latt - 0.005", person_target_point.lat() - 0.005);



    console.log("my_new_point.lat", my_new_point.lat());

    console.log("my_new_point.lng", person_target_point.lat() - 0.005);



    // infowindow.close();



    setPersonModelPointByNationId(nation_id_me, my_new_point);

    setPersonPointByNationId(nation_id_me, my_new_point.lng(), my_new_point.lat());



    try {

        if (typeof sync_current_position === 'function') {

            sync_current_position(my_new_point.lng(), my_new_point.lat(), { throttleMs: 0 });

        } else if (typeof update_location_and_open_nearest_place === 'function') {

            update_location_and_open_nearest_place(my_new_point.lng(), my_new_point.lat(), { maxDistanceM: 1000, throttleMs: 0 });

        }

    } catch (e) {

        console.warn('Failed to sync current position after talk movement:', e);

    }



    rotateMyModel180AfterTalkMove(nation_id);

    // return true;

    // var point = new BMapGL.Point(116.28882, 39.72164);

    let person_point = my_new_point;





    let hello_msg = "Hello";



    var contentString = `

    <p style='margin:0;line-height:1.5;font-size:13px;'>

    ${hello_msg}

    </p></div>`;

    // Create a <h4> element

    var h4Element = document.createElement('h4');



    // Set styles

    h4Element.style.margin = '0 0 5px 0';



    // Set text content

    h4Element.textContent = person_data_me['nick_name'];





    const offsetpoint = new google.maps.Size(20, -50);

    // infowindow = new google.maps.InfoWindow({

    //     content: contentString,

    //     ariaLabel: "Profile",

    //     headerContent: h4Element,

    //     // headerDisabled: true,

    //     position: person_point,

    //     pixelOffset: offsetpoint,

    // });

    //

    //

    //     infowindow.open({

    //         anchor: null,

    //         map,

    //     });





    // send_im(person_data_me["account"], person_target["account"], hello_msg);





    let point2 = person_target_point;



    let hello_msg2 = "Nice to meet you.";



    var contentString2 = `

    <p style='margin:0;line-height:1.5;font-size:13px;'>

    ${hello_msg2}

    </p></div>`;

    // Create a <h4> element

    var h4Element2 = document.createElement('h4');



    // Set styles

    h4Element2.style.margin = '0 0 5px 0';



    // Set text content

    h4Element2.textContent = person_target['nick_name'];





    const offsetpoint2 = new google.maps.Size(20, -50);

    // infowindow2 = new google.maps.InfoWindow({

    //     content: contentString2,

    //     ariaLabel: "Profile",

    //     headerContent: h4Element2,

    //     // headerDisabled: true,

    //     position: point2,

    //     pixelOffset: offsetpoint2,

    // });





    // setTimeout(function () {

    //     infowindow.close();

    // }, 1500);





    // setTimeout(function () {

    //     infowindow2.open({

    //         anchor: null,

    //         map,

    //     });

    // }, 1500);

    //

    //

    // setTimeout(function () {

    //     infowindow2.close();

    // }, 3000);

}



function talk_to_it(nation_id, content) {

    // content=""

    // alert(nation_id);

    let marker = hiddenMarkers[nation_id];

    hideMarker(marker);



    // alert(map.getZoom());

    person_target_point = getPersonPointByNationId(nation_id);

    person_data_me = getPersonDataByNationId(nation_id_me);

    person_target = getPersonDataByNationId(nation_id);

    setTimeout(function () {
        map.setCenter(new google.maps.LatLng(person_target_point.lat() - 0.0025, person_target_point.lng()- 0.0025));
        showAlert("Moving to talk.");

    }, 100);
    setTimeout(function () {

        map.setZoom(16.9);

    }, 2000);
    setTimeout(function () {

        map.setTilt(90);

    }, 2500);
    setTimeout(function () {

        map.setHeading(270);

    }, 2800);



    try {

        const account = (person_target && person_target["account"]) ? String(person_target["account"]).trim() : '';

        const nick_name = (person_target && person_target["nick_name"]) ? String(person_target["nick_name"]).trim() : '';

        if (account) {

            __snsPostJson('/api/sns/agent-instruction', {

                instruction: `I will communicate with ${nick_name},it's account is ${account},\n\n**Action Command:**\n\n**【3_COMMUNICATE】**:communicate with ${account}`

            });

        } else {

            console.warn('talk_to_it skipped: target account is empty', person_target);
        }

    } catch (e) {

        console.warn('talk_to_it failed to send agent instruction:', e);
    }

    loadModel(person_target);


    console.log("the user point:");

    console.log(person_target_point);

    console.log(person_target_point.lng);

    console.log(person_target_point.lat);

    console.log(person_target_point.lng);

    console.log(person_target_point.lat);





    my_new_point = new google.maps.LatLng(person_target_point.lat() - 0.005, person_target_point.lng());



    console.log("person_target_point.lat", person_target_point.lat())

    console.log("person_target_point.latt - 0.005", person_target_point.lat() - 0.005)



    console.log("my_new_point.lat", my_new_point.lat())

    console.log("my_new_point.lng", person_target_point.lat() - 0.005)



    //close the window of profile

    try {

        closeBubble();

    } catch (e) {

    }





    setPersonModelPointByNationId(nation_id_me, my_new_point);

    setPersonPointByNationId(nation_id_me, my_new_point.lng(), my_new_point.lat());



    try {

        if (typeof sync_current_position === 'function') {

            sync_current_position(my_new_point.lng(), my_new_point.lat(), { throttleMs: 0 });

        } else if (typeof update_location_and_open_nearest_place === 'function') {

            update_location_and_open_nearest_place(my_new_point.lng(), my_new_point.lat(), { maxDistanceM: 1000, throttleMs: 0 });

        }

    } catch (e) {

        console.warn('Failed to sync current position after talk movement:', e);

    }



    rotateMyModel180AfterTalkMove(nation_id);

    // return true;



    let person_point = my_new_point;





    if (false) {

        let hello_msg = "Hello";



        var contentString = `

    <p style='margin:0;line-height:1.5;font-size:13px;'>

    ${hello_msg}

    </p></div>`;

        // Create a <h4> element

        var h4Element = document.createElement('h4');



        // Set styles

        h4Element.style.margin = '0 0 5px 0';



        // Set text content

        h4Element.textContent = person_data_me['nick_name'];





        const offsetpoint = new google.maps.Size(20, -50);

        infowindow = new google.maps.InfoWindow({

            content: contentString,

            ariaLabel: "Profile",

            headerContent: h4Element,

            // headerDisabled: true,

            position: person_point,

            pixelOffset: offsetpoint,

        });





        infowindow.open({

            anchor: null,

            map,

        });





        send_im(person_data_me["account"], person_target["account"], hello_msg);





        let point2 = person_target_point;



        let hello_msg2 = "Nice to meet you.";



        var contentString2 = `

    <p style='margin:0;line-height:1.5;font-size:13px;'>

    ${hello_msg2}

    </p></div>`;

        // Create a <h4> element

        var h4Element2 = document.createElement('h4');



        // Set styles

        h4Element2.style.margin = '0 0 5px 0';



        // Set text content

        h4Element2.textContent = person_target['nick_name'];





        const offsetpoint2 = new google.maps.Size(20, -50);

        infowindow2 = new google.maps.InfoWindow({

            content: contentString2,

            ariaLabel: "Profile",

            headerContent: h4Element2,

            // headerDisabled: true,

            position: point2,

            pixelOffset: offsetpoint2,

        });





        setTimeout(function () {

            infowindow.close();

        }, 1500);





        setTimeout(function () {

            infowindow2.open({

                anchor: null,

                map,

            });

        }, 1500);





        setTimeout(function () {

            infowindow2.close();

        }, 3000);

    }

}



function stop_talk_to_it(nation_id) {

    try {

        resetMyModelRotationAfterTalk();
        map.setHeading(0);
        map.setTilt(90);

    } catch (e) {

    }



    try {

        if (typeof hidePersonModelByNationId === 'function') {

            hidePersonModelByNationId(nation_id);

        }

    } catch (e) {

    }



    try {

        if (typeof hiddenMarkers === 'undefined' || !hiddenMarkers) {

            console.warn('stop_talk_to_it skipped: hiddenMarkers not ready');

            return;

        }

        let marker = hiddenMarkers[nation_id];

        if (!marker || typeof marker.setVisible !== 'function') {

            console.warn('stop_talk_to_it skipped: marker not ready');

            return;

        }

        marker.setVisible(true);

    } catch (e) {

        console.warn('stop_talk_to_it marker restore failed:', e);

    }



    try {

        let targetAccount = '';

        try {

            if (typeof person_target !== 'undefined' && person_target && person_target["account"]) {

                targetAccount = String(person_target["account"]).trim();

            }

        } catch (e) {

        }

        if (!targetAccount) {

            try {

                const p = getPersonDataByNationId(nation_id);

                if (p && p["account"]) {

                    targetAccount = String(p["account"]).trim();

                }

            } catch (e) {

            }

        }

        if (targetAccount) {

            __snsSendMessage(targetAccount, 'TERMINATE');

        }

    } catch (e) {

    }



    try {

        closeprofile();

    } catch (e) {

    }

}





// Flag variable indicating whether an info window is currently being shown

let showing_info_flag = false;



function send_chat_msg(lng, lat, msg, send_person_name = "") {

    // Check whether an info window is currently being shown

    if (showing_info_flag) {

        console.log("Bubble is still open. Please wait...");



        // Retry later

        setTimeout(() => send_chat_msg(lng, lat, msg, send_person_name), 1000);

        return; // If showing, exit

    }



    // Set flag to true to indicate a bubble is being shown

    showing_info_flag = true;



    // Create map coordinate point

    let person_point = new google.maps.LatLng(lat, lng);



    openBubble({

        title: send_person_name || 'Message',

        body: msg,

        showClose: false,

        position: person_point,

        pixelOffset: new google.maps.Size(20, -200),

    }, map);



    // Set timer to close the bubble and reset the flag

    setTimeout(function () {

        closeBubble();

        showing_info_flag = false; // reset flag

    }, 3000);



    // Debug output

    console.log("Chat bubble opened.");

}





function showprofile(nation_id) {

    // closeBubble();



    let person_point = getPersonPointByNationId(nation_id);

    console.log("person_point");

    console.log(person_point);

    let person = getPersonDataByNationId(nation_id);



    var level = (person["level"] !== undefined && person["level"] !== null && person["level"] !== '') ? person["level"] : 1;

    var badgeHTML = '<span class="bubble-level-badge">' + level + '</span>';

    var bodyHTML = badgeHTML + person["profile"] +

        '<div style="text-align: right;"><a href="#" class="bubble-action-btn" onclick="talk_to_it(\'' + nation_id + '\',\'\');return false;">Chat</a></div>';



    openBubble({

        title: person['nick_name'],

        body: bodyHTML,

        showClose: true,

        closeAction: 'closeprofile()',

        position: person_point,

        pixelOffset: new google.maps.Size(20, -50),

    }, map);



    open_sns_profile(person['sns_url']);

}



function closeprofile() {

    closeBubble();

    close_sns_profile();

}



function showprofile3d(geoGroup) {

    let nation_id = geoGroup.userData.nation_id;

    let person_point = getPersonPointByNationId(nation_id);

    let person = geoGroup.userData;



    var level = (person["level"] !== undefined && person["level"] !== null && person["level"] !== '') ? person["level"] : 1;

    var badgeHTML = '<span class="bubble-level-badge">' + level + '</span>';

    var bodyHTML = badgeHTML + person["profile"] +

        '<div style="text-align: right;"><a href="#" class="bubble-action-btn btn-danger" onclick="stop_talk_to_it(\'' + nation_id + '\');return false;">End chat</a></div>';



    openBubble({

        title: person['nick_name'],

        body: bodyHTML,

        showClose: true,

        closeAction: 'closeprofile()',

        position: person_point,

        pixelOffset: new google.maps.Size(20, -50),

    }, map);

    overlay.requestRedraw();

}





//navigate places



var auto_navigate_flag = false;



function toggleNavigate() {

    if (auto_navigate_flag) {

        cancelNavigate();

        auto_navigate_flag = false;

    } else {

        autoNavigate();

        auto_navigate_flag = true;

    }

}



function autoNavigate() {

    console.log("auto navigate");



    // Initialize Street View

    let scene, renderer, camera, loader;





    // Move mapOptions definition inside the function

    const mapOptions = {

        tilt: 45,

        heading: 200,

        zoom: 18,

        center: {lat: 51.5009027372566, lng: -0.12384218788291879},

        disableDefaultUI: true,

        backgroundColor: 'transparent',

        gestureHandling: 'greedy',

        mapId: "b8fc4b5a8471b933",

    };

    map.setOptions(mapOptions);



    const webglOverlayView = new google.maps.WebGLOverlayView();



    webglOverlayView.onAdd = () => {

        scene = new THREE.Scene();

        camera = new THREE.PerspectiveCamera();



        const ambientLight = new THREE.AmbientLight(0xffffff, 0.75);

        scene.add(ambientLight);



        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);

        directionalLight.position.set(0.5, -1, 0.5);

        scene.add(directionalLight);



        loader = new THREE.GLTFLoader();

        const source = "cbot.glb";



        loader.load(source, function (gltf) {

            gltf.scene.scale.set(30, 30, 30);

            gltf.scene.rotation.x = Math.PI + 29.9;

            scene.add(gltf.scene);

        });

    };



    webglOverlayView.onContextRestored = ({gl}) => {

        renderer = new THREE.WebGLRenderer({

            antialias: true,

            canvas: gl.canvas,

            context: gl,

            ...gl.getContextAttributes(),

        });

        renderer.autoClear = false;



        renderer.toneMapping = THREE.ACESFilmicToneMapping; // set tone mapping

        renderer.toneMappingExposure = 2.0; // set exposure; otherwise colors are too dark



        loader.manager.onLoad = () => {

            renderer.setAnimationLoop(() => {

                webglOverlayView.requestRedraw();



                const {tilt, heading, zoom} = mapOptions;

                map.moveCamera({tilt, heading, zoom});



                if (mapOptions.tilt < 67.5) {

                    mapOptions.tilt += 0.5;

                } else if (mapOptions.heading <= 720) {

                    mapOptions.heading += 0.2;

                    mapOptions.zoom -= 0.0005;

                } else {

                    renderer.setAnimationLoop(null);

                    cancelNavigate();

                }

            });

        };

    };



    webglOverlayView.onDraw = ({gl, transformer}) => {

        const latLngAltitudeLiteral = {

            lat: mapOptions.center.lat,

            lng: mapOptions.center.lng,

            altitude: 80,

        };



        const matrix = transformer.fromLatLngAltitude(latLngAltitudeLiteral);

        camera.projectionMatrix = new THREE.Matrix4().fromArray(matrix);



        webglOverlayView.requestRedraw();

        renderer.render(scene, camera);

        renderer.resetState();

    };



    webglOverlayView.setMap(map);





}



function cancelNavigate() {

    console.log("cancel");

    auto_navigate_flag = false;

    refresh();

}



