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
    alert("nation_id_me");
    alert(nation_id_me);
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
// Load 3D models
var all_model_meshes = [];
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
                alert(url);

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
            const position = overlay.latLngAltitudeToVector3(coordinates);
            console.log("model.positiona24", model.position)
            console.log("model.positionxa24", model.position.x)
            console.log("model.positionza24", model.position.z)
            console.log("position", position)
            const position2 = overlay.latLngAltitudeToVector3(coordinates, model.position);
            console.log("position2", position2)
            console.log("model.position", model.position)
            console.log("model.positionx", model.position.x)
            console.log("model.positionz", model.position.z)

            try {
                if (typeof update_location_and_open_nearest_place === 'function') {
                    const clickLng = (coordinates && typeof coordinates.lng === 'function') ? coordinates.lng() : null;
                    const clickLat = (coordinates && typeof coordinates.lat === 'function') ? coordinates.lat() : null;
                    if (clickLng !== null && clickLat !== null) {
                        update_location_and_open_nearest_place(clickLng, clickLat, { maxDistanceM: 1000, throttleMs: 800 });
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

    const contentString = "<div style='font-size:20px'>Hello,I'm CBot.Nice to meet you.</div>";

    const offsetpoint = new google.maps.Size(20, -150);
    var infowindow = new google.maps.InfoWindow({
        content: contentString,
        ariaLabel: "Uluru",
        headerDisabled: true,
        position: {
            lat: 40.76971146231474,
            lng: -73.97265643012797,
            altitude: 520
        },
        pixelOffset: offsetpoint,
    });
    const uluru = {lat: 40.76971146231474, lng: -73.97265643012797};
    const latLngAltitudeLiteral2 = {
        lat: 40.76726879657253,
        lng: -73.97383222939642,
        altitude: 80,
    };

    function showinfo() {
        infowindow.open({
            anchor: null,
            map,
        });
    }

    function moveinfo() {
        infowindow.close();
        const contentString2 = "<div style='font-size:20px'>Nice to meet you.How can I go to AI-SNS Center.</div>";
        const offsetpoint2 = new google.maps.Size(-140, -150);
        var infowindow2 = new google.maps.InfoWindow({
            content: contentString2,
            ariaLabel: "Uluru",
            headerDisabled: true,
            position: {
                lat: 40.76971146231474,
                lng: -73.97265643012797,
                altitude: 520
            },
            pixelOffset: offsetpoint2,
        });

        const opt = {
            content: contentString2,
            ariaLabel: "Uluru",
            headerDisabled: true,
            position: {
                lat: 40.76971146231474,
                lng: -73.97265643012797,
                altitude: 520
            },
            pixelOffset: offsetpoint2,
        }
        infowindow2.open({
            anchor: null,
            map,
        });
        setTimeout(() => {
            // Close info window
            infowindow2.close();
            console.log("Info window closed"); // For debugging
        }, 2000);
    }

// Use async/await for async loading to ensure models are fully loaded before continuing
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
            modelhouse.scale.set(1, 1, 1);
            modelhouse.rotation.x = (Math.PI / 15) * 0;
            modelhouse.rotation.y = (Math.PI / 15) * 1.6;
            const position3 = overlay.latLngAltitudeToVector3(home_position, modelhouse.position);
            // Add model to scene
            overlay.scene.add(modelhouse);
            console.log("House model loaded successfully");
            modelLoadStatus.house = true;
            checkAnimationStart();
        } catch (error) {
            console.error('Failed to load house model:', error);
        }
    };
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
            model.position.set(60, 0, -250);
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
            model2.position.set(130, 0, -250);
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
        north: 39.76812,
        south: 39.74441,
        east: 116.25646,
        west: 116.22971,
    };

    playGroundOverlay = new google.maps.GroundOverlay(
        "shouhuimap.png",//"https://storage.googleapis.com/geo-devrel-public-buckets/newark_nj_1922-661x516.jpeg",
        imageBounds,
    );
    playGroundOverlay.setMap(map);


    //loadcube
    const webglOverlay = new google.maps.WebGLOverlayView();
    const cubePosition = { lat: 39.931188733629675, lng: 116.36270578593066 };

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
        if (mousePosition.x != 0 && mousePosition.y != 0) {
            var intersections = overlay.raycast(mousePosition, all_model_meshes, {
                recursive: false,
            });
            if (highlightedObject) {
                console.log("Highlight cleared");
                console.log("Mouse position:", mousePosition);
            }
            if (intersections.length === 0) {
                highlightedObject = null;
                return;
            }
            highlightedObject = intersections[0].object;
            highlightedObject.material.color.setHex(HIGHLIGHT_COLOR);// pause color changes
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

function loadModel(persondata) {
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
alert(height);
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
            const position2 = overlay.latLngAltitudeToVector3(altitudeCoordinates, model.position);
            console.log("Model position:", position2);

            // Add to scene
            overlay.scene.add(model);
            model_loaded_list[persondata["nation_id"]] = model;

            // Process meshes
            let modelMeshes = findMeshes(gltf.scene);
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
        }
    };

    // Execute loading
    loadPersonalModel();
}

