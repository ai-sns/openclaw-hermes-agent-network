//route plan
var directionDisplay;
var stepDisplay;
var markerArray = [];
var position;
var polyline = null;
var poly2 = null;
var speed = 0.000005, wait = 1;

var myPano;
var user_marker;
var route_status = "stopped";
var panoClient;
var nextPanoId;
var timerHandle = null;
var steps = []

var step = 5; // 5; // metres
var tick = 100; // milliseconds
var eol;
var k = 0;
var stepnum = 0;
var speed = "";
var lastVertex = 1;
var currentDistance = 0;
var is_route_move_action = false;
var last_p = null;

// Flag whether route planning is initiated by the user
var isUserInitiatedRoutePlanning = false;

// Coordinate capture related variables
var coordinateCaptureMode = false;
var targetInputField = null;

function initialize_route() {

    // Create a renderer for directions and bind it to the map.

    var rendererOptions = {
        draggable: true,
        map: map
    }
    directionsDisplay = new google.maps.DirectionsRenderer(rendererOptions);

    directionsDisplay.addListener("directions_changed", () => {
        const directions = directionsDisplay.getDirections();

        if (directions) {
            computeTotalDistance(directions);
            console.log(directions);
            handleRoute(directions);
        }
    });


    // Instantiate an info window to hold step text.
    stepDisplay = new google.maps.InfoWindow();

    polyline = new google.maps.Polyline({
        path: [],
        strokeColor: '#FF0000',
        strokeWeight: 3
    });
    poly2 = new google.maps.Polyline({
        path: [],
        strokeColor: '#FF0000',
        strokeWeight: 3
    });

    // Add change listener for position type selection
    const positionTypeSelect = document.getElementById("position_type");
    if (positionTypeSelect) {
        positionTypeSelect.addEventListener("change", function() {
            toggleCoordinateLink();
        });
    }
}

// Toggle coordinate link show/hide
function toggleCoordinateLink() {
    const positionType = document.getElementById("position_type").value;
    const startCoordLink = document.getElementById("start_coord_link");
    const endCoordLink = document.getElementById("end_coord_link");
    const positionTypeSelect = document.getElementById("position_type");

    if (positionType === "coordinates") {

            startCoordLink.style.display = "block";
            endCoordLink.style.display = "block";

    } else {
        startCoordLink.style.display = "none";
        endCoordLink.style.display = "none";

        // Exit coordinate capture mode
        if (coordinateCaptureMode) {
            stopCoordinateCapture();
        }
    }
}

// Start coordinate capture
function startCoordinateCapture(targetField) {
    coordinateCaptureMode = true;
    targetInputField = targetField;

    // Change map cursor style
    map.setOptions({ draggableCursor: 'crosshair' });

    // Update the currently clicked link text
    const linkElement = document.getElementById(targetField + "_coord_link_element");
    if (linkElement) {
        linkElement.textContent = "Stop coordinate capture";
        linkElement.onclick = stopCoordinateCapture;
    }

    // Ensure other links revert to "Click here to get coordinates"
    const otherFields = ['start', 'end', 'home_address'];
    const currentFieldIndex = otherFields.indexOf(targetField);
    if (currentFieldIndex !== -1) {
        // Reset all other coordinate links
        otherFields.forEach(field => {
            if (field !== targetField) {
                const otherLinkElement = document.getElementById(field + "_coord_link_element");
                if (otherLinkElement) {
                    otherLinkElement.textContent = "Click to get coordinates";
                    otherLinkElement.onclick = function() { startCoordinateCapture(field); };
                }
            }
        });
    }

    showAlert("Click on the map to capture coordinates.");
}

// Stop coordinate capture
function stopCoordinateCapture() {
    coordinateCaptureMode = false;
    targetInputField = null;

    // Restore map cursor style
    map.setOptions({ draggableCursor: null });

    // Restore link text and click handlers
    const startLinkElement = document.getElementById("start_coord_link_element");
    if (startLinkElement) {
        startLinkElement.textContent = "Click to get coordinates";
        startLinkElement.onclick = function() { startCoordinateCapture('start'); };
    }

    const endLinkElement = document.getElementById("end_coord_link_element");
    if (endLinkElement) {
        endLinkElement.textContent = "Click to get coordinates";
        endLinkElement.onclick = function() { startCoordinateCapture('end'); };
    }

    // Restore home position link text and click handler
    const homeAddressLinkElement = document.getElementById("home_address_coord_link_element");
    if (homeAddressLinkElement) {
        homeAddressLinkElement.textContent = "Click to get coordinates";
        homeAddressLinkElement.onclick = function() { startCoordinateCapture('home_address'); };
    }
}

