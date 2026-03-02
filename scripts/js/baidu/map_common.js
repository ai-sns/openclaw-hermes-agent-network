// todo
// Delay initializing the map center until current_position is set
function initializeMapCenter() {
    var centerPoint;
    // Prefer global current_position if present and has valid lng/lat
    if (typeof window.current_position !== 'undefined' && window.current_position !== null &&
        typeof window.current_position.lng !== 'undefined' && typeof window.current_position.lat !== 'undefined') {
        centerPoint = new BMapGL.Point(window.current_position.lng, window.current_position.lat);
        console.log("Initialize the map using the configured location:", window.current_position);
    } else {
        centerPoint = new BMapGL.Point(116.28882, 39.71164);
        console.log("Initialize the map using the default location.");
    }

    map.centerAndZoom(centerPoint, 16);
}

// If current_position already exists, initialize immediately; otherwise wait
if (typeof window.current_position !== 'undefined' && window.current_position !== null) {
    initializeMapCenter();
} else {
    // Delay execution until current_position is set (set in interact_python)
    console.log("Waiting for current_position to initialize...");
}
map.setHeading(90);
map.setTilt(80);
map.enableKeyboard();
map.enableScrollWheelZoom();
map.enableInertialDragging();
map.enableContinuousZoom();
driving = new BMapGL.DrivingRouteLine(map, {
    renderOptions: {
        map: map,
        autoViewport: true,
        enableDragging: true,
    },
    onSearchComplete: function (result) {
        if (driving.getStatus() === BMAP_STATUS_SUCCESS || driving.getStatus() === 5) {
            alert("Planning successful, number of coordinates:");
            alert(result);
            console.log("Planning successful, number of coordinates:", result);

            // Get the route plan
            const plan = result.getPlan(0);
            if (plan) {
                alert("Distance and duration");
                distance = plan.getDistance(true);
                duration = plan.getDuration(true);
                alert(distance);
                alert(duration);

                // Convert distance to a float and compute move_duration
                // First extract numeric value from strings like "35.5km"
                var distanceValue = parseFloat(String(distance).replace(/[^\d\.]/g, ''));
                if (!isNaN(distanceValue)) {
                    move_duration = distanceValue / 0.05;
                }
            }

            gpsPositions = getAllGpsPositions(result);
            console.log("Planning successful, number of coordinates:", gpsPositions.length);

            const start = document.getElementById("start").value.trim();
            const end = document.getElementById("end").value.trim();

            // Save start/end to backend
            update_map_setting("route_start", start);
            update_map_setting("route_end", end);

            // Update route status to playing
            route_status = "playing";
            update_map_setting("route_status", route_status);

            // Only user-initiated route planning resets progress/current position
            // Auto planning (e.g. on page load) keeps previous progress
            if (isUserInitiatedRoutePlanning) {
                update_map_setting("route_current_position", "");
                update_map_setting("route", "");
                // Reset flag
                isUserInitiatedRoutePlanning = false;
            }

            // Get start/end input elements
            const startInput = document.getElementById('start');
            const endInput = document.getElementById('end');
            const msgdiv = document.getElementById("setroute");
            const positionTypeSelect = document.getElementById("position_type");
            const startCoordLink = document.getElementById("start_coord_link");
            const endCoordLink = document.getElementById("end_coord_link");

            // Make inputs read-only
            if (startInput) startInput.setAttribute('readonly', 'readonly');
            if (endInput) endInput.setAttribute('readonly', 'readonly');

            // Show view/reset buttons, hide confirm button
            if (msgdiv) {
                const buttons = msgdiv.getElementsByTagName('button');
                for (let i = 0; i < buttons.length; i++) {
                    const button = buttons[i];
                    const buttonText = button.textContent.trim();
                    if (buttonText === 'Confirm') {
                        button.style.display = 'none';
                    } else if (buttonText === 'View' || buttonText === 'Reset') {
                        button.style.display = 'inline-block';
                    }
                }
            }

            // Hide position_type select and coordinate links
            if (positionTypeSelect) positionTypeSelect.style.display = 'none';
            if (startCoordLink) startCoordLink.style.display = 'none';
            if (endCoordLink) endCoordLink.style.display = 'none';

            // Only update menu checkmarks after route planning succeeds
            const randomRouteItem = document.getElementById("random_route");
            const specifiedRouteItem = document.getElementById("specified_route");
            if (randomRouteItem && specifiedRouteItem) {
                // Remove ✓ from random route
                randomRouteItem.textContent = randomRouteItem.textContent.replace(' ✓', '');
                // Add ✓ to specified route
                if (!specifiedRouteItem.textContent.includes('✓')) {
                    specifiedRouteItem.textContent += ' ✓';
                }
            }
        } else {
            // Route planning failed; do not update status or UI
            alert("Route planning failed, status code:" + driving.getStatus());
        }
    }
});


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
            console.log(`Remaining retry attempts: ${retriesLeft}`);

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
                console.warn(`Request failed, error: ${error.message}. Remaining retries: ${retriesLeft}. Retrying in ${delay} ms...`);
                showAlert(`Failed to fetch data, remaining retries: ${retriesLeft}. Retrying in ${delay} ms...`);
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
    try {
        const data = await loadPersonsData(dataUrl); // Load person data
        console.log("Successfully loaded personnel data:", data);
        showAlert(`User data loaded successfully.`);

        // Filter out items whose nation_id equals the input value
        personsdata = data.filter(person => {
            const pid = (person && (person.nation_id || person.nationid)) ? String(person.nation_id || person.nationid).trim() : '';
            return pid !== String(nation_id || '').trim();
        });

        // Show updated data points
        showpoints();
    } catch (error) {
        console.error("Failed to load personnel data, suggestion:",
            error.name === 'AbortError'
                ? 'Check your network connection or try again later'
                : 'Check your computer.');
    }
}

