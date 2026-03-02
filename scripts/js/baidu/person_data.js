function getPersonDataByNationId(nation_id) {
    if (nation_id == nation_id_me) {
        return person_data_me;
    } else {
        return personsdata.find(person => {
            const pid = (person && (person.nation_id || person.nationid)) ? String(person.nation_id || person.nationid).trim() : '';
            return pid === String(nation_id || '').trim();
        }) || null;
    }
}

function getPersonModelByNationId(nation_id) {
    // alert("getPersonModelByNationId");
    // alert(nation_id);
    groupLayer = threeLayer.scene.getObjectByName(nation_id);
    // alert(groupLayer);
    return groupLayer;
}

function getPersonPointByNationId(nation_id) {
    let persondata = getPersonDataByNationId(nation_id);
    if (!persondata || !persondata["location"]) {
        console.error("Unable to get user data or location info, nation_id:", nation_id);
        // Return a default position, e.g. the map center
        return new BMapGL.Point(116.397428, 39.90923);
    }
    let location = persondata["location"];

    const point = new BMapGL.Point(location[0], location[1]);
    return point;
}

function setPersonPointByNationId(nation_id, lng, lat) {
    let persondata = getPersonDataByNationId(nation_id);
    if (!persondata) {
        console.error("Unable to get user data, nation_id:", nation_id);
        return;
    }
    let location = persondata["location"];
    if (!location) {
        location = [];
        persondata["location"] = location;
    }
    location[0] = lng;
    location[1] = lat;
}

function getPersonModelPointByNationId(nation_id) {
    if (is_3d_flag) {
        user_geogroup_layer = getPersonModelByNationId(nation_id);
        // Assume geoGroup2.position x/y are Mercator coordinates
        const mercatorX = user_geogroup_layer.position.x;
        const mercatorY = user_geogroup_layer.position.y;

        const mercatorPoint = new BMapGL.Point(mercatorX, mercatorY);

        const point = BMapGL.Projection.convertMC2LL(mercatorPoint);

        return point;

    }


    var person_user_layer = getPersonModelByNationId(nation_id);

    if (person_user_layer === null) {
        return null;
    } else {
        return person_user_layer.getPoint();
    }
}

function setPersonModelPointByNationId(nation_id, point) {
    person_model = getPersonModelByNationId(nation_id);
    llPoint = new BMapGL.Point(point.lng, point.lat);
    const mercatorPoint = BMapGL.Projection.convertLL2MC(llPoint);
    console.log("mercatorPoint", mercatorPoint);
    person_model.position.set(mercatorPoint.lng, mercatorPoint.lat, 0);
}

function getNationIdByAccount(account) {
    if (account == person_data_me.account) {
        return person_data_me.nation_id;
    } else {
        let persondata = personsdata.find(person => person.account === account) || null;
        return persondata["nation_id"];
    }
}

function getPersonDataByAccount(account) {
    if (account == person_data_me.account) {
        return person_data_me;
    } else {
        return persondata = personsdata.find(person => person.account === account) || null;
    }
}

function getPersonModelByAccount(account) {

    let nation_id = getNationIdByAccount(account);
    let person_model = getPersonModelByNationId(nation_id);
    // If no matching account is found, return null
    return person_model;

}

function getPersonPointByAccount(account) {

    let persondata = getPersonDataByAccount(account);
    let location = persondata["location"];
    const point = new BMapGL.Point(location[0], location[1]);
    return point;

}