// Reset coordinate links to initial state
function resetCoordinateLinks() {
    coordinateCaptureMode = false;
    targetInputField = null;

    // Restore map cursor style
    map.setOptions({ draggableCursor: null });

    // Restore start link text and click handler
    const startLinkElement = document.getElementById("start_coord_link_element");
    if (startLinkElement) {
        startLinkElement.textContent = "Click to get coordinates";
        startLinkElement.onclick = function() { startCoordinateCapture('start'); };
    }

    // Restore end link text and click handler
    const endLinkElement = document.getElementById("end_coord_link_element");
    if (endLinkElement) {
        endLinkElement.textContent = "Click to get coordinates";
        endLinkElement.onclick = function() { startCoordinateCapture('end'); };
    }

    // Restore home position link text and click handler
    const homeAddressLinkElement = document.getElementById("home_address_coord_link_element");
    if (homeAddressLinkElement) {
        homeAddressLinkElement.textContent = "Click to get coordinates";
        homeAddressLinkElement.onclick = function() { startCoordinateCapture('home_address'); };
    }
}

// Map click handler
function handleMapClick(latLng) {
    if (!coordinateCaptureMode || !targetInputField) return;

    // Fill coordinates into the target input
    const inputElement = document.getElementById(targetInputField);
    if (inputElement) {
        inputElement.value = latLng.lng() + "," + latLng.lat();
    }
}

function createMarker(latlng, label, html) {

    var contentString = '<b>' + label + '</b><br>' + html;

    // Convert avatar path to the _map variant
    // Example: images/avatars/NG2025052719071718435.png -> images/avatars/NG2025052719071718435_map.png
    var avatarPath = person_data_me.avatar;
    var lastDotIndex = avatarPath.lastIndexOf('.');
    var mapAvatarPath;
    if (lastDotIndex !== -1) {
        mapAvatarPath = avatarPath.substring(0, lastDotIndex) + '_map' + avatarPath.substring(lastDotIndex);
    } else {
        // If there is no extension, append _map directly
        mapAvatarPath = avatarPath + '_map';
    }

    var user_marker = new google.maps.Marker({
        position: latlng,
        map: map,
        title: label,
        icon: {
            url: '/' + mapAvatarPath, // icon image path
            scaledSize: new google.maps.Size(36, 49), // icon scaled size (px)
            origin: new google.maps.Point(0, 0), // icon origin, usually (0, 0)
            anchor: new google.maps.Point(18, 49) // icon anchor, usually bottom-center
        },
        zIndex: Math.round(latlng.lat() * -100000) << 5
    });
    user_marker.myname = label;


    google.maps.event.addListener(user_marker, 'click', function () {
        infowindow.setContent(contentString);
        infowindow.open(map, user_marker);
    });
    return user_marker;
}


// isUserInitiated: whether initiated by the user, default is true
function planRoute(isUserInitiated = true) {
    // Set flag based on parameter: whether route planning is initiated by the user
    isUserInitiatedRoutePlanning = isUserInitiated;

    stopTrack(); // Clear existing route
    calcRoute();
}