// Initialize 3D view
var view = new mapvgl.View({map: map});
var threeLayer = new mapvgl.ThreeLayer({notUpdateSize: false});
view.addLayer(threeLayer);

// Test threeLayer click event
// threeLayer.addEventListener('click', function(e) {
//     console.log('threeLayer click event triggered!', e);
// });

// Add lights
var lights = [];
lights[0] = new THREE.PointLight(0xffffff, 1, 0);
lights[0].position.set(0, -1000, 1000);
threeLayer.scene.add(lights[0]);

// Animation loop
var clock = new THREE.Clock();
var mixers = []; // Stores animation mixers
var meshes = []; // Stores all Mesh instances
var geoGroups = []; // Stores all THREE.Group instances
var person_gltfLoader = new mapvgl.THREELoader.GLTFLoader();

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
        console.warn(`Filename has fewer than 6 parameters: ${filename}, found ${params.length} parameters`);
        return null;
    }

    // Parse scale parameter (5th number, index 4)
    // If it starts with 0, treat as decimal, e.g. 05 => 0.5
    let scaleMultiplier = 1;
    const scaleParam = params[4];
    if (scaleParam.startsWith('0') && scaleParam.length > 1) {
        // Starts with 0: convert to decimal
        scaleMultiplier = parseFloat('0.' + scaleParam.substring(1));
        scaleMultiplier = scaleMultiplier*10;
    } else {
        scaleMultiplier = parseFloat(scaleParam);
    }

    return {
        rotationX: parseFloat(params[0]) || 0,      // 1st number: X rotation (degrees)
        rotationY: parseFloat(params[1]) || 0,      // 2nd number: Y rotation (degrees)
        rotationZ: parseFloat(params[2]) || 0,      // 3rd number: Z rotation (degrees)
        altitude: parseFloat(params[3]) || 0,       // 4th number: altitude
        scaleMultiplier: scaleMultiplier,     // 5th number: scale multiplier (Baidu is ~1.8x smaller than Google)
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

// GLTF model loader
function loadModel(persondata) {
    let url = persondata["avatar_3d"];
    let pos = persondata["location"];
    let llPoint = new BMapGL.Point(pos[0], pos[1]);
    console.log("llPoint", llPoint);
    const mcpoint = BMapGL.Projection.convertLL2MC(llPoint);
    console.log("mcpoint", mcpoint)

    // Parse filename params
    let modelParams = null;

    // If not a web URL, add directory prefix and parse filename params
    if (!isWebUrl(url)) {
        // Parse params from filename
        modelParams = parseModelFilename(url);
        if (modelParams) {
            console.log(`Parsed model parameters:`, modelParams);
        }
        // Add directory prefix
        url = '/scripts/avatar3d/' + url;
        console.log(`Full model path: ${url}`);
    }

    person_gltfLoader.load(url, function (obj) {
        let model = obj.scene;
        model.rotateX(90 / 180 * Math.PI); // Rotate model

        // Compute model bounding box
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const height = size.y; // Model height
        alert(height);
        console.log("the height33:", height);
        // Get model bounding box

        const modelHeight = box.max.y - box.min.y;
        console.log("the modelHeight333:", modelHeight);

        // Adjust scale based on height
        const desiredHeight = 150; // Desired height
        let scale = desiredHeight / height;


        // If filename params exist, apply scale multiplier
        if (modelParams && modelParams.scaleMultiplier) {
            scale = scale * modelParams.scaleMultiplier;
            console.log(`Applied scale multiplier ${modelParams.scaleMultiplier}, final scale: ${scale}`);
        } else {
            console.log("scale", scale);
        }


        // Set model scale/rotation/position
        model.scale.set(scale, scale, scale);

        let geoGroup = new THREE.Group();
        geoGroup.add(model);

        // Position model and account for altitude
        let altitude = 0;
        if (modelParams && modelParams.altitude) {
            altitude = modelParams.altitude;
            console.log(`Applied altitude: ${altitude}`);
        }
        geoGroup.position.set(mcpoint.lng, mcpoint.lat, altitude);

        // Set rotation
        if (modelParams) {
            // Use rotation params parsed from filename (convert to radians)
            // Note: in Baidu map the model has already been rotated 90 degrees (rotateX(90 / 180 * Math.PI))
            model.rotation.x += THREE.MathUtils.degToRad(modelParams.rotationX) - Math.PI / 30;
            model.rotation.y = THREE.MathUtils.degToRad(modelParams.rotationY);
            model.rotation.z = THREE.MathUtils.degToRad(modelParams.rotationZ);
            console.log(`Applied rotation: x=${modelParams.rotationX}°, y=${modelParams.rotationY}°, z=${modelParams.rotationZ}°`);
        } else {
            // Default rotation: tilt the head slightly upward
            model.rotation.x -= Math.PI / 30;
        }

        console.log("mcpoint.lng", mcpoint.lng);
        console.log("mcpoint.lat", mcpoint.lat);
        geoGroup.name = persondata["nation_id"];
        geoGroup.userData = persondata;
        threeLayer.add(geoGroup);
        geoGroups.push(geoGroup); // Add geoGroup to array

        // Process animations
        if (obj.animations && obj.animations.length > 0) {
            let mixer = new THREE.AnimationMixer(obj.scene);

            // Determine which animation index to play
            let animIndex = 0;
            if (modelParams && modelParams.animationIndex !== undefined) {
                animIndex = modelParams.animationIndex;
                // Ensure index is within bounds
                if (animIndex >= obj.animations.length) {
                    console.warn(`Animation index ${animIndex} is out of range, using index 0`);
                    animIndex = 0;
                }
            }

            const action = mixer.clipAction(obj.animations[animIndex]);
            mixer.timeScale = 0.5;
            const duration = obj.animations[animIndex].duration || 1;
            action.setDuration(duration).play();
            mixers.push(mixer); // Add mixer to array
            console.log(`Model animation started, playing animation index: ${animIndex}`);
        }

        let modelMeshes = findMeshes(model); // Find all Mesh
        modelMeshes.forEach(mesh => {
            mesh.userData = persondata; // Bind dataset to each Mesh.userData
        });
        meshes.push(...modelMeshes); // Add to global meshes array
    });
}

function removeModel(nation_id) {
    const groupIndex = geoGroups.findIndex(group => group.name === nation_id);

    if (groupIndex !== -1) {
        // Remove geoGroup from threeLayer
        threeLayer.remove(geoGroups[groupIndex]);
        // Remove geoGroup from geoGroups array
        geoGroups.splice(groupIndex, 1);
    }

    //  currentModel = threeLayer.scene.getObjectByName(nation_id);
    //
    // threeLayer.remove(currentModel);

    // If you want to hide the model (instead of deleting)
    // currentModel.visible = false;
}

// Find all Mesh
function findMeshes(object) {
    const meshes = [];
    object.traverse((child) => {
        if (child.isMesh) {
            meshes.push(child);
        }
    });
    return meshes;
}

// Click event handling
var raycaster = new THREE.Raycaster();
var mouse = new THREE.Vector2();
var currentModel = null;

map.addEventListener('click', function (e) {
    mouse.x = (e.x / window.innerWidth) * 2 - 1;
    mouse.y = -(e.y / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, threeLayer.camera);

    // Use the collected Mesh objects for hit-testing
    // const intersects = raycaster.intersectObjects([...meshes1, ...meshes2], true);
    const intersects = raycaster.intersectObjects([...meshes], true);

    if (intersects.length > 0) {
        const intersectedObject = intersects[0].object;
        alert(intersectedObject.userData.nation_id);
        alert(intersectedObject.userData["nation_id"]);
        nation_id = intersectedObject.userData.nation_id;
        currentModel = threeLayer.scene.getObjectByName(nation_id);
        showprofile3d(currentModel);


    } else {

        currentModel = null;
    }
});

map.addEventListener('click', function (e) {
    alert("in clicking");
    if (instruct_to_move_flag == true) {


        my_point = getPersonPointByNationId(nation_id_me);

        alert('My current coordinates: ' + my_point.lng + ',' + my_point.lat);

        alert('Clicked coordinates: ' + e.latlng.lng + ',' + e.latlng.lat);


        last_click_point = new BMapGL.Point(e.latlng.lng, e.latlng.lat);

        distance = map.getDistance(my_point, last_click_point);
        alert('Distance from current location to clicked point: ' + distance);


        centerpoint = map.getCenter();
        alert('Map center coordinates: ' + centerpoint.lng + ',' + centerpoint.lat);


        Viewport = map.getViewport();
        viewcenter = Viewport.center;
        alert('Viewport center coordinates: ' + viewcenter.lng + ',' + viewcenter.lat);

        // var list = cusLayer.getCustomOverlays();
        // console.log(list[0]);
        // list[0].setPoint(new BMapGL.Point(e.latlng.lng, e.latlng.lat), false);
        //
        // mercatorPoint = new BMapGL.Point(e.latlng.lng, e.latlng.lat);
        // console.log("mercatorPoint", mercatorPoint);
        // const geoCoord2 = BMapGL.Projection.convertLL2MC(mercatorPoint);
        // console.log("geoCoord2", geoCoord2)
        //
        //
        // currentAircraft.position.set(geoCoord2.lng, geoCoord2.lat, 0);
        //
        //
        // console.log(list[0]);

        setPersonModelPointByNationId(nation_id_me, e.latlng);
        setPersonPointByNationId(nation_id_me, e.latlng.lng, e.latlng.lat);

        try {
            if (typeof update_location_and_open_nearest_place === 'function') {
                update_location_and_open_nearest_place(e.latlng.lng, e.latlng.lat, { maxDistanceM: 1000, throttleMs: 800 });
            }
        } catch (err) {
            console.warn('Failed to sync location to backend:', err);
        }

        service = getServiceForUser();
        if (service !== null) {
            const userConfirmed = confirm("There is an associated app service here. Do you want to continue?");
            if (userConfirmed) {
                alert("You clicked OK.");
                open_place_web_address(service.address);
            } else {
                return;
            }

        }

        // map.setDefaultCursor("url(http://webmap0.bdimg.com/image/api/openhand.cur) 8 8,default");
        // instruct_to_move_flag = false;
        map.cancelViewAnimation(animation);

    }
});
// Listen for zoom events
map.addEventListener("zoomend", function () {
    // Get current zoom level
    var currentZoom = map.getZoom();

    // Log current zoom level
    // alert("Current zoom level: " + currentZoom);
    console.log("Current zoom level: " + currentZoom);

    // You can add additional logic here, e.g. update data based on zoom level
});

function getAllGroups(scene) {
    const groups = [];
    scene.traverse((object) => {
        if (object.isGroup) { // Check whether it's a THREE.Group
            groups.push(object);
        }
    });
    return groups;
}

function checkAnimationStart() {
    if (animationStarted) return;

    if (modelLoadStatus.building) {

        animate(0);
        animationStarted = true;
        console.log("All models finished loading, starting animation");
    }
}


function updateHouseModel(position, scale, rotation) {
    // If threeLayer is not defined, return early
    if (typeof threeLayer === 'undefined' || !threeLayer.scene) {
        console.warn('threeLayer not initialized, cannot update model');
        return;
    }

    // Debug: list all objects in the scene
    console.log('Scene objects:');
    threeLayer.scene.traverse(function(object) {
        console.log('Object name:', object.name, 'Type:', object.type);
    });

    // Find houseModel Group in the scene (note: this is a Group, not the model itself)
    let houseModelGroup = threeLayer.scene.getObjectByName('houseModel');

    // If not found by name, try alternative search
    if (!houseModelGroup) {
        threeLayer.scene.traverse(function(object) {
            if (object.name && object.name.includes('house')) {
                houseModelGroup = object;
                console.log('Found house-related object:', object.name);
            }
        });
    }

    if (houseModelGroup) {
        console.log('Found houseModelGroup:', houseModelGroup);

        // Convert coordinates (same approach as reference code)
        const llPoint = new BMapGL.Point(position.lng, position.lat);
        const mercatorPoint = BMapGL.Projection.convertLL2MC(llPoint);
        console.log("mercatorPoint", mercatorPoint);

        // Update Group position (model is inside Group; Group position is the model map position)
        houseModelGroup.position.set(mercatorPoint.lng, mercatorPoint.lat, 0);

        // Ensure Group is visible
        houseModelGroup.visible = true;

        // Update scale of the model inside the Group
        if (houseModelGroup.children.length > 0) {
            const model = houseModelGroup.children[0];
            model.scale.set(scale, scale, scale);

            // Update model rotation (keep the original Math.PI / 2 offset)
            model.rotation.x = (rotation.x || 0) + Math.PI / 2;
            model.rotation.y = rotation.y || 0;
            model.rotation.z = rotation.z || 0;

            // Ensure model is visible
            model.visible = true;
        }

        // Re-render
        threeLayer.render();

        console.log('House model updated:', {
            position: {lng: position.lng, lat: position.lat},
            mercator: {lng: mercatorPoint.lng, lat: mercatorPoint.lat},
            scale: scale,
            rotation: rotation
        });

        // Debug: check whether model is within viewport
        const mapCenter = map.getCenter();
        const mapZoom = map.getZoom();
        console.log('Map center:', mapCenter, 'Zoom:', mapZoom);
        console.log('Model position:', mercatorPoint);

        // Compute distance between model and map center
        const centerMercator = BMapGL.Projection.convertLL2MC(new BMapGL.Point(mapCenter.lng, mapCenter.lat));
        const distance = Math.sqrt(
            Math.pow(mercatorPoint.lng - centerMercator.lng, 2) +
            Math.pow(mercatorPoint.lat - centerMercator.lat, 2)
        );
        console.log('Distance from center (mercator units):', distance);

        // Check model bounds
        const box = new THREE.Box3().setFromObject(houseModelGroup);
        console.log('Model bounding box:', box);

        // Check model matrix
        console.log('Model matrix:', houseModelGroup.matrix);
    } else {
        console.warn('houseModel group not found');

        // List all objects for confirmation
        console.log('All objects in scene:');
        threeLayer.scene.traverse(function(object) {
            console.log('Name:', object.name, 'Type:', object.type);
        });
    }
}

function queryAddress() {
    // Create geocoder instance
    var address = document.getElementById("address").value;
    var myGeo = new BMapGL.Geocoder();
    if (marker) {
        map.removeOverlay(marker);
    }
    // Show geocoding result on the map and adjust viewport
    myGeo.getPoint(address, function (point) {
        if (point) {
            map.centerAndZoom(point, 16);
            marker = new BMapGL.Marker(point);
            map.addOverlay(marker);
            init_address = address;
            home_position = point;
        } else {
            alert('Address not resolved!');
        }
    }, '')

}



function set_move_status() {

    if (instruct_to_move_flag) {
        instruct_to_move_flag = false;
        map.setDefaultCursor("url(http://webmap0.bdimg.com/image/api/openhand.cur) 8 8,default");
    } else {
        instruct_to_move_flag = true;
        document.body.classList.toggle('crosshair-cursor');
        // Set map container cursor to crosshair
        document.getElementById('map').classList.add('crosshair-cursor');
        alert(map.getDefaultCursor());
        map.getDefaultCursor();
        map.setDefaultCursor("crosshair");
        showAlert("Please click on the map to select the destination to move to.");
    }

}

var opts = {
    width: 200,     // Info window width 200
    height: 100,     // Info window height 100
    title: "", // Info window title
    offset: new BMapGL.Size(30, -50),
}

var infoWindow = new BMapGL.InfoWindow("Hi, I'm YBot", opts);  // Create info window object

var infoWindow2 = new BMapGL.InfoWindow("Hello!", opts);  // Create info window object

function start_talk_to_it(nation_id, content) {
    // div = hiddenPoints[nation_id];
    // div.style.display = 'none';
    alert(nation_id);
    alert(map.getZoom());
    person_target_point = getPersonPointByNationId(nation_id);
    person_data_me = getPersonDataByNationId(nation_id_me);
    person_target = getPersonDataByNationId(nation_id);

    loadModel(person_target);


    let person = getPersonDataByNationId(nation_id);
    alert(person_data_me["account"]);
    alert(person_target["account"]);
    map.setHeading(0);
    // map.setTilt(0);
    console.log("the user point:");
    console.log(person_target_point);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);
    // cusLayer.updateData(personsdata2);

    my_new_point = new BMapGL.Point(person_target_point.lng, person_target_point.lat - 0.01);

    setPersonModelPointByNationId(nation_id_me, my_new_point);
    setPersonPointByNationId(nation_id_me,my_new_point.lng,my_new_point.lat);

    div = document.getElementById(nation_id);
            if (!div) {
                console.warn(`Element with ID ${nation_id} not found on map`);
                return;
            }
            hiddenPoints[param_1] = div;
div = hiddenPoints[nation_id];
    div.style.display = 'none';
}