function removeModel(nation_id) {
    if (model_loaded_list[nation_id]) {
        model = model_loaded_list[nation_id];
        overlay.scene.remove(model);
        delete model_loaded_list[nation_id];
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

function start_talk_to_it(nation_id, content) {
    // ... (rest of the code remains the same)
    // content=""
    // alert("start_talk_to_it");
    alert(nation_id);
    let marker = hiddenMarkers[nation_id];
    hideMarker(marker);

    // alert(map.getZoom());
    person_target_point = getPersonPointByNationId(nation_id);
    person_data_me = getPersonDataByNationId(nation_id_me);
    person_target = getPersonDataByNationId(nation_id);
    loadModel(person_target);


    alert(person_data_me["account"]);
    alert(person_target["account"]);
    // map.setHeading(0);
    // map.setTilt(0);
    console.log("the user point:");
    console.log(person_target_point);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);


    my_new_point = new google.maps.LatLng(person_target_point.lat() - 0.01, person_target_point.lng());
    alert("newpoint");
    alert(person_target_point.lng());
    alert(person_target_point.lat() - 0.01);
    console.log("person_target_point.lat", person_target_point.lat());
    console.log("person_target_point.latt - 0.01", person_target_point.lat() - 0.01);

    console.log("my_new_point.lat", my_new_point.lat());
    console.log("my_new_point.lng", person_target_point.lat() - 0.01);

    // infowindow.close();

    setPersonModelPointByNationId(nation_id_me, my_new_point);
    setPersonPointByNationId(nation_id_me, my_new_point.lng(), my_new_point.lat());
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
    alert(nation_id);
    let marker = hiddenMarkers[nation_id];
    hideMarker(marker);

    // alert(map.getZoom());
    person_target_point = getPersonPointByNationId(nation_id);
    person_data_me = getPersonDataByNationId(nation_id_me);
    person_target = getPersonDataByNationId(nation_id);
    loadModel(person_target);


    alert(person_data_me["account"]);
    alert(person_target["account"]);
    // map.setHeading(0);
    // map.setTilt(0);
    console.log("the user point:");
    console.log(person_target_point);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);


    my_new_point = new google.maps.LatLng(person_target_point.lat() - 0.01, person_target_point.lng());

    console.log("person_target_point.lat", person_target_point.lat())
    console.log("person_target_point.latt - 0.01", person_target_point.lat() - 0.01)

    console.log("my_new_point.lat", my_new_point.lat())
    console.log("my_new_point.lng", person_target_point.lat() - 0.01)

    //close the window of profile
    infowindow.close();


    setPersonModelPointByNationId(nation_id_me, my_new_point);
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

function stop_talk_to_it(nation_id) {
    try {
        if (typeof removeModel === 'function') {
            removeModel(nation_id);
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
        if (typeof infowindow !== 'undefined' && infowindow && typeof infowindow.close === 'function') {
            infowindow.close();
        }
    } catch (e) {
    }
}


// Flag variable indicating whether an info window is currently being shown
let showing_info_flag = false;

function send_chat_msg(lng, lat, msg, send_person_name = "") {
    // Check whether an info window is currently being shown
    if (showing_info_flag) {
        console.log("Info window is still open. Please wait...");

        // Retry later
        setTimeout(() => send_chat_msg(lng, lat, msg, send_person_name), 1000);
        return; // If showing, exit
    }

    // Set flag to true to indicate an info window is being shown
    showing_info_flag = true;

    // Create map coordinate point

    let person_point = new google.maps.LatLng(lat, lng);

    var contentString = `
    <p style='margin:0;line-height:1.5;font-size:13px;'>
    ${msg}

    </p></div>`;

    // Create a <h4> element
    var h4Element = document.createElement('h4');

    // Set styles
    h4Element.style.margin = '0 30px 5px 0';

    // Set text content
    if (send_person_name) {
        h4Element.textContent = send_person_name;
    } else {
        h4Element.textContent = "Message";
    }


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

    // Set timer to close the info window and reset the flag
    setTimeout(function () {
        infowindow.close(); // close info window
        showing_info_flag = false; // reset flag
    }, 3000);

    // Debug output
    console.log("Info window opened.");
}


function showprofile(nation_id) {
    if (infowindow) {
        infowindow.close();
    }

    let person_point = getPersonPointByNationId(nation_id);
    console.log("person_point");
    console.log(person_point);
    let person = getPersonDataByNationId(nation_id);
    var contentString = `
<div style="display: flex; justify-content: space-between; align-items: center; margin: 0; line-height: 1.5; font-size: 13px; color: black;">
    <span style="font-weight: bold;corlor:black; cursor: pointer;" >${person['nick_name']}</span>
    <span style="cursor: pointer;color:black;"  onclick="closeprofile()">X</span>
</div>

    ${person["profile"]}
    <a href="#" onclick="talk_to_it('${nation_id}','');return false;">Chat</a>
    </p></div>`;
    // Create a <h4> element
    // var h4Element = document.createElement('h4');
    var h4Element = document.createElement('div');

    // Set styles
    h4Element.style.margin = '0 0 5px 0';

    // Set text content
    h4Element.textContent = person['nick_name'];


    const offsetpoint = new google.maps.Size(20, -50);
    infowindow = new google.maps.InfoWindow({
        content: contentString,
        ariaLabel: "Profile",
        headerContent: h4Element,
        headerDisabled: true,
        position: person_point,
        pixelOffset: offsetpoint,
    });

    infowindow.open({
        anchor: null,
        map,
    });

    open_sns_profile(person['sns_url']);

}

function closeprofile() {
    infowindow.close();
    close_sns_profile()
}

function showprofile3d(geoGroup) {
    let nation_id = geoGroup.userData.nation_id;
    let person_point = getPersonPointByNationId(nation_id);
    let person = geoGroup.userData;
    var contentString = `
    <p style='margin:0;line-height:1.5;font-size:13px;text-indent:2em'>
    ${person["profile"]}
    <a href="#" onclick="stop_talk_to_it('${nation_id}');return false;">End chat</a>
    </p></div>`;
// Create a <h4> element
    var h4Element = document.createElement('h4');

    // Set styles
    h4Element.style.margin = '0 0 5px 0';

    // Set text content
    h4Element.textContent = person['nick_name'];


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