function calcRoute() {

    if (timerHandle) {
        clearTimeout(timerHandle);
    }
    if (user_marker) {
        user_marker.setMap(null);
    }
    polyline.setMap(null);
    poly2.setMap(null);
    directionsDisplay.setMap(null);
    polyline = new google.maps.Polyline({
        path: [],
        strokeColor: '#FF0000',
        strokeWeight: 3
    });
    poly2 = new google.maps.Polyline({
        path: [],
        strokeColor: '#FF0000',
        strokeWeight: 3
    });
    // Create a renderer for directions and bind it to the map.
    rendererOptions = {
        draggable: true,
        map: map
    }
    directionsDisplay = new google.maps.DirectionsRenderer(rendererOptions);

    directionsDisplay.addListener("directions_changed", () => {
        const directions = directionsDisplay.getDirections();

        if (directions) {
            computeTotalDistance(directions);
            console.log(directions);
            handleRoute(directions);
        }
    });

    var start = document.getElementById("start").value;
    var end = document.getElementById("end").value;
    var positionType = document.getElementById("position_type").value;

    // Keep original values for database storage
    var startForStorage = start;
    var endForStorage = end;

    // If end point is coordinates, use the coordinates directly

    // Parse coordinate string "lat,lng"
    var coords = end.split(",");
    if (coords.length === 2) {

        var endLat = parseFloat(coords[1]);
        var endLng = parseFloat(coords[0]);
        // Check for valid numbers
        if (!isNaN(endLat) && !isNaN(endLng)) {
            end = new google.maps.LatLng(endLat, endLng);
        }

    }


    // Check whether start point is coordinates
    var startCoords = start.split(",");
    if (startCoords.length === 2) {
        var startLat = parseFloat(startCoords[1]);
        var startLng = parseFloat(startCoords[0]);
        // Check for valid numbers
        if (!isNaN(startLat) && !isNaN(startLng)) {
            start = new google.maps.LatLng(startLat, startLng);
        }
    }

    var travelMode = google.maps.DirectionsTravelMode.DRIVING

    var request = {
        origin: start,
        destination: end,
        travelMode: travelMode
    };

    // Route the directions and pass the response to a
    // function to create markers for each step.
    directionsService.route(request, function (response, status) {
        if (status == google.maps.DirectionsStatus.OK) {
            let directions = response;
            directionsDisplay.setDirections(directions);

            // Save start/end to backend
            update_map_setting("route_start", startForStorage);
            update_map_setting("route_end", endForStorage);

            // After successful route planning, update status to 'playing'
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

            // Show view/reset buttons and hide confirm button
            if (msgdiv) {
                const buttons = msgdiv.getElementsByTagName('button');
                for (let i = 0; i < buttons.length; i++) {
                    const button = buttons[i];
                    const action = (button && button.dataset) ? String(button.dataset.action || '') : '';
                    if (action === 'route-confirm') {
                        button.style.display = 'none';
                    } else if (action === 'route-view' || action === 'route-reset') {
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
            showAlert("Route planning failed: " + status);
        }
    });
}


function handleRoute(directions) {

    if (timerHandle) {
        clearTimeout(timerHandle);
    }
    if (user_marker) {
        user_marker.setMap(null);
    }
    polyline.setMap(null);
    poly2.setMap(null);
    // directionsDisplay.setMap(null);

    polyline = new google.maps.Polyline({
        path: [],
        strokeColor: '#FF0000',
        strokeWeight: 3
    });
    poly2 = new google.maps.Polyline({
        path: [],
        strokeColor: '#FF0000',
        strokeWeight: 3
    });

    var bounds = new google.maps.LatLngBounds();
    var route = directions.routes[0];
    startLocation = {};
    endLocation = {};

    // For each route, display summary information.
    var path = directions.routes[0].overview_path;
    var legs = directions.routes[0].legs;
    for (i = 0; i < legs.length; i++) {
        if (i == 0) {
            startLocation.latlng = legs[i].start_location;
            startLocation.address = legs[i].start_address;
            // user_marker = google.maps.Marker({map:map,position: startLocation.latlng});
            if (init_route_current_position) {
                // Create lat/lng values
                const latitude = init_route_current_position.lat; // example latitude
                const longitude = init_route_current_position.lng; // example longitude
                // Create google.maps.LatLng to represent a location on the map
                const latlng = new google.maps.LatLng(latitude, longitude);
                user_marker = createMarker(latlng, "start", legs[i].start_address, "green");
            } else {
                user_marker = createMarker(legs[i].start_location, "start", legs[i].start_address, "green");
            }

        }
        endLocation.latlng = legs[i].end_location;
        console.log("endLocation.latlng:", endLocation.latlng);
        endLocation.address = legs[i].end_address;
        var steps = legs[i].steps;
        for (j = 0; j < steps.length; j++) {
            var nextSegment = steps[j].path;
            for (k = 0; k < nextSegment.length; k++) {
                polyline.getPath().push(nextSegment[k]);
                bounds.extend(nextSegment[k]);


            }
        }
    }

    polyline.setMap(map);
    map.fitBounds(bounds);
}


//animation functions
function updatePoly(d) {
    // Spawn a new polyline every 20 vertices, because updating a 100-vertex poly is too slow
    if (poly2.getPath().getLength() > 20) {
        poly2 = new google.maps.Polyline([polyline.getPath().getAt(lastVertex - 1)]);
    }

    if (polyline.GetIndexAtDistance(d) < lastVertex + 2) {
        if (poly2.getPath().getLength() > 1) {
            poly2.getPath().removeAt(poly2.getPath().getLength() - 1)
        }
        poly2.getPath().insertAt(poly2.getPath().getLength(), polyline.GetPointAtDistance(d));
    } else {
        poly2.getPath().insertAt(poly2.getPath().getLength(), endLocation.latlng);
    }
}


function animatePoly(d) {
    if (d > eol) {
        console.log("endLocation.latlng", endLocation.latlng.lat());
        map.panTo(endLocation.latlng);
        user_marker.setPosition(endLocation.latlng);
        return;
    }
    var p = polyline.GetPointAtDistance(d);
    last_p = p;
    // setPersonModelPointByNationId(nation_id_me, p);
    console.log("middle point", p.lat());
    // map.panTo(p);
    user_marker.setPosition(p);
    updatePoly(d);
    timerHandle = setTimeout("animatePoly(" + (d + step) + ")", tick);
    currentDistance = d + step;
    const route_current_position = JSON.stringify(p);
    const current_position = route_current_position;
    update_map_setting("route_current_position", route_current_position);
    update_map_setting("route", currentDistance);
    update_map_setting("current_position", route_current_position);
}


function startAnimation() {

    eol = polyline.Distance();
    if (init_route_current_position) {
        map.setCenter(init_route_current_position);
    } else {
        map.setCenter(polyline.getPath().getAt(0));
    }


    poly2 = new google.maps.Polyline({
        path: [polyline.getPath().getAt(0)],
        strokeColor: "#FF0000",
        strokeWeight: 10
    });


    setTimeout(function () {
        animatePoly(init_route_distance); // pass variable to animatePoly
    }, 2000); // keep delay unchanged
    // display

}


function viewRoute() {
alert("1viewroute");
    eol = polyline.Distance();
    alert(0);
    alert(eol);
    if(polyline){
    if (init_route_current_position && Object.keys(init_route_current_position).length > 0) {
        alert(init_route_current_position);
        const str = JSON.stringify(init_route_current_position);
        alert(str);
        alert(11);
        map.setCenter(init_route_current_position);
    } else {
        alert(22);
        map.setCenter(polyline.getPath().getAt(0));
    }}else{showAlert("Failed to load route. Check your network, refresh the page, or specify the route again.",true)}
}

// Track toggle function
function route_move_action_from_python(){
    // Call startTrack or continueTrack based on currentDistance
    if (currentDistance === 0) {
        startTrack();
    } else {
        continueTrack();
    }

    // Call pauseTrack after 10 seconds
    setTimeout(() => {
        pauseTrack();
    }, 11000);
}

function toggleTrack() {
    const span = document.getElementById('route_opr');
    const icon = document.getElementById('track_icon');

    switch (route_status) {
        case 'stopped':
            startTrack();
            span.textContent = 'Pause roaming'; // update text
            icon.className = 'fas fa-circle-pause'; // update icon to pause
            route_status = 'playing'; // update status
            break;
        case 'playing':
            pauseTrack();
            span.textContent = 'Resume roaming'; // update text
            icon.className = 'fas fa-circle-play'; // update icon to play
            route_status = 'paused'; // update status
            break;
        case 'paused':
            continueTrack();
            span.textContent = 'Pause roaming'; // update text
            icon.className = 'fas fa-circle-pause'; // update icon to pause
            route_status = 'playing'; // update status
            break;
        default:
            console.error('Unknown route status:', route_status);
    }
    update_map_setting("route_status", route_status);
}

// Track simulation
function startTrack() {

    startAnimation();
}

// Pause animation and show current geographic point
function pauseTrack() {

    if (timerHandle) {
        clearTimeout(timerHandle);
    }

    // Compute a new position offset by ~50 meters
    // On Earth, 1 degree of latitude is ~111km, so 50m is ~0.00045 degrees
    const offsetDegrees = 0.00045; // ~50m
    const offsetPoint = new google.maps.LatLng(
        last_p.lat() + offsetDegrees,
        last_p.lng() + offsetDegrees
    );

    setPersonModelPointByNationId(nation_id_me, offsetPoint);

}

// Continue animation
function continueTrack() {
    d = currentDistance;
    timerHandle = setTimeout("animatePoly(" + d + ")", tick);
}

// Clear route
function stopTrack() {
    try {
        if (timerHandle) {
            clearTimeout(timerHandle);
            timerHandle = null;
        }

        if (user_marker) {
            try {
                user_marker.setMap(null);
            } catch (e) {
                console.warn("Failed to remove user_marker:", e);
            }
            user_marker = null;
        }

        if (polyline) {
            try {
                polyline.setMap(null);
            } catch (e) {
                console.warn("Failed to remove polyline:", e);
            }
        }

        if (poly2) {
            try {
                poly2.setMap(null);
            } catch (e) {
                console.warn("Failed to remove poly2:", e);
            }
        }

        if (directionsDisplay) {
            try {
                directionsDisplay.setMap(null);
            } catch (e) {
                console.warn("Failed to remove directionsDisplay:", e);
            }
        }

        console.log("Route has been fully cleared");

        // Note: do not update menu checkmarks here
        // stopTrack() may be called from multiple places (e.g. before planning a new route)
        // Only update checkmarks when switching to random route is confirmed (handled in setRouteRandom callback)
    } catch (error) {
        console.error("stopTrack failed:", error);
        // Ensure references are cleared even on errors
        timerHandle = null;
        user_marker = null;
    }
}

function computeTotalDistance(result) {
    let total = 0;
    const myroute = result.routes[0];

    if (!myroute) {
        return;
    }

    for (let i = 0; i < myroute.legs.length; i++) {
        total += myroute.legs[i].distance.value;
    }

    total = total / 1000;

alert("Total distance");
alert(total);

}