function talk_to_it(nation_id, content) {
    div = hiddenPoints[nation_id];
    div.style.display = 'none';
    alert(nation_id);
    alert(map.getZoom());
    person_target_point = getPersonPointByNationId(nation_id);
    person_data_me = getPersonDataByNationId(nation_id_me);
    person_target = getPersonDataByNationId(nation_id);

    loadModel(person_target);


    let person = getPersonDataByNationId(nation_id);
    alert(person_data_me["account"]);
    alert(person_target["account"]);
    map.setHeading(0);
    // map.setTilt(0);
    console.log("the user point:");
    console.log(person_target_point);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);
    console.log(person_target_point.lng);
    console.log(person_target_point.lat);
    // cusLayer.updateData(personsdata2);

    my_new_point = new BMapGL.Point(person_target_point.lng, person_target_point.lat - 0.01);

    setPersonModelPointByNationId(nation_id_me, my_new_point);
    // var point = new BMapGL.Point(116.28882, 39.72164);
    let point = my_new_point;

    let opts = {
        width: 200,     // Info window width 200
        height: 100,     // Info window height 100
        title: person_data_me["nick_name"], // Info window title
        offset: new BMapGL.Size(30, -70),
    }
    let hello_msg = "Hello";
    let infoWindow_me = new BMapGL.InfoWindow(hello_msg, opts);  // Create info window object

    map.openInfoWindow(infoWindow_me, point); // Open info window
    if (content != "__no_info_window__") {

        send_im(person_data_me["account"], person_target["account"], hello_msg);
    }
    // var point2 = new BMapGL.Point(116.28882, 39.71564);
    point2 = person_target_point;

    let opts2 = {
        width: 200,     // Info window width 200
        height: 100,     // Info window height 100
        title: person_target["nick_name"], // Info window title
        offset: new BMapGL.Size(30, -70),
    }


    // Use setTimeout to delay opening the second info window by 1.5s
    let infoWindow_person_target = new BMapGL.InfoWindow("Nice to meet you.", opts2);  // Create info window object


        setTimeout(function () {
            map.openInfoWindow(infoWindow_person_target, point2);
        }, 1500);


        setTimeout(function () {
            map.closeInfoWindow();
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
        if (typeof hiddenPoints === 'undefined' || !hiddenPoints) {
            console.warn('stop_talk_to_it skipped: hiddenPoints not ready');
            return;
        }
        const div = hiddenPoints[nation_id];
        if (!div || !div.style) {
            console.warn('stop_talk_to_it skipped: hidden point not ready');
            return;
        }
        div.style.display = 'block';
    } catch (e) {
        console.warn('stop_talk_to_it restore failed:', e);
    }

    try {
        if (typeof map !== 'undefined' && map && typeof map.closeInfoWindow === 'function') {
            map.closeInfoWindow();
        }
    } catch (e) {
    }
}


