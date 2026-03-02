
    //handle cluster marker
    var markerCluster;
    var hiddenMarkers = {};
    var markers;

    function _aiSnsUrl(p) {
        try {
            const baseRaw = (typeof window !== 'undefined' && window.__AI_SNS_SERVER__) ? String(window.__AI_SNS_SERVER__) : '';
            const base = baseRaw.endsWith('/') ? baseRaw.slice(0, -1) : baseRaw;
            if (!base) return '';
            const path = String(p || '');
            if (!path) return base;
            if (path.startsWith('/')) return base + path;
            return base + '/' + path;
        } catch (e) {
            return '';
        }
    }

    function showpoints() {
        // 2. Generate coordinate points

        const markersData = personsdata;


        // 3. Create marker objects and add to the map
        const iconSize = new google.maps.Size(36, 49); // Actual icon size
        markers = markersData.map(data => {
            const marker = new google.maps.Marker({
                position: {
                    lng: data.location[0],
                    lat: data.location[1]
                },
                map: map,
                title: data.nick_name, // Marker title
                nation_id: data.nation_id,
                icon: {
                    url: _aiSnsUrl('/avatars/' + data.nation_id + '_avatar.png'), // Custom icon URL
                    scaledSize: iconSize // Scaled icon size
                }
            });

            // Add click handler for each marker
            marker.addListener('click', () => {
                alert(`Coordinates: (${data.location[0]}, ${data.location[1]})\nName: ${data.nick_name}`);
                hiddenMarkers[data.nation_id] = marker;
                showprofile(data.nation_id);
                // hideMarker(marker); // Hide marker and move to hidden list
            });
            console.log("marker:", marker);

            return marker;
        });

        // 4. Marker clustering (optional)
        markerCluster = new MarkerClusterer(map, markers, {
            // imagePath: 'https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m'
            imagePath: './m'
            // Combined m1-m5: actual URL e.g. https://developers.google.com/maps/documentation/javascript/examples/markerclusterer/m1.png
        });
        console.log("markers", markers);
        persons_loaded_flag = true;
    }

    function getMarkerByNationId(nationId) {
        return markers.find(marker => marker.nation_id === nationId) || null;
    }

    function hideMarker(marker) {
        marker.setVisible(false); // Hide marker

    }
