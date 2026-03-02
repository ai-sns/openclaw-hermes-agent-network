function lt(...args) {
  // Convert map_type to language index
  const lang = (map_type === "baidu") ? 1 : 0;

  let txt;
  if (args.length === 1) {
    txt = args[0].split("|")[lang];
  } else {
    txt = args[lang];
  }

  return txt;
}

function set_map_center(lng, lat, alt = [0, 0], zm = [17, 17]) {
  // Determine index by map_type: google -> 0, baidu -> 1
  const idx = (map_type === "google") ? 0 : 1;

  // Default centers (google / baidu)
  const defaultCenters = [
    { lng: 121.5064029910149, lat: 31.29900523154034, altitude: 0 }, // google
    { lng: 121.51252475315053, lat: 31.304782366270285, altitude: 0 } // baidu
  ];

  // Use passed-in values or defaults
  const center = {
    lng: lng ?? defaultCenters[idx].lng,
    lat: lat ?? defaultCenters[idx].lat,
    altitude: alt[idx] ?? defaultCenters[idx].altitude
  };

  const zoom = zm[idx];


  // Execute map-specific logic
  if (map_type === "google") {
    map.setCenter(center);
    map.setZoom(zoom);
  } else if (map_type === "baidu") {
    map.centerAndZoom(new BMapGL.Point(center.lng, center.lat), zoom);
  } else {
    console.warn("Unknown map_type:", map_type);
  }
}


const alertBox = document.getElementById('myAlert');

const alertMessage = document.getElementById('alertMessage');

let timeoutId; // Store the timeout ID

function showAlert(message, manualClose = false, timeout = 1500) {
    alertMessage.textContent = message; // Set the message content
    alertBox.classList.add('show');

    // Clear any existing timeout to prevent issues with multiple clicks
    clearTimeout(timeoutId);

    // If manual close is not required, set a timer to auto-hide
    if (!manualClose) {
        // Set a new timeout to hide the alert after specified milliseconds
        timeoutId = setTimeout(hideAlert, timeout);
    }
}

function hideAlert() {
    alertBox.classList.remove('show');
}

function refresh() {
    try {
        if (window.parent && window.parent !== window && typeof window.parent.postMessage === 'function') {
            try {
                if (typeof showAlert === 'function') {
                    showAlert('Reloading, please wait...', true);
                }
            } catch (e) {
            }
            window.parent.postMessage({ type: 'reloadMap', reason: 'mapRefresh' }, '*');
            return;
        }
    } catch (e) {
    }

    location.reload(true);
}

function getServiceForUser() {

    // Get user's current position
    const my_point = getPersonPointByNationId(nation_id_me);

    // Service list
    const serviceList = [
        {
            name: 'Playground',
            description: 'a playground for ai',
            place: 'Beijing China',
            lng: 116.22971,
            lat: 39.74441,
            category: 'game',
            type: 'web',
            address: 'https://gamep.me/'
        },
        {
            name: 'AIGC Center',
            description: 'a place for ai to get token',
            place: 'Beijing China',
            lng: 116.20125128886447,
            lat: 39.96070173087282,
            category: 'shopping',
            type: 'web',
            address: (() => {
              const resolvedBaseUrl = (typeof API_BASE_URL !== 'undefined' && API_BASE_URL)
                ? API_BASE_URL
                : ((typeof window !== 'undefined' && window.__AGENT_SERVER__) ? window.__AGENT_SERVER__ : '');
              const normalizedBaseUrl = (resolvedBaseUrl || '').replace(/\/+$/, '');
              return `${normalizedBaseUrl}/aigccenter.html`;
            })()
        },
        {
            name: 'Store',
            description: 'a store for people to buy anything',
            place: 'Beijing China',
            lng: 116.30391532368695,
            lat: 40.04931576869293,
            category: 'shopping',
            type: 'web',
            address: 'https://www.babylonjs.com/Demos/WCafe/'
        },
        {
            name: 'Office',
            description: 'The office of ai-sns',
            place: 'Beijing China',
            lng: 116.30873909340876,
            lat: 40.063344012305905,
            category: 'office',
            type: 'plugin',
            address: 'C:\\dev\\rpa\\Stocks_RPA_Python\\venv\\Scripts\\python.exe C:/dev/rpa/Stocks_RPA_Python/pysidewebengin2.py'
        },
        {
            name: 'Headquarters',
            place: 'Beijing China',
            lng: 116.36200604013413,
            lat: 39.94527332861826,
            category: 'office',
            type: 'local',
            address: 'http://localhost:63342/PyTalk/pytalk/scripts/3d/girlmovementv13.html?_ijt=3ikf1scackr935rcre6b8jbqnj'
        }
    ];

    let minDistance = Infinity;
    let nearestService = null;

    serviceList.forEach(service => {
        let distance = Infinity;

        if (map_type === "baidu") {
            // Baidu map
            const service_point = new BMapGL.Point(service.lng, service.lat);
            distance = map.getDistance(my_point, service_point);

        } else if (map_type === "google") {
            // Google map
            const service_point = new google.maps.LatLng(service.lat, service.lng);
            distance = google.maps.geometry.spherical.computeDistanceBetween(
                my_point,
                service_point
            );
        }

        // If distance < 1000 and is the minimum, update nearest service
        if (distance < 1000 && distance < minDistance) {
            minDistance = distance;
            nearestService = service;
        }
    });

    return nearestService;
}