// Flag variable indicating whether an info window is currently being shown
let showing_info_flag = false;

function send_chat_msg(lng, lat, msg,send_person_name="") {
    // Check whether an info window is currently being shown
    if (showing_info_flag) {
        console.log("The info window is still showing. Please wait...");

        // Retry later
        setTimeout(() => send_chat_msg(lng, lat, msg,send_person_name), 1000);
        return; // If showing, exit
    }

    // Set flag to true to indicate an info window is being shown
    showing_info_flag = true;

    // Create map coordinate point
    var point = new BMapGL.Point(lng, lat);


    let opts = {
    width: 200,     // Info window width 200
    height: 100,     // Info window height 100
    title: send_person_name, // Info window title
    offset: new BMapGL.Size(30, -50),
}

let infoWindow_chat = new BMapGL.InfoWindow(msg, opts);  // Create info window object




    // Open info window
    map.openInfoWindow(infoWindow_chat, point);

    // Set timer to close the info window and reset the flag
    setTimeout(function () {
        map.closeInfoWindow(); // close info window
        showing_info_flag = false; // reset flag
    }, 3000);

    // Debug output
    console.log("Info window opened.");
}



function showprofile(nation_id) {
    alert("showprofile");

    let person_point = getPersonPointByNationId(nation_id);
    alert("person_point");
    console.log("person_point");
    console.log(person_point);
    let person = getPersonDataByNationId(nation_id);
    var sContent = `
    <p style='margin:0;line-height:1.5;font-size:13px;text-indent:2em'>
    ${person["profile"]}
    <a href="#" onclick="talk_to_it('${nation_id}','');return false;">Chat</a>
    </p></div>`;
    alert("showprofile22");
    var opts = {
        width: 200,     // Info window width 200
        height: 100,     // Info window height 100
        title: `<h4 style='margin:0 0 5px 0;'>${person["nick_name"]}</h4>`, // Info window title
        offset: new BMapGL.Size(30, -50),
    }
    let profile_info_window = new BMapGL.InfoWindow(sContent, opts);
    alert("showprofile2333cjrok");
    // Listen for InfoWindow close event
profile_info_window.addEventListener("close", function() {
    // Code to run when the InfoWindow is closed
    alert(1);
    closeprofile();
});

    // var point = new BMapGL.Point(116.28882, 39.72164);
    var point = getPersonPointByNationId(nation_id);
    console.log("the point", point)
    map.openInfoWindow(profile_info_window, point); // Open InfoWindow
    // map.openInfoWindow(profile_info_window, point); // Open InfoWindow
    // map.openInfoWindow(profile_info_window, point); // Open InfoWindow
    // map.openInfoWindow(infoWindow3, point); // Open InfoWindow
    // map.openInfoWindow(infoWindow3, point); // Open InfoWindow
    alert("showprofile444");
    open_sns_profile(person['sns_url']);

}

