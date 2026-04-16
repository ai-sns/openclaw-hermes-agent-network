var hiddenPoints = {}; // Store hidden point elements

var hiddenPointNationIds = {};

function setSinglePointHidden(nation_id, hidden) {
    const nid = String(nation_id || '').trim();
    if (!nid) return;
    try {
        if (hidden) {
            hiddenPointNationIds[nid] = true;
        } else {
            delete hiddenPointNationIds[nid];
        }
    } catch (e) {
    }

    try {
        const div = document.getElementById(nid);
        if (div && div.style) {
            div.style.display = hidden ? 'none' : 'block';
            if (hidden) {
                hiddenPoints[nid] = div;
            }
        }
    } catch (e) {
    }
}

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

// Get single-point HTML element
function getSinglePointHTML(context) {
    const div = document.createElement('div');
    div.className = 'single-point';
    div.id = context.nation_id;

    try {
        const nid = String(context.nation_id || '').trim();
        if (nid && hiddenPointNationIds && hiddenPointNationIds[nid]) {
            div.style.display = 'none';
        }
    } catch (e) {
    }

    div.innerHTML = `
                <img src="${_aiSnsUrl('/avatars/' + context.nation_id + '_avatar.png')}" style="width: 36px;height: 49px">
                <span style="display: none">${context.name}</span>
            `;

    // Click: hide single point
    div.addEventListener('click', function (event) {
        event.stopPropagation(); // Stop propagation
        hiddenPoints[context.nation_id] = div; // Store in hidden list
        // div.style.display = 'none'; // Hide point
        showprofile(context.nation_id);


    });

    return div;
}


var cluster = null;

// Add clustered data
function addCluster() {
    if (cluster) {
        return;
    }
    cluster = new Cluster.View(map, {
        clusterMinPoints: 2,
        clusterMaxZoom: 18,
        updateRealTime: true,
        fitViewOnClick: true,
        // Use pixel-distance clustering for all zoom levels (global-compatible)
        clusterType: [
            [3, null, Cluster.ClusterType.DIS_PIXEL, 64]
        ],
        renderClusterStyle: {
            type: Cluster.ClusterRender.DOM,
            inject: (props) => {
                const count = props.pointCount;
                const container = document.createElement('div');

                // Set styles based on cluster size
                const size = count < 10 ? 40 : count < 100 ? 50 : 60;
                const color = count < 10 ? '#1E90FF' : count < 100 ? '#FF7F50' : '#FF4500';

                Object.assign(container.style, {
                    width: `${size}px`,
                    height: `${size}px`,
                    lineHeight: `${size}px`,
                    textAlign: 'center',
                    backgroundColor: color,
                    color: 'white',
                    borderRadius: '50%',
                    fontSize: '14px',
                    boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
                    border: '2px solid white'
                });

                container.innerHTML = count;
                return container;
            }
        },
        renderSingleStyle: {
            type: Cluster.ClusterRender.DOM,
            style: {
                anchors: [0, 1],
                offsetX: -20,
                offsetY: -9.5
            },
            inject: getSinglePointHTML
        }
    });
    cluster.on(Cluster.ClusterEvent.CLICK, (e) => {
        console.log('ClusterEvent.CLICK', e);
    });
    // cluster.on(Cluster.ClusterEvent.MOUSE_OVER, (e) => {
    //     console.log('ClusterEvent.MOUSEOVER', e);
    // });
    // cluster.on(Cluster.ClusterEvent.MOUSE_OUT, (e) => {
    //     console.log('ClusterEvent.MOUSEOUT', e);
    // });
    var points = Cluster.pointTransformer(personsdata, function (data) {
        return {
            point: [data.location[0], data.location[1]],
            properties: {
                name: data.nick_name,
                nation_id: data.nation_id,
            }
        }
    });
    console.log(points);
    cluster.setData(points);
    persons_loaded_flag = true;
}

// Remove clustered data
function removeCluster() {
    cluster && cluster.destroy();
    cluster = null;
}

function showpoints() {
    addCluster();
}

// Show all hidden points
function showHiddenPoints() {
    // Traverse hidden list and show points again
    hiddenPoints.forEach((point) => {
        point.style.display = 'block';
    });

    // Clear hidden record
    hiddenPoints = {};
}