function closeprofile(){
    // map.closeInfoWindow();
    alert("closing");
    close_sns_profile()
}

function showprofile3d(geoGroup) {
    nation_id = geoGroup.userData.nation_id;
    let person = geoGroup.userData;
    var sContent = `<h4 style='margin:0 0 5px 0;'>${person["nick_name"]}</h4>
    <p style='margin:0;line-height:1.5;font-size:13px;text-indent:2em'>
    ${person["profile"]}
    <a href="#" onclick="stop_talk_to_it('${nation_id}');return false;">End chat</a>
    </p></div>`;

    var opts = {
        width: 200,     // Info window width 200
        height: 100,     // Info window height 100
        title: "", // Info window title
        offset: new BMapGL.Size(30, -50),
    }
    var infoWindow3 = new BMapGL.InfoWindow(sContent, opts);


    // Assume geoGroup.position x/y are Mercator coordinates
    const mercatorX = geoGroup.position.x;
    const mercatorY = geoGroup.position.y;
// const mercatorX = intersectedObject.position.x;
// const mercatorY = intersectedObject.position.y;

// Create a Baidu Map Point object
    const mercatorPoint = new BMapGL.Point(mercatorX, mercatorY);

// Convert Mercator coordinates to lat/lng
    const geoCoord2 = BMapGL.Projection.convertMC2LL(mercatorPoint);

    console.log('Longitude:', geoCoord2.lng); // Output longitude
    console.log('Latitude:', geoCoord2.lat); // Output latitude
    let point = geoCoord2;


    map.openInfoWindow(infoWindow3, point); // Open InfoWindow


    // Get all THREE.Group instances in threeLayer
    const allGroups = getAllGroups(threeLayer.scene);
    console.log(allGroups); // Output all THREE.Group instances

    var retrievedGeoGroup1 = threeLayer.scene.getObjectByName("geoGroup1");
    console.log("retrievedGeoGroup1", retrievedGeoGroup1);

}





//navigate places
var keyFrames = [
    {
        center: new BMapGL.Point(116.307092, 40.054922),
        zoom: 20,
        tilt: 50,
        heading: 0,
        percentage: 0
    },
    {
        center: new BMapGL.Point(116.307631, 40.055391),
        zoom: 21,
        tilt: 70,
        heading: 0,
        percentage: 0.1
    },
    {
        center: new BMapGL.Point(116.306858, 40.057887),
        zoom: 21,
        tilt: 70,
        heading: 0,
        percentage: 0.25
    },
    {
        center: new BMapGL.Point(116.306858, 40.057887),
        zoom: 21,
        tilt: 70,
        heading: -90,
        percentage: 0.35
    },
    {
        center: new BMapGL.Point(116.307904, 40.058118),
        zoom: 21,
        tilt: 70,
        heading: -90,
        percentage: 0.45
    },
    {
        center: new BMapGL.Point(116.307904, 40.058118),
        zoom: 21,
        tilt: 70,
        heading: -180,
        percentage: 0.55
    },
    {
        center: new BMapGL.Point(116.308902, 40.055954),
        zoom: 21,
        tilt: 70,
        heading: -180,
        percentage: 0.75
    },
    {
        center: new BMapGL.Point(116.308902, 40.055954),
        zoom: 21,
        tilt: 70,
        heading: -270,
        percentage: 0.85
    },
    {
        center: new BMapGL.Point(116.307779, 40.055754),
        zoom: 21,
        tilt: 70,
        heading: -360,
        percentage: 0.95
    },
    {
        center: new BMapGL.Point(116.307092, 40.054922),
        zoom: 20,
        tilt: 50,
        heading: -360,
        percentage: 1
    },
];

var view_opts = {
    duration: 50000,
    delay: 1500,
    interation: '2'
};

var view_animation = new BMapGL.ViewAnimation(keyFrames, view_opts);

var auto_navigate_flag=false;

function toggleNavigate(){
    if(auto_navigate_flag){
        cancelNavigate();
        auto_navigate_flag=false;
    }else{
        autoNavigate();
        auto_navigate_flag = true;
    }
}

function autoNavigate() {
    map.centerAndZoom(new BMapGL.Point(116.307092, 40.054922), 20);  // Initialize map: center + zoom level
    map.enableScrollWheelZoom(true);     // Enable mouse wheel zoom
    map.setTilt(50);      // Set initial tilt
    // Define keyframes

    displayOptions={
            indoor: false,
            poiText: true,
            poiIcon: false,
            building: true,
        }
        map.setDisplayOptions(displayOptions);


    // Bind events
    view_animation.addEventListener('animationstart', function (e) {
        console.log('start')
    });
    view_animation.addEventListener('animationiterations', function (e) {
        console.log('onanimationiterations')
    });
    view_animation.addEventListener('animationend', function (e) {
        console.log('end');
        cancelNavigate();

    });
    // Start animation
    setTimeout('map.startViewAnimation(view_animation)', 1);

}

function cancelNavigate(){
    auto_navigate_flag=false;
        displayOptions={
            indoor: false,
            poiText: false,
            poiIcon: false,
            building: false,
        }
        map.setDisplayOptions(displayOptions);
    map.cancelViewAnimation(view_animation);
    refresh();
}
