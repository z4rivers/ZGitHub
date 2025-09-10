// Global variables
let climateData = null;
let maxCost = 0;
let houseLoads = { heating: 0, cooling: 0 };
let runYears = 15; // years for summary calculations

// County-level ASHRAE design temperatures (authoritative)
// Loaded from ashrae_county_data.js; supports datasets keyed by FIPS or any key with a 'fips' field
const rawCountyDataset = (typeof ASHRAE_COUNTY_DATA !== 'undefined') ? ASHRAE_COUNTY_DATA : {};
const countyAshraeData = buildCountyFipsIndex(rawCountyDataset);
console.log('County ASHRAE data loaded:', Object.keys(countyAshraeData).length, 'counties');

// NOAA station HDD/CDD database (built locally from 13,472 CSVs → 5,826 usable stations)
// Loaded on demand and cached in-memory
let NOAA_STATIONS_DB = null;
async function loadNoaaStationsDb() {
    if (NOAA_STATIONS_DB !== null) return NOAA_STATIONS_DB;
    try {
        const res = await fetch('noaa_climate_database.json', { cache: 'no-store' });
        if (!res.ok) {
            console.warn('NOAA station DB not found (noaa_climate_database.json)');
            NOAA_STATIONS_DB = [];
            return NOAA_STATIONS_DB;
        }
        const json = await res.json();
        NOAA_STATIONS_DB = Array.isArray(json) ? json : [];
        console.log('NOAA stations loaded:', NOAA_STATIONS_DB.length);
        return NOAA_STATIONS_DB;
    } catch (e) {
        console.warn('Failed to load NOAA station DB:', e);
        NOAA_STATIONS_DB = [];
        return NOAA_STATIONS_DB;
    }
}

function findNearestNoaaStation(lat, lon, stations) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || !stations || !stations.length) return null;
    let best = null;
    let bestD = Infinity;
    for (const s of stations) {
        if (!Number.isFinite(s.latitude) || !Number.isFinite(s.longitude)) continue;
        const d = calculateDistance(lat, lon, s.latitude, s.longitude); // miles
        if (d < bestD) { bestD = d; best = s; }
    }
    if (!best) return null;
    return { station: best, distance_mi: Math.round(bestD * 10) / 10 };
}

// ZIP → FIPS override for known ambiguous ZIPs
const ZIP_TO_FIPS_OVERRIDE = {
    '97201': '41051', // Portland, OR - Multnomah County
    '97219': '41051', // Portland, OR - Multnomah County  
    '97501': '41029', // Medford, OR - Jackson County
    '97015': '41005', // Clackamas, OR - Clackamas County
    '96001': '06089'  // Redding, CA - Shasta County
};

function buildCountyFipsIndex(dataset) {
    try {
        const index = {};
        const addEntry = (val) => {
            if (!val || typeof val !== 'object') return;
            const fipsRaw = val.fips || val.FIPS || val.countyFIPS || val.county_fips;
            if (fipsRaw != null) {
                const fips = String(fipsRaw).padStart(5, '0');
                index[fips] = val;
            }
        };
        const walk = (node, depth = 0) => {
            if (!node || depth > 3) return;
            if (Array.isArray(node)) {
                for (const item of node) {
                    addEntry(item);
                    if (item && typeof item === 'object') walk(item, depth + 1);
                }
                return;
            }
            if (typeof node === 'object') {
                // Add if object itself looks like an entry
                addEntry(node);
                for (const v of Object.values(node)) {
                    if (v && typeof v === 'object') walk(v, depth + 1);
                }
                return;
            }
        };
        walk(dataset, 0);
        if (Object.keys(index).length) return index;
        // Fallback to shallow key scan (covers already-keyed-by-FIPS objects)
        const shallow = {};
        for (const [key, value] of Object.entries(dataset || {})) {
            if (!value || typeof value !== 'object') continue;
            const fipsRaw = value.fips || value.FIPS || value.countyFIPS || value.county_fips || key;
            const fips = (fipsRaw != null) ? String(fipsRaw).padStart(5, '0') : null;
            if (fips) shallow[fips] = value;
        }
        return Object.keys(shallow).length ? shallow : (dataset || {});
    } catch (e) {
        console.warn('Failed to build county FIPS index:', e);
        return dataset || {};
    }
}

async function tryLoadExternalCountyJson() {
    // Optional: load a large county dataset without changing code
    // Try preferred filename first, then legacy
    const candidateUrls = ['HVAC_Design_Temps_FULL.json', 'ashrae_county_data.json'];
    try {
        let json = null;
        for (const url of candidateUrls) {
            try {
                const res = await fetch(url, { cache: 'no-store' });
                if (!res.ok) continue;
                json = await res.json();
                console.log(`Loaded external county JSON: ${url}`);
                break;
            } catch (_) { /* try next */ }
        }
        if (!json) return; // No JSON available
        const idx = buildCountyFipsIndex(json);
        let merged = 0;
        for (const [k, v] of Object.entries(idx)) {
            if (!countyAshraeData[k]) {
                countyAshraeData[k] = v; // mutate const object (allowed)
                merged++;
            }
        }
        if (merged > 0) console.log(`Merged ${merged} counties from external JSON dataset`);
    } catch (e) {
        console.warn('External county JSON load skipped:', e);
    }
}

async function tryLoadExternalCountyCsv() {
    // Optional: CSV fallback (requires a FIPS column)
    const url = 'ashrae_county_data.csv';
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) return; // CSV file not present
        const text = await res.text();
        const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
        if (lines.length < 2) return;
        const header = lines[0].split(',').map(h => h.trim().toLowerCase());
        const idx = (name) => header.indexOf(name);
        const fipsIdx = [idx('fips'), idx('county_fips')].find(i => i >= 0);
        if (fipsIdx == null || fipsIdx < 0) {
            console.warn('CSV missing FIPS column; skipping import');
            return;
        }
        const nameIdx = [idx('name'), idx('county'), idx('county_name')].find(i => i >= 0);
        const stateIdx = [idx('state'), idx('state_abbr'), idx('state_code')].find(i => i >= 0);
        const heatingIdx = [idx('heating'), idx('heating_99'), idx('heatingdesign'), idx('heating_design')].find(i => i >= 0);
        const coolingIdx = [idx('cooling'), idx('cooling_01'), idx('coolingdesign'), idx('cooling_design')].find(i => i >= 0);
        const hddIdx = [idx('hdd'), idx('hdd65'), idx('heating_degree_days')].find(i => i >= 0);
        const cddIdx = [idx('cdd'), idx('cdd65'), idx('cooling_degree_days')].find(i => i >= 0);
        let merged = 0;
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            if (cols.length <= fipsIdx) continue;
            const fips = String(cols[fipsIdx]).trim().padStart(5, '0');
            if (!fips || countyAshraeData[fips]) continue;
            const getNum = (v) => {
                const n = Number(String(v).trim());
                return Number.isFinite(n) ? n : undefined;
            };
            const entry = {
                name: nameIdx != null && nameIdx >= 0 ? String(cols[nameIdx]).trim() : undefined,
                state: stateIdx != null && stateIdx >= 0 ? String(cols[stateIdx]).trim().toUpperCase() : undefined,
                fips: fips,
                heating: heatingIdx != null && heatingIdx >= 0 ? getNum(cols[heatingIdx]) : undefined,
                cooling: coolingIdx != null && coolingIdx >= 0 ? getNum(cols[coolingIdx]) : undefined,
                hdd: hddIdx != null && hddIdx >= 0 ? getNum(cols[hddIdx]) : undefined,
                cdd: cddIdx != null && cddIdx >= 0 ? getNum(cols[cddIdx]) : undefined,
                source: 'External CSV import'
            };
            countyAshraeData[fips] = entry;
            merged++;
        }
        if (merged > 0) console.log(`Merged ${merged} counties from ashrae_county_data.csv`);
    } catch (e) {
        console.warn('External county CSV load skipped:', e);
    }
}

// NOAA Normals (HDD/CDD) merger: enrich missing degree days
async function tryMergeNoaaNormalsHddCdd() {
    const url = 'noaa_normals_hdd_cdd_1991_2020.csv';
    try {
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) return; // CSV not present
        const text = await res.text();
        const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
        if (lines.length < 2) return;
        const header = lines[0].split(',').map(h => h.trim().toLowerCase());
        const idx = (name) => header.indexOf(name);
        const idIdx = [idx('station_id'), idx('id'), idx('station')].find(i => i >= 0);
        const nameIdx = [idx('station_name'), idx('name')].find(i => i >= 0);
        const latIdx = [idx('latitude'), idx('lat')].find(i => i >= 0);
        const lonIdx = [idx('longitude'), idx('lon'), idx('lng')].find(i => i >= 0);
        const hddIdx = [idx('hdd65_ann'), idx('hdd65'), idx('hdd')].find(i => i >= 0);
        const cddIdx = [idx('cdd65_ann'), idx('cdd65'), idx('cdd')].find(i => i >= 0);
        if ([idIdx, latIdx, lonIdx].some(i => i == null || i < 0)) {
            console.warn('NOAA normals CSV missing required columns; skipping merge');
            return;
        }
        const stations = [];
        for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',');
            if (cols.length <= Math.max(idIdx, latIdx, lonIdx)) continue;
            const station = {
                id: String(cols[idIdx]).trim(),
                name: nameIdx >= 0 ? String(cols[nameIdx]).trim() : '',
                lat: parseFloat(cols[latIdx]),
                lon: parseFloat(cols[lonIdx]),
                hdd: hddIdx >= 0 ? parseFloat(cols[hddIdx]) : undefined,
                cdd: cddIdx >= 0 ? parseFloat(cols[cddIdx]) : undefined
            };
            if (Number.isFinite(station.lat) && Number.isFinite(station.lon)) stations.push(station);
        }
        if (!stations.length) return;

        // Build list of counties missing HDD or CDD
        const counties = Object.entries(countyAshraeData).map(([fips, entry]) => ({ fips, entry }));
        let filled = 0;
        for (const { fips, entry } of counties) {
            const needsHdd = !(Number.isFinite(entry.hdd));
            const needsCdd = !(Number.isFinite(entry.cdd));
            if (!needsHdd && !needsCdd) continue;
            // Use nearest station by haversine distance
            const nearest = nearestStation(entry.lat, entry.lon, stations);
            if (!nearest) continue;
            if (needsHdd && Number.isFinite(nearest.hdd)) entry.hdd = nearest.hdd;
            if (needsCdd && Number.isFinite(nearest.cdd)) entry.cdd = nearest.cdd;
            if ((needsHdd && Number.isFinite(entry.hdd)) || (needsCdd && Number.isFinite(entry.cdd))) filled++;
        }
        if (filled > 0) console.log(`NOAA normals merged into ${filled} counties`);
    } catch (e) {
        console.warn('NOAA normals merge skipped:', e);
    }
}

function nearestStation(lat, lon, stations) {
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || !stations || !stations.length) return null;
    let best = null; let bestD = Infinity;
    for (const s of stations) {
        const d = haversine(lat, lon, s.lat, s.lon);
        if (d < bestD) { bestD = d; best = s; }
    }
    return best;
}

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371; // km
    const toRad = (v) => v * Math.PI / 180;
    const dLat = toRad(lat2 - lat1);
    const dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// Simple Heating Load Input
function updateHeatingLoad() {
    // Get the numeric value from the formatted input
    const heatingLoadInput = parseFloat(document.getElementById('heatingLoadInput').value.replace(/[^\d]/g, '')) || 0;
    
    // Estimate cooling load as 80% of heating load (typical ratio)
    const coolingLoad = Math.round(heatingLoadInput * 0.8);
    
    houseLoads = {
        heating: heatingLoadInput,
        cooling: coolingLoad
    };
    
    // Calculate annual energy needs for heating systems
    updateAnnualHeatingDisplay(heatingLoadInput);
    
    console.log('Heating load set to:', heatingLoadInput, 'BTU/hr');
}

function updateAnnualHeatingDisplay(heatingLoad) {
    if (!climateData) return;
    
    const hdd = climateData.hdd || 0;
    const heatingDesign = climateData.heating;
    const indoorTemp = 65;
    const heatingDesignDiff = indoorTemp - heatingDesign;
    if (heatingDesignDiff <= 0) return;
    
    // Use same degree-day method as cost path
    const heatLossRate = heatingLoad / heatingDesignDiff; // BTU/hr/°F
    const annualHeatingLoadBTU = heatLossRate * hdd * 24; // BTU/year
    
    // Inputs
    const afue = (parseFloat(document.getElementById('furnaceEfficiency').value) || 95) / 100;
    const cop = parseFloat(document.getElementById('heatPumpCOP').value) || 3.5;
    const crossoverTemp = parseFloat(document.getElementById('crossoverTemp').value) || 35;
    const hpShare = calculateHeatPumpEfficiency(heatingDesign, crossoverTemp, hdd);
    
    // Gas furnace therms at meter
    const gasTherms = annualHeatingLoadBTU / (100000 * afue);
    
    // Heat pump kWh
    const hpKWh = annualHeatingLoadBTU / (cop * 3412);
    
    // Hybrid split
    const hybridGasTherms = (annualHeatingLoadBTU * (1 - hpShare)) / (100000 * afue);
    const hybridElecKWh = (annualHeatingLoadBTU * hpShare) / (cop * 3412);
    
    // Update UI
    document.getElementById('annualGasHeat').textContent = formatNumberWithCommas(Math.round(gasTherms)) + ' therms';
    document.getElementById('annualHeatPump').textContent = formatNumberWithCommas(Math.round(hpKWh)) + ' kWh';
    document.getElementById('annualHybridGas').textContent = formatNumberWithCommas(Math.round(hybridGasTherms)) + ' therms';
    document.getElementById('annualHybridElec').textContent = formatNumberWithCommas(Math.round(hybridElecKWh)) + ' kWh';
}

// Format number with commas
function formatNumberWithCommas(num) {
    if (isNaN(num) || num === null || num === undefined) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// Format heating input with commas as user types
function formatHeatingInput(input) {
    // Remove all non-numeric characters
    let value = input.value.replace(/[^\d]/g, '');
    
    // Add commas for thousands
    if (value.length > 0) {
        value = parseInt(value).toLocaleString();
    }
    
    // Update the input value
    input.value = value;
    
    // Trigger the update function
    updateHeatingLoad();
}

// Add event listener for heating load input
document.addEventListener('DOMContentLoaded', async function() {
    const hlInput = document.getElementById('heatingLoadInput');
    hlInput.addEventListener('input', updateHeatingLoad);
    // Format initial value with commas and initialize derived values
    formatHeatingInput(hlInput);

    // Initialize hybrid split bar (default state)
    updateHybridSplitBar(null, null, null);

    // Preload comprehensive county datasets if present (only works on a server)
    if (location.protocol !== 'file:') {
        try {
            await tryLoadExternalCountyJson();
            await tryLoadExternalCountyCsv();
            await tryMergeNoaaNormalsHddCdd();
            console.log('County datasets preloaded. Counties available:', Object.keys(countyAshraeData).length);
        } catch (e) {
            console.warn('County dataset preload skipped:', e);
        }
    } else {
        console.warn('[Preload] Skipping external data fetch on file:// protocol.');
    }

    // --- Interactive Equipment Selectors ---
    // Furnace Efficiency Selector (Refactored for button-based segmented control)
    const furnaceSlider = document.getElementById('furnaceEfficiencySlider');
    const furnaceValue = document.getElementById('furnaceEfficiencyValue');
    const furnaceHidden = document.getElementById('furnaceEfficiency');
    const furnaceBtns = document.querySelectorAll('.furnace-btn');

    function updateFurnaceDisplay() {
        const activeFlue = document.querySelector('.furnace-btn.active').dataset.flueType;
        let value = parseInt(furnaceSlider.value, 10);

        // Enforce floor for plastic flue
        if (activeFlue === 'plastic' && value < 90) {
            value = 90;
            furnaceSlider.value = 90;
        }

        furnaceHidden.value = value;
        furnaceValue.textContent = `${value}%`;

        const min = parseInt(furnaceSlider.min, 10);
        const max = parseInt(furnaceSlider.max, 10);
        const percent = (max - min) > 0 ? ((value - min) / (max - min)) * 100 : 0;
        furnaceSlider.style.setProperty('--fill-percent', `${percent}%`);
        
        recalculateIfDataAvailable();
    }

    function handleFurnaceButtonClick(e) {
        const clickedButton = e.target;
        const flueType = clickedButton.dataset.flueType;

        furnaceBtns.forEach(btn => btn.classList.remove('active'));
        clickedButton.classList.add('active');

        if (flueType === 'metal') {
            furnaceSlider.disabled = true;
            furnaceSlider.value = 80;
        } else if (flueType === 'plastic') {
            furnaceSlider.disabled = false;
            // If current value is below 90, snap to 90
            if (parseInt(furnaceSlider.value, 10) < 90) {
                furnaceSlider.value = 90;
            }
        }
        
        updateFurnaceDisplay();
    }

    furnaceSlider.addEventListener('input', updateFurnaceDisplay);
    furnaceBtns.forEach(btn => {
        btn.addEventListener('click', handleFurnaceButtonClick);
    });

    // Heat Pump Performance Selector
    const hpSlider = document.getElementById('hpPerformanceSlider');
    const hpValue = document.getElementById('hpPerformanceValue');
    const hpHidden = document.getElementById('heatPumpCOP');
    const hpBtns = document.querySelectorAll('.hp-btn');

    function syncHPControls(source) {
        let value;
        if (source === 'slider') {
            value = hpSlider.value;
        } else {
            value = hpHidden.value;
        }
        
        hpHidden.value = value;
        hpSlider.value = value;
        hpValue.textContent = parseFloat(value).toFixed(1);

        hpBtns.forEach(btn => {
            if (btn.dataset.value === value) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
        
        const min = parseFloat(hpSlider.min);
        const max = parseFloat(hpSlider.max);
        const percent = (max - min) > 0 ? ((parseFloat(value) - min) / (max - min)) * 100 : 0;
        hpSlider.style.setProperty('--fill-percent', `${percent}%`);

        recalculateIfDataAvailable();
    }

    hpSlider.addEventListener('input', () => syncHPControls('slider'));
    hpBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            hpHidden.value = btn.dataset.value;
            syncHPControls('btn');
        });
    });

    // Initial setup on load
    updateFurnaceDisplay(); // Use a single function to init and update
    syncHPControls('btn');
});

// Regional estimates removed to enforce ASHRAE-only mandate

const LOCAL_RESNET_FALLBACK = {
    "01001": { name: "AGAWAM/WESTFIELD, MA", heating: 5, cooling: 87, hdd: 6479, cdd: 764, lat: 42.1, lon: -72.6, source: "Hardcoded Fallback" },
    "97201": { name: "PORTLAND, OR", heating: 25, cooling: 85, hdd: 4635, cdd: 341, lat: 45.5, lon: -122.7, source: "Hardcoded Fallback" }
};

function getResnetStations() {
    if (typeof RESNET_ASHRAE_DATA === 'undefined') return [];
    return Object.values(RESNET_ASHRAE_DATA).filter(s => s && Number.isFinite(s.lat) && Number.isFinite(s.lon));
}

function findNearestResnetStation(lat, lon) {
    const stations = getResnetStations();
    if (!stations.length || !Number.isFinite(lat) || !Number.isFinite(lon)) {
        return null;
    }

    let closestStation = null;
    let minDistance = Infinity;

    for (const station of stations) {
        const distance = calculateDistance(lat, lon, station.lat, station.lon);
        if (distance < minDistance) {
            minDistance = distance;
            closestStation = station;
        }
    }
    return closestStation;
}

async function lookupClimateData() {
    const zipCode = document.getElementById('zipCode').value.trim();
    
    if (!zipCode || zipCode.length !== 5) {
        showError('Please enter a valid 5-digit zip code');
        return;
    }

    showLoading();
    hideError();
    hideResults();

    // STEP 1: Check for in-memory data (from resnet_ashrae_data.js or local fallback)
    try {
        const resnetData = (typeof RESNET_ASHRAE_DATA !== 'undefined') ? RESNET_ASHRAE_DATA[zipCode] : null;
        const fallbackData = LOCAL_RESNET_FALLBACK[zipCode] || null;
        const zr = resnetData || fallbackData;
        
        if (zr) {
            if (['heating','cooling','hdd','cdd'].every(k => Number.isFinite(Number(zr[k])))) {
                climateData = {
                    name: zr.name || `ZIP ${zipCode}`,
                    heating: Number(zr.heating), cooling: Number(zr.cooling), hdd: Number(zr.hdd), cdd: Number(zr.cdd),
                    source: (zr.source ? `RESNET/ASHRAE ZIP ${zipCode} – ${zr.source}` : `RESNET/ASHRAE ZIP ${zipCode}`),
                    lat: Number(zr.lat), lon: Number(zr.lon)
                };
                displayClimateData();
                calculateHVACCosts();
                hideLoading();
                return; // <-- CRITICAL FIX: Stop execution after success.
            }
        }
    } catch (e) {
        console.error('Error during in-memory check:', e);
    }

    // If running from file://, stop here to prevent network errors.
    if (location.protocol === 'file:') {
        showError('This ZIP requires a network lookup. Please use "Go Live" to run on a local server.');
        hideLoading();
        return;
    }

    // STEP 2: Full network lookup
    let locationData, fipsInfo, countyEntry;
    try {
        locationData = await getLocationFromZip(zipCode);
        fipsInfo = await getCountyFIPS(locationData.latitude, locationData.longitude);
        countyEntry = countyAshraeData[fipsInfo.countyFIPS];

        if (!countyEntry) {
            countyEntry = findNearestResnetStation(locationData.latitude, locationData.longitude);
            if (countyEntry) {
                 countyEntry.source = `Nearest RESNET Station: ${countyEntry.name}`;
            } else {
                throw new Error("All lookups and fallbacks failed.");
            }
        }

        const normalized = normalizeCountyEntry(countyEntry, fipsInfo);
        if (!Number.isFinite(normalized.heating)) {
            throw new Error('Final data is incomplete (missing heating design temperature).');
        }

        // STEP 2b: Merge HDD/CDD from local NOAA station DB (nearest station by lat/lon)
        try {
            const stations = await loadNoaaStationsDb();
            if (stations && stations.length) {
                const nearest = findNearestNoaaStation(locationData.latitude, locationData.longitude, stations);
                if (nearest && nearest.station) {
                    const hdd = Number(nearest.station.hdd);
                    const cdd = Number(nearest.station.cdd);
                    if (Number.isFinite(hdd)) normalized.hdd = hdd;
                    if (Number.isFinite(cdd)) normalized.cdd = cdd;
                    const src = normalized.source || '';
                    const nearestName = nearest.station.name || nearest.station.station_id || 'NOAA Station';
                    normalized.source = src ? (src + ' + NOAA Normals 2006–2020 (nearest: ' + nearestName + ')')
                                            : ('NOAA Normals 2006–2020 (nearest: ' + nearestName + ')');
                }
            }
        } catch (e) {
            console.warn('NOAA merge skipped:', e);
        }

        if (!Number.isFinite(normalized.hdd)) {
            throw new Error('Final data is incomplete (missing HDD after NOAA merge).');
        }

        climateData = normalized;
        displayClimateData();
        calculateHVACCosts();
        hideError();

    } catch (error) {
        console.error('The lookup process failed. Final error:', error);
        showError('No valid county-level ASHRAE data available for this ZIP.');
    } finally {
        hideLoading();
    }
}

async function tryMergeNceiHddCdd(fips) {
    try {
        const url = 'ashrae_county_hdd_cdd.json';
        const res = await fetch(url, { cache: 'no-store' });
        if (!res.ok) return null;
        const ncei = await res.json();
        const entry = ncei[fips];
        if (!entry) return null;
        // Merge HDD/CDD into existing county entry if present
        if (countyAshraeData[fips]) {
            countyAshraeData[fips].hdd = entry.hdd;
            countyAshraeData[fips].cdd = entry.cdd;
            countyAshraeData[fips].source = (countyAshraeData[fips].source || '') + ' + ' + entry.source;
            return countyAshraeData[fips];
        }
        return entry;
    } catch (e) {
        return null;
    }
}
function normalizeCountyEntry(entry, fipsInfo) {
    const getNum = (v) => {
        const n = Number(v);
        return Number.isFinite(n) ? n : undefined;
    };
    const heating = getNum(entry.heating) ?? getNum(entry.heating_99) ?? getNum(entry.heatingDesign) ?? getNum(entry.heating_design);
    const cooling = getNum(entry.cooling) ?? getNum(entry.cooling_01) ?? getNum(entry.coolingDesign) ?? getNum(entry.cooling_design);
    const hdd = getNum(entry.hdd) ?? getNum(entry.HDD) ?? getNum(entry.heating_degree_days) ?? getNum(entry.HDD65);
    const cdd = getNum(entry.cdd) ?? getNum(entry.CDD) ?? getNum(entry.cooling_degree_days) ?? getNum(entry.CDD65);
    const name = entry.name || `${fipsInfo.countyName}, ${fipsInfo.stateAbbr}`;
    const source = entry.source || 'Appendix A (Normative) + RESNET HDD/CDD';
    const lat = getNum(entry.lat);
    const lon = getNum(entry.lon);
    return { name, heating, cooling, hdd, cdd, source, lat, lon };
}

async function getLocationFromZip(zipCode) {
    try {
        console.log('Looking up zip code:', zipCode);
        const response = await fetch(`https://api.zippopotam.us/us/${zipCode}`);
        console.log('Zippopotam response status:', response.status);
        
        if (!response.ok) {
            console.error('Zippopotam API error:', response.status, response.statusText);
            throw new Error('Location lookup failed');
        }
        
        const data = await response.json();
        console.log('Zippopotam data:', data);
        
        if (!data.places || data.places.length === 0) {
            throw new Error('No location data found for zip code');
        }
        
        return {
            latitude: parseFloat(data.places[0].latitude),
            longitude: parseFloat(data.places[0].longitude),
            city: data.places[0]['place name'],
            state: data.places[0]['state abbreviation']
        };
    } catch (error) {
        console.error('Zip code lookup error:', error);
        throw error;
    }
}

async function getCountyFIPS(lat, lon) {
    // FCC Census API - returns county FIPS and names
    const url = `https://geo.fcc.gov/api/census/area?lat=${lat}&lon=${lon}&format=json`;
    const res = await fetch(url);
    if (!res.ok) {
        console.error('FCC FIPS API error:', res.status, res.statusText);
        throw new Error('FIPS lookup failed');
    }
    const data = await res.json();
    if (!data || !data.results || data.results.length === 0) {
        throw new Error('No FIPS result for coordinates');
    }
    const county = data.results[0];
    return {
        countyFIPS: county['county_fips'] || county['FIPS'] || county['county_fips_code'] || null,
        countyName: county['county_name'] || county['name'] || 'Unknown County',
        stateAbbr: county['state_code'] || county['state_abbr'] || county['state'] || ''
    };
}

function reportMissingCounty(fipsInfo) {
    try {
        if (!window.MISSING_COUNTIES) window.MISSING_COUNTIES = {};
        const key = fipsInfo.countyFIPS || `${fipsInfo.countyName}-${fipsInfo.stateAbbr}`;
        window.MISSING_COUNTIES[key] = {
            countyFIPS: fipsInfo.countyFIPS,
            countyName: fipsInfo.countyName,
            stateAbbr: fipsInfo.stateAbbr,
            timestamp: new Date().toISOString()
        };
        console.log('Recorded missing county for population:', window.MISSING_COUNTIES[key]);
    } catch (e) {
        console.warn('Could not record missing county:', e);
    }
}


// getWeatherStationData removed to enforce ASHRAE-only mandate

// getHistoricalWeatherData removed to enforce ASHRAE-only mandate

function calculatePercentile(sortedArray, percentile) {
    const index = (percentile * (sortedArray.length - 1));
    const lower = Math.floor(index);
    const upper = Math.ceil(index);
    const weight = index % 1;
    
    if (upper >= sortedArray.length) return sortedArray[sortedArray.length - 1];
    return sortedArray[lower] * (1 - weight) + sortedArray[upper] * weight;
}

function findNearestASHRAEData(city, state, lat, lon) {
    console.log('Finding nearest ASHRAE data for:', city, state, lat, lon);
    console.log('Available ASHRAE data entries:', Object.keys(ashraeData).length);
    
    // First try exact city/state match
    for (const [zip, data] of Object.entries(ashraeData)) {
        if (data.name.includes(city) && data.name.includes(state)) {
            console.log('Found exact match:', data);
            return data;
        }
    }
    
    // Find the closest by distance using coordinates
    let closestData = null;
    let minDistance = Infinity;
    
    for (const [zip, data] of Object.entries(ashraeData)) {
        // Only consider entries with coordinates
        if (data.lat && data.lon) {
            const distance = calculateDistance(lat, lon, data.lat, data.lon);
            if (distance < minDistance) {
                minDistance = distance;
                closestData = data;
            }
        }
    }
    
    console.log('Closest ASHRAE data:', closestData, 'Distance:', minDistance);
    // Integrity check: require heating, cooling, hdd, cdd to be finite numbers
    if (closestData) {
        const valid = ['heating','cooling','hdd','cdd'].every(k => Number.isFinite(closestData[k]));
        if (!valid) {
            console.error('ASHRAE entry missing required fields:', closestData);
            return null;
        }
    }
    return closestData;
}

// Minimal self-test to verify a few spot zips resolve to ASHRAE entries
function runAshraeSelfTest() {
    const tests = ['97201','98101','10001'];
    const results = tests.map(z => ({ zip: z, ok: !!RESNET_ASHRAE_DATA[z] }));
    console.log('ASHRAE self-test:', results);
    return results;
}

// findRegionalMatch removed to enforce ASHRAE-only mandate

function getGeographicRegion(lat, lon) {
    if (lat >= 45) return 'north';
    if (lat >= 35) return 'central';
    if (lat >= 25) return 'south';
    return 'tropical';
}

function getStateRegion(state) {
    const stateRegions = {
        'AK': 'north', 'WA': 'north', 'OR': 'north', 'ID': 'north', 'MT': 'north', 'ND': 'north', 'MN': 'north', 'WI': 'north', 'MI': 'north', 'ME': 'north', 'VT': 'north', 'NH': 'north',
        'CA': 'west', 'NV': 'west', 'UT': 'west', 'CO': 'west', 'WY': 'west', 'NM': 'west', 'AZ': 'west',
        'TX': 'south', 'OK': 'south', 'AR': 'south', 'LA': 'south', 'MS': 'south', 'AL': 'south', 'GA': 'south', 'FL': 'south', 'SC': 'south', 'NC': 'south', 'TN': 'south', 'KY': 'south',
        'IL': 'central', 'IN': 'central', 'OH': 'central', 'PA': 'central', 'NY': 'central', 'NJ': 'central', 'CT': 'central', 'RI': 'central', 'MA': 'central', 'VT': 'central', 'NH': 'central', 'ME': 'central',
        'IA': 'central', 'MO': 'central', 'KS': 'central', 'NE': 'central', 'SD': 'central', 'ND': 'central'
    };
    return stateRegions[state] || 'central';
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    // Haversine formula for calculating distance between two points
    const R = 3959; // Earth's radius in miles
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
             Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
             Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// getRegionalEstimate removed to enforce ASHRAE-only mandate

function getRegionFromZip(zipCode) {
    const firstDigit = zipCode[0];
    const firstTwoDigits = zipCode.substring(0, 2);
    
    if (firstTwoDigits === '33') return 'southflorida';
    if (firstDigit >= '0' && firstDigit <= '2') return 'northeast';
    if (firstDigit >= '3' && firstDigit <= '4') return 'south';
    if (firstDigit >= '5' && firstDigit <= '6') return 'midwest';
    if (firstDigit >= '7' && firstDigit <= '8') return 'west';
    if (firstDigit === '9') return 'northwest';
    return 'midwest';
}

function calculateHDD(heatingDesign) {
    const baseTemp = 65;
    const dailyHDD = Math.max(0, baseTemp - heatingDesign);
    return Math.round(dailyHDD * 365.25);
}

function calculateCDD(coolingDesign) {
    const baseTemp = 65;
    const dailyCDD = Math.max(0, coolingDesign - baseTemp);
    return Math.round(dailyCDD * 365.25);
}

function displayClimateData() {
    // Enforce integrity: heating + HDD required; cooling optional (not used)
    if (!climateData || !Number.isFinite(climateData.heating) || !Number.isFinite(climateData.hdd)) {
        console.error('Invalid ASHRAE county climate data:', climateData);
        showError('Invalid ASHRAE county data for this ZIP.');
        return;
    }
    document.getElementById('locationName').textContent = climateData.name;
    document.getElementById('dataSource').textContent = `Data source: ${climateData.source}`;
    document.getElementById('locationInfo').style.display = 'block';

    document.getElementById('heatingDesign').textContent = climateData.heating;
    // Show cooling design on chart if present (visual only; not used in pricing)
    if (document.getElementById('coolingDesign')) {
        document.getElementById('coolingDesign').textContent = Number.isFinite(climateData.cooling) ? climateData.cooling : '--';
    }

    const avgCold = Math.round((climateData.heating + 65) / 2);
    document.getElementById('avgCold').textContent = avgCold;
    if (document.getElementById('avgHot')) {
        const avgHotVal = Number.isFinite(climateData.cooling) ? Math.round((climateData.cooling + 65) / 2) : null;
        document.getElementById('avgHot').textContent = (avgHotVal != null) ? avgHotVal : '--';
    }
    
    // Update heating load when climate data is available
    updateHeatingLoad();
    
    positionTemperatureMarkers();
    document.getElementById('temperatureBar').style.display = 'block';

    // Show cooling markers/labels if cooling data present
    const hasCooling = Number.isFinite(climateData.cooling);
    const coolingMarker = document.getElementById('coolingMarker');
    if (coolingMarker) coolingMarker.style.display = hasCooling ? '' : 'none';
    const avgHotMarker = document.getElementById('avgHotMarker');
    if (avgHotMarker) avgHotMarker.style.display = hasCooling ? '' : 'none';
}

function positionTemperatureMarkers() {
    const minTemp = -20;
    const maxTemp = 120;
    const range = maxTemp - minTemp;
    
    const heatingPos = ((climateData.heating - minTemp) / range) * 100;
    const avgColdPos = ((Math.round((climateData.heating + 65) / 2) - minTemp) / range) * 100;
    const hasCooling = Number.isFinite(climateData.cooling);
    const coolingPos = hasCooling ? ((climateData.cooling - minTemp) / range) * 100 : null;
    const avgHotPos = hasCooling ? ((Math.round((climateData.cooling + 65) / 2) - minTemp) / range) * 100 : null;

    document.getElementById('heatingMarker').style.left = heatingPos + '%';
    document.getElementById('avgColdMarker').style.left = avgColdPos + '%';
    if (hasCooling && document.getElementById('coolingMarker')) {
        document.getElementById('coolingMarker').style.left = coolingPos + '%';
    }
    if (hasCooling && document.getElementById('avgHotMarker')) {
        document.getElementById('avgHotMarker').style.left = avgHotPos + '%';
    }

    // Position average temp labels to match their markers
    document.querySelector('#avgCold').parentElement.style.left = avgColdPos + '%';
    if (hasCooling) {
        document.querySelector('#avgHot').parentElement.style.left = avgHotPos + '%';
    }

    // Position house icon between average cold and average hot when available
    const housePos = hasCooling ? (avgColdPos + avgHotPos) / 2 : avgColdPos;
    document.getElementById('houseIcon').style.left = housePos + '%';
}

function calculateHVACCosts() {
    const hdd = climateData.hdd;
    const cdd = Number.isFinite(climateData.cdd) ? climateData.cdd : 0;
    const heatingDesign = climateData.heating;
    const coolingDesign = Number.isFinite(climateData.cooling) ? climateData.cooling : 0;

    const electricityRate = parseFloat(document.getElementById('electricityRate').value) || 0.12;
    const gasRate = parseFloat(document.getElementById('gasRate').value) || 1.20;
    const heatPumpCOP = parseFloat(document.getElementById('heatPumpCOP').value) || 3.5;
    const furnaceEfficiency = parseFloat(document.getElementById('furnaceEfficiency').value) || 95;
    const autoX = document.getElementById('autoCrossover') && document.getElementById('autoCrossover').checked;
    let crossoverTemp = parseFloat(document.getElementById('crossoverTemp').value);
    if (!Number.isFinite(crossoverTemp)) crossoverTemp = 35;
    
    if (autoX) {
        const auto = computeAutoCrossoverTemperature(electricityRate, gasRate, furnaceEfficiency, heatPumpCOP);
        crossoverTemp = Math.max(20, Math.min(50, Math.round(auto)));
        const xEl = document.getElementById('crossoverTemp');
        if (xEl) { xEl.value = crossoverTemp; xEl.disabled = true; }
    } else {
        const xEl = document.getElementById('crossoverTemp');
        if (xEl) xEl.disabled = false;
    }

    const systems = {
        heatPump: {
            name: 'Heat Pump System',
            cop: heatPumpCOP
        },
        furnace: {
            name: 'Furnace System',
            furnaceAFUE: furnaceEfficiency / 100
        },
        hybrid: {
            name: 'Hybrid System',
            cop: heatPumpCOP,
            furnaceAFUE: furnaceEfficiency / 100
        }
    };

    const results = {};
    
    for (const [systemType, specs] of Object.entries(systems)) {
        const costs = calculateSystemCosts(systemType, specs, hdd, cdd, heatingDesign, coolingDesign, electricityRate, gasRate, crossoverTemp);
        results[systemType] = costs;
    }

    maxCost = Math.max(results.heatPump.total, results.furnace.total, results.hybrid.total);
    displayCostBars(results);
    displaySystemResults(results);
    showWinner(results);
    updateTechnicalDetails(results, hdd, cdd, heatingDesign, coolingDesign, electricityRate, gasRate, heatPumpCOP, furnaceEfficiency, crossoverTemp);

    const rsTop = document.getElementById('resultsSectionTop');
    if (rsTop) rsTop.style.display = 'block';
    
    // Update hybrid split bar with calculated data
    const hpEff = calculateHeatPumpEfficiency(heatingDesign, crossoverTemp, hdd);
    updateHybridSplitBar(hpEff, heatingDesign, crossoverTemp);

    // Update hybrid decision panel
    updateHybridDecision(results, heatingDesign, crossoverTemp, hdd);
}

function calculateSystemCosts(systemType, specs, hdd, cdd, heatingDesign, coolingDesign, electricityRate, gasRate, crossoverTemp) {
    let annualHeatingCost = 0;
    let annualCoolingCost = 0;

    // Design loads (use actual user input)
    const designHeatingLoad = houseLoads.heating || 50000; // BTU/hr from user input
    const designCoolingLoad = houseLoads.cooling || 40000; // BTU/hr from user input
    
    // Indoor design temperature (standard for degree day calculations)
    const indoorTemp = 65; // °F (standard indoor temp for HDD/CDD calculations)
    const heatingDesignDiff = indoorTemp - heatingDesign; // Temperature difference for heating
    const coolingDesignDiff = coolingDesign - indoorTemp; // Temperature difference for cooling
    
    // Calculate heat loss rate (BTU/hr/°F) from design load
    // Design load = heat loss rate × design temp difference
    const heatLossRate = designHeatingLoad / heatingDesignDiff; // BTU/hr/°F
    const coolGainRate = designCoolingLoad / coolingDesignDiff; // BTU/hr/°F
    
    // Calculate annual energy using proper degree day method
    // Annual Energy = Heat Loss Rate × HDD × 24 hours
    const annualHeatingLoad = heatLossRate * hdd * 24; // Total BTU/year
    const annualCoolingLoad = coolGainRate * cdd * 24; // Total BTU/year
    
    // Debug the calculation
    console.log('Annual Load Calculation:');
    console.log('Design Heating Load:', designHeatingLoad, 'BTU/hr');
    console.log('Heating Design Diff:', heatingDesignDiff, '°F');
    console.log('Heat Loss Rate:', heatLossRate, 'BTU/hr/°F');
    console.log('HDD:', hdd);
    console.log('Annual Heating Load:', annualHeatingLoad, 'BTU/year');

    let annualTherms = 0;
    let annualKWh = 0;

    if (systemType === 'furnace') {
        // Gas furnace heating
        const heatingTherms = annualHeatingLoad / (100000 * specs.furnaceAFUE); // 100,000 BTU/therm
        annualHeatingCost = heatingTherms * gasRate;
        annualCoolingCost = 0; // No cooling
        annualTherms = heatingTherms;

    } else if (systemType === 'heatPump') {
        // Heat pump heating - Use COP for heating efficiency
        const heatingkWh = annualHeatingLoad / (specs.cop * 3412); // COP×3412 BTU per kWh
        annualHeatingCost = heatingkWh * electricityRate;
        annualCoolingCost = 0; // No cooling
        annualKWh = heatingkWh;
        console.log('Heat pump debug:', {
            annualHeatingLoad,
            cop: specs.cop,
            heatingkWh,
            electricityRate,
            annualHeatingCost
        });

    } else if (systemType === 'hybrid') {
        // Use user-specified crossover temperature
        const xover = Number.isFinite(crossoverTemp) ? crossoverTemp : 35;
        
        // Calculate what percentage of heating degree days are above/below crossover
        let heatPumpPercentage;
        if (heatingDesign > xover) {
            heatPumpPercentage = 1.0; // Always use heat pump
        } else if (heatingDesign > (xover - 15)) {
            heatPumpPercentage = 0.7; // Mostly heat pump
        } else if (heatingDesign > (xover - 25)) {
            heatPumpPercentage = 0.5; // Split operation
        } else {
            heatPumpPercentage = 0.3; // Mostly gas backup
        }
        
        // Split the heating load
        const heatPumpHeatingLoad = annualHeatingLoad * heatPumpPercentage;
        const gasHeatingLoad = annualHeatingLoad * (1 - heatPumpPercentage);
        
        // Calculate costs for each portion
        const heatPumpkWh = heatPumpHeatingLoad / (specs.cop * 3412); // COP×3412 BTU per kWh
        const gasHeatingTherms = gasHeatingLoad / (100000 * specs.furnaceAFUE);
        
        annualHeatingCost = (heatPumpkWh * electricityRate) + (gasHeatingTherms * gasRate);
        annualCoolingCost = 0; // No cooling
        annualKWh = heatPumpkWh;
        annualTherms = gasHeatingTherms;
    }

    const annualEnergyCost = annualHeatingCost + annualCoolingCost;

    return {
        install: 0, // No installation cost in this calculation
        energy: Math.round(annualEnergyCost),
        maintenance: 0, // No maintenance cost in this calculation
        total: Math.round(annualEnergyCost),
        annualTherms,
        annualKWh
    };
}

function calculateHeatPumpEfficiency(heatingDesign, crossoverTemp, hdd) {
    // Calculate heat pump share using actual HDD and temperature thresholds
    // Heat pump runs when temperature > crossover, furnace when temperature <= crossover
    const baseTemp = 65; // HDD base temperature

    if (!hdd || hdd <= 0) {
        return null; // No heating data available - use null to indicate no data
    }

    // If crossover temperature is above or equal to base temp, heat pump handles everything
    if (crossoverTemp >= baseTemp) {
        return 1.0;
    }

    // If crossover temperature is at or below design temp, furnace handles everything
    if (crossoverTemp <= heatingDesign) {
        return 0.0;
    }

    // Calculate the temperature range where heat pump operates
    const totalRange = baseTemp - heatingDesign; // Total heating range
    const hpRange = baseTemp - crossoverTemp; // Range where heat pump operates

    if (totalRange <= 0) {
        return 0;
    }

    // Heat pump handles the portion above crossover temperature
    const share = Math.min(1, hpRange / totalRange);

    return share;
}

function calculateCrossoverTemperature(heatingDesign) {
    // Crossover temperature is typically 35°F for most heat pumps
    // Below this temperature, heat pump efficiency drops significantly
    return 35;
}

// Compute economic break-even crossover temperature from prices, AFUE, and a simple COP curve
function computeAutoCrossoverTemperature(pricePerKWh, pricePerTherm, furnaceEffPercent, copAt47F) {
    const afue = Math.max(0.5, Math.min(1.0, (parseFloat(furnaceEffPercent) || 95) / 100));
    const e = Math.max(0.01, parseFloat(pricePerKWh) || 0.12);
    const g = Math.max(0.01, parseFloat(pricePerTherm) || 1.2);
    const cop47 = Math.max(1.0, parseFloat(copAt47F) || 3.5);
    const cop17 = Math.max(1.0, cop47 - 1.5); // simple default slope
    const slopePerDeg = (cop17 - cop47) / (17 - 47); // ~ (ΔCOP)/(-30)
    const copThreshold = 29.3 * afue * (e / g);
    if (Math.abs(slopePerDeg) < 1e-6) return 35; // avoid divide-by-zero
    const t = 47 + (copThreshold - cop47) / slopePerDeg;
    // Clamp to UI range
    return Math.max(0, Math.min(70, t));
}

function updateHybridDecision(results, heatingDesign, crossoverTemp, hdd) {
    try {
        const hpEff = calculateHeatPumpEfficiency(heatingDesign, crossoverTemp, hdd);
        const hpPct = Math.round(hpEff * 100);
        const gasPct = 100 - hpPct;
        const line = `Above ${crossoverTemp}°F use heat pump; below ${crossoverTemp}°F use furnace.`;
        const split = `Season split: ${hpPct}% heat pump, ${gasPct}% furnace.`;
        const r = results || {};
        const hpCost = r.heatPump ? r.heatPump.total : NaN;
        const gasCost = r.furnace ? r.furnace.total : NaN;
        const hybCost = r.hybrid ? r.hybrid.total : NaN;
        let savingsText = 'Savings: --';
        let lowestBadge = false;
        if ([hpCost, gasCost, hybCost].every(Number.isFinite)) {
            const saveVsHP = hpCost - hybCost;
            const saveVsGas = gasCost - hybCost;
            savingsText = `Hybrid saves $${Math.round(Math.max(0, saveVsHP)).toLocaleString()} vs heat pump and $${Math.round(Math.max(0, saveVsGas)).toLocaleString()} vs furnace (per year).`;
            lowestBadge = (hybCost <= hpCost && hybCost <= gasCost);
        }
        const lineEl = document.getElementById('hybridDecisionLine');
        const splitEl = document.getElementById('hybridSeasonSplit');
        const saveEl = document.getElementById('hybridSavingsLine');
        const badgeEl = document.getElementById('hybridDecisionBadge');
        if (lineEl) lineEl.textContent = line;
        if (splitEl) splitEl.textContent = split;
        if (saveEl) saveEl.textContent = savingsText;
        if (badgeEl) badgeEl.style.display = lowestBadge ? 'inline-block' : 'none';
    } catch (e) {
        console.warn('updateHybridDecision error', e);
    }
}

function displayCostBars(results) {
    // Update the cost amounts in the boxes
    document.getElementById('heatPumpTotal').textContent = `$${Math.round(results.heatPump.total)}`;
    document.getElementById('furnaceTotal').textContent = `$${Math.round(results.furnace.total)}`;
    document.getElementById('hybridTotal').textContent = `$${Math.round(results.hybrid.total)}`;

    // Find the lowest cost
    const costs = [
        { type: 'heatPump', cost: results.heatPump.total },
        { type: 'furnace', cost: results.furnace.total },
        { type: 'hybrid', cost: results.hybrid.total }
    ];
    
    const lowestCost = Math.min(...costs.map(c => c.cost));
    const lowestType = costs.find(c => c.cost === lowestCost).type;

    // Remove 'lowest' class from all boxes
    document.getElementById('heatPumpBox').classList.remove('lowest');
    document.getElementById('furnaceBox').classList.remove('lowest');
    document.getElementById('hybridBox').classList.remove('lowest');

    // Add 'lowest' class to the cheapest option
    document.getElementById(lowestType + 'Box').classList.add('lowest');
}

function displaySystemResults(results) {
    const systems = ['heatPump', 'furnace', 'hybrid'];
    
    systems.forEach(system => {
        document.getElementById(system + 'Total').textContent = '$' + results[system].total.toLocaleString();
    });

    // Emissions (toggle)
    const showEm = document.getElementById('includeEmissions')?.checked;
    const gasMtPerTherm = 0.0053; // metric tons CO2/therm (EPA combustion)
    const elecMtPerKWh = 0.000394; // metric tons CO2/kWh (eGRID delivered avg)

    const setEm = (idBase, therms, kwh) => {
        // Always hide emissions text inside cost boxes
        const boxText = document.getElementById(idBase + 'Emissions');
        if (boxText) boxText.style.display = 'none';

        // Toggle off: clear coal rows and labels, hide bar area
        if (!showEm) {
            ['hp','furnace','hybrid'].forEach(key => {
                const r1 = document.getElementById(key + 'CoalRow1');
                const r2 = document.getElementById(key + 'CoalRow2');
                const lab = document.getElementById(key + 'Co2Label');
                if (r1) r1.innerHTML = '';
                if (r2) r2.innerHTML = '';
                if (lab) { lab.textContent = ''; lab.removeAttribute('data-tooltip'); }
            });
            const bars = document.getElementById('emissionsBars');
            if (bars) bars.style.display = 'none';
            return;
        }

        // Calculate emissions
        const mt = (therms * gasMtPerTherm) + (kwh * elecMtPerKWh);
        const mtRounded = Math.round(mt * 100) / 100; // X.XX
        const lbs = mt * 2204.62;
        const lbsRounded = Math.round(lbs).toLocaleString();

        // Update the label to the right of coal chart
        const labelEl = document.getElementById(idBase + 'Co2Label');
        if (labelEl) {
            labelEl.textContent = `${mtRounded} t CO2`;
            labelEl.setAttribute('data-tooltip', `${lbsRounded} lbs CO2 per year`);
        }

        // Coal bar: normalize against 80% furnace baseline
        const baselineTherms = (houseLoads.heating / (65 - climateData.heating)) * (climateData.hdd * 24) / (100000 * 0.80);
        const baselineMt = baselineTherms * gasMtPerTherm;
        const ratio = baselineMt > 0 ? Math.min(1, mt / baselineMt) : 0;
        const maxLumps = 24; // two rows of 12 for compact width
        const lumps = Math.round(ratio * maxLumps);
        const row1 = document.getElementById(idBase + 'CoalRow1');
        const row2 = document.getElementById(idBase + 'CoalRow2');
        if (row1 && row2) {
            row1.innerHTML = '';
            row2.innerHTML = '';
            let remaining = lumps;
            for (let col = 0; col < 12; col++) {
                const d1 = document.createElement('div');
                d1.className = 'coal-lump' + (remaining > 0 ? '' : ' empty');
                d1.setAttribute('data-tooltip', `${lbsRounded} lbs CO2 per year`);
                row1.appendChild(d1);
                if (remaining > 0) remaining--;
                const d2 = document.createElement('div');
                d2.className = 'coal-lump' + (remaining > 0 ? '' : ' empty');
                d2.setAttribute('data-tooltip', `${lbsRounded} lbs CO2 per year`);
                row2.appendChild(d2);
                if (remaining > 0) remaining--;
            }
            const bars = document.getElementById('emissionsBars');
            if (bars) bars.style.display = 'block';
        }
    };

    setEm('hp', results.heatPump.annualTherms||0, results.heatPump.annualKWh||0);
    setEm('furnace', results.furnace.annualTherms||0, results.furnace.annualKWh||0);
    setEm('hybrid', results.hybrid.annualTherms||0, results.hybrid.annualKWh||0);
}

function showWinner(results) {
    const costs = Object.values(results).map(r => r.total);
    const minCost = Math.min(...costs);
    
    let winner = 'heatPump';
    for (const [systemType, result] of Object.entries(results)) {
        if (result.total === minCost) {
            winner = systemType;
            break;
        }
    }

    // Remove existing lowest classes
    document.querySelectorAll('.cost-box').forEach(box => box.classList.remove('lowest'));
    
    // Add winner class to the winning box (CSS handles the "LOWEST RUN COST" badge)
    const winnerBox = document.getElementById(winner + 'Box');
    if (winnerBox) {
        winnerBox.classList.add('lowest');
    }
}

function showLoading() {
    document.getElementById('loadingSection').style.display = 'block';
    document.getElementById('lookupBtn').disabled = true;
}

function hideLoading() {
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('lookupBtn').disabled = false;
}

function showError(message) {
    const errorDiv = document.getElementById('errorSection');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function hideError() {
    document.getElementById('errorSection').style.display = 'none';
}

function hideResults() {
    document.getElementById('locationInfo').style.display = 'none';
    // Don't hide temperature bar or results section - keep them visible
}

// Event listeners
document.getElementById('zipCode').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        lookupClimateData();
    }
});

// Recalculate when inputs change
document.getElementById('electricityRate').addEventListener('input', recalculateIfDataAvailable);
document.getElementById('gasRate').addEventListener('input', recalculateIfDataAvailable);
document.getElementById('heatPumpCOP').addEventListener('input', recalculateIfDataAvailable);
document.getElementById('furnaceEfficiency').addEventListener('input', recalculateIfDataAvailable);
document.getElementById('crossoverTemp').addEventListener('input', recalculateIfDataAvailable);
const autoX = document.getElementById('autoCrossover');
if (autoX) autoX.addEventListener('change', recalculateIfDataAvailable);

function recalculateIfDataAvailable() {
    if (climateData) {
        calculateHVACCosts();
    }
}

function toggleTechnicalInfo() {
    const techInfo = document.getElementById('technicalInfo');
    const toggleText = document.getElementById('techToggleText');
    const toggleIcon = document.getElementById('techToggleIcon');
    
    if (techInfo.style.display === 'none') {
        techInfo.style.display = 'block';
        toggleText.textContent = 'Hide Technical Details';
        toggleIcon.textContent = '▲';
    } else {
        techInfo.style.display = 'none';
        toggleText.textContent = 'Show Technical Details';
        toggleIcon.textContent = '▼';
    }
}

// JS tooltip to avoid covering inputs or going off-screen
(function() {
    const body = document.body;
    body.classList.add('js-tooltips-active');
    let bubble;
    let hideTimer;
    function showBubble(target) {
        const text = target.getAttribute('data-tooltip');
        if (!text) return;
        if (!bubble) {
            bubble = document.createElement('div');
            bubble.className = 'tooltip-bubble';
            document.body.appendChild(bubble);
        }
        const inCoal = !!(target.closest && target.closest('#emissionsBars'));
        const isHPPerf = (target.id === 'heatPumpCOP' || target.getAttribute('for') === 'heatPumpCOP');
        const isHomeBTU = (target.id === 'heatingLoadInput' || target.getAttribute('for') === 'heatingLoadInput');
        let theme = '';
        if (inCoal) theme = ' theme-coal';
        else if (isHPPerf) theme = ' theme-hp';
        else if (isHomeBTU) theme = ' theme-home';
        else theme = ' theme-accent';
        bubble.className = 'tooltip-bubble' + theme;
        // Convert escaped newlines in data attributes ("\n") into real breaks
        const html = String(text)
            .replace(/\\n\\n/g, '<br><br>')
            .replace(/\\n/g, '<br>');
        bubble.innerHTML = html;
        // Position to the side that fits best
        const row = target.closest('.input-row');
        const rect = row ? row.getBoundingClientRect() : target.getBoundingClientRect();
        const padding = 12;
        const prefRightX = rect.right + padding;
        const prefLeftX = rect.left - padding;
        const topY = Math.max(12, rect.top);
        bubble.style.visibility = 'hidden';
        bubble.style.left = '0px';
        bubble.style.top = '0px';
        bubble.style.display = 'block';
        const bw = bubble.offsetWidth;
        const bh = bubble.offsetHeight;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        let x, y;
        // Special positioning for coal charts: center above/below the emission bar to avoid drifting into neighbors
        if (inCoal) {
            const bar = target.closest('.emission-bar') || target.closest('.emissions-grid') || target;
            const brect = bar.getBoundingClientRect();
            // Force BELOW coal chart to avoid covering content; clamp if viewport is short
            const belowY = brect.bottom + padding;
            y = (belowY + bh <= vh) ? belowY : Math.max(12, Math.min(vh - bh - 12, belowY));
            x = Math.max(12, Math.min(vw - bw - 12, brect.left + (brect.width - bw)/2));
            bubble.style.left = x + 'px';
            bubble.style.top = y + 'px';
            bubble.style.visibility = 'visible';
            return;
        }
        // Prefer left or right of the entire row to avoid covering either label or field.
        if (target.classList.contains('tooltip-left')) {
            x = Math.max(12, Math.min(vw - bw - 12, rect.left - padding - bw));
            y = Math.max(12, Math.min(vh - bh - 12, rect.top + (rect.height - bh)/2));
        } else if (target.classList.contains('tooltip-right')) {
            x = Math.max(12, Math.min(vw - bw - 12, rect.right + padding));
            y = Math.max(12, Math.min(vh - bh - 12, rect.top + (rect.height - bh)/2));
        } else if (target.classList.contains('tooltip-below')) {
            // Place below the entire control-group to avoid covering label/input
            const group = target.closest('.control-group');
            const grect = group ? group.getBoundingClientRect() : rect;
            y = Math.max(12, Math.min(vh - bh - 12, grect.bottom + padding));
            x = Math.max(12, Math.min(vw - bw - 12, grect.left + (grect.width - bw)/2));
        } else {
            // Fallback: above/below then center horizontally
            const belowY = rect.bottom + padding;
            const aboveY = rect.top - padding - bh;
            const canBelow = belowY + bh <= vh;
            const canAbove = aboveY >= 0;
            if (canBelow) {
                y = belowY;
            } else if (canAbove) {
                y = aboveY;
            } else {
                y = Math.max(12, Math.min(vh - bh - 12, rect.top + rect.height + padding));
            }
            if (prefRightX + bw <= vw) {
                x = prefRightX;
            } else if (prefLeftX - bw >= 0) {
                x = prefLeftX - bw;
            } else {
                x = Math.max(12, Math.min(vw - bw - 12, rect.left + (rect.width - bw)/2));
            }
        }
        // Prevent bubble from touching window edges
        x = Math.max(12, Math.min(vw - (bubble.offsetWidth + 12), x));
        y = Math.max(12, Math.min(vh - (bubble.offsetHeight + 12), y));
        bubble.style.left = x + 'px';
        bubble.style.top = y + 'px';
        bubble.style.visibility = 'visible';
    }
    function hideBubble() {
        if (bubble) bubble.style.display = 'none';
    }
    document.addEventListener('mouseenter', function(e) {
        if (!e.target || typeof e.target.closest !== 'function') return; // Error guard
        const t = e.target.closest('[data-tooltip]');
        if (t) {
            if (hideTimer) { clearTimeout(hideTimer); hideTimer = null; }
            showBubble(t);
        }
    }, true);
    document.addEventListener('mouseleave', function(e) {
        if (!e.target || typeof e.target.closest !== 'function') return; // Error guard
        const t = e.target.closest('[data-tooltip]');
        if (t) {
            hideTimer = setTimeout(() => hideBubble(), 200);
        }
    }, true);
})();

// Modes system: basic | guided | pro | nonprofit
(function initModes() {
    function getQueryParam(name) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }
    const mode = (getQueryParam('mode') || 'pro').toLowerCase();
    const sections = {
        equipment: document.getElementById('equipmentGroup'),
        hybridRow: document.getElementById('hybridControlsRow'),
        homeNeeds: document.getElementById('homeNeedsGroup'),
        emissionsBars: document.getElementById('emissionsBars'),
        hybridDecision: document.getElementById('hybridDecision'),
        technical: document.getElementById('technicalSection'),
        title: document.getElementById('appTitle')
    };

    function show(el, visible) { if (el) el.style.display = visible ? '' : 'none'; }

    switch (mode) {
        case 'basic':
            show(sections.equipment, false);
            show(sections.hybridRow, false);
            show(sections.technical, false);
            show(sections.emissionsBars, false);
            show(sections.hybridDecision, true);
            break;
        case 'nonprofit':
            show(sections.equipment, true);
            show(sections.hybridRow, true);
            show(sections.technical, false);
            show(sections.emissionsBars, true);
            show(sections.hybridDecision, true);
            if (sections.title) sections.title.textContent = 'Electrify Now: Home Heating Cost Guide';
            break;
        case 'pro':
            show(sections.equipment, true);
            show(sections.hybridRow, true);
            show(sections.technical, true);
            show(sections.emissionsBars, true);
            show(sections.hybridDecision, true);
            break;
        case 'guided':
        default:
            show(sections.equipment, true);
            show(sections.hybridRow, true);
            show(sections.technical, true);
            show(sections.emissionsBars, true);
            show(sections.hybridDecision, true);
            break;
    }
})();

function updateTechnicalDetails(results, hdd, cdd, heatingDesign, coolingDesign, electricityRate, gasRate, heatPumpCOP, furnaceEfficiency, crossoverTemp) {
    // House specifications
    document.getElementById('houseSize').textContent = '2,000 sq ft';
    document.getElementById('heatingLoadFactor').textContent = '1.2 BTU/sq ft/HDD';
    const clf = document.getElementById('coolingLoadFactor');
    if (clf) clf.parentElement.style.display = 'none';

    // Climate data
    document.getElementById('hddValue').textContent = Number.isFinite(hdd) ? hdd.toLocaleString() : '--';
    const cddEl = document.getElementById('cddValue');
    if (cddEl) {
        if (Number.isFinite(cdd) && cdd > 0) {
            cddEl.textContent = cdd.toLocaleString();
            cddEl.parentElement.style.display = '';
        } else {
            cddEl.parentElement.style.display = 'none';
        }
    }
    document.getElementById('heatingDesignValue').textContent = Number.isFinite(heatingDesign) ? (heatingDesign + '°F') : '--';
    const cdv = document.getElementById('coolingDesignValue');
    if (cdv) {
        if (Number.isFinite(coolingDesign) && coolingDesign !== 0) {
            cdv.textContent = coolingDesign + '°F';
            cdv.parentElement.style.display = '';
        } else {
            cdv.parentElement.style.display = 'none';
        }
    }

    // Energy calculations
    const houseSize = 2000;
    const heatingLoadFactor = 1.2;
    const totalHeatingBTU = hdd * houseSize * heatingLoadFactor;
    
    document.getElementById('totalHeatingBTU').textContent = totalHeatingBTU.toLocaleString() + ' BTU';
    const tcb = document.getElementById('totalCoolingBTU');
    if (tcb) tcb.parentElement.style.display = 'none';
    document.getElementById('electricityRateValue').textContent = '$' + electricityRate + '/kWh';
    document.getElementById('gasRateValue').textContent = '$' + gasRate + '/therm';

    // System performance details
    document.getElementById('heatPumpCOPValue').textContent = heatPumpCOP;
    document.getElementById('furnaceAFUEValue').textContent = furnaceEfficiency + '%';
    const xoverEl = document.getElementById('crossoverTempValue');
    if (xoverEl) xoverEl.textContent = crossoverTemp + '°F';

    // Totals 5/10/15 years
    const years = [5,10,15];
    const furnace = results.furnace;
    const hp = results.heatPump;
    const hybrid = results.hybrid;
    const tech = document.getElementById('technicalInfo');
    if (tech) {
        const existing = tech.querySelector('#miniCharts');
        if (existing) existing.remove();
        const wrap = document.createElement('div');
        wrap.id = 'miniCharts';
        wrap.className = 'tech-group';
        // Build 15-year summary (highest cost first, with % saved for others)
        // Years input (default 15)
        const yearsInputId = 'runYearsInput';
        let summaryYears = runYears;
        const prevInput = document.getElementById(yearsInputId);
        if (prevInput) {
            const y = parseInt(prevInput.value, 10);
            if (Number.isFinite(y) && y > 0 && y <= 30) summaryYears = y;
        }
        const totals = [
            { key: 'Heat Pump', val: hp.total*summaryYears },
            { key: 'Furnace', val: furnace.total*summaryYears },
            { key: 'Hybrid', val: hybrid.total*summaryYears }
        ].sort((a,b) => b.val - a.val);
        const maxVal = totals[0].val || 1;
        const rows = totals.map((t, idx) => {
            const totalTxt = `$${Math.round(t.val).toLocaleString()}`;
            if (idx === 0) {
                return `<tr><td class="label">${t.key}</td><td class="total">${totalTxt}</td><td class="saved"></td></tr>`;
            }
            const savedAbs = maxVal - t.val;
            const savedPct = 100 * (savedAbs / maxVal);
            const savedTxt = isFinite(savedPct) ? `Savings: $${Math.round(savedAbs).toLocaleString()} (${savedPct.toFixed(1)}%)` : '';
            return `<tr><td class="label">${t.key}</td><td class="total">${totalTxt}</td><td class="saved">${savedTxt}</td></tr>`;
        }).join('');
        const summaryHtml = '<div id="fifteenYearSummary"><div class="summary-box">' +
            '<h6>Run Cost</h6>' +
            `<div class="summary-years"><label for="${yearsInputId}">Years:</label><input id="${yearsInputId}" type="number" min="1" max="30" step="1" value="${summaryYears}" inputmode="numeric" pattern="[0-9]*"></div>` +
            `<table class="summary-table"><tbody>${rows}</tbody></table>` +
            '</div></div>';
        wrap.innerHTML =
            '<div class="mini-charts">' +
                '<div class="mini-chart" id="runCostSummary">' + summaryHtml + '</div>' +
                '<div class="mini-chart" id="co2Chart"><h6>CO2 Totals (metric tons)</h6><div class="mini-chart-body"></div></div>' +
            '</div>';
        tech.appendChild(wrap);

        // Recompute on years change
        const yInput = document.getElementById(yearsInputId);
        if (yInput && !yInput._bound) {
            const handler = () => {
                const raw = yInput.value.trim();
                if (raw === '') { // allow temporary empty state while editing
                    return;
                }
                const val = parseInt(raw, 10);
                if (Number.isFinite(val)) {
                    // clamp to 1..30
                    const clamped = Math.max(1, Math.min(30, val));
                    if (clamped !== val) {
                        yInput.value = clamped;
                    }
                    runYears = clamped;
                    updateTechnicalDetails(results, hdd, cdd, heatingDesign, coolingDesign, electricityRate, gasRate, heatPumpCOP, furnaceEfficiency, crossoverTemp);
                }
            };
            yInput.addEventListener('input', handler);
            yInput.addEventListener('change', handler);
            yInput._bound = true;
        }

        const build = (mountId, groups, formatter) => {
            const mount = wrap.querySelector('#' + mountId);
            const body = mount.querySelector('.mini-chart-body');
            body.innerHTML = '';
            groups.forEach(g => {
                const gEl = document.createElement('div');
                gEl.className = 'mini-group';
                const barsWrap = document.createElement('div');
                barsWrap.className = 'mini-bars';
                years.forEach((y, idx) => {
                    const v = g.values[y];
                    const bar = document.createElement('div');
                    bar.className = 'mini-bar year' + y + ' ' + g.className;
                    const max = Math.max(...groups.flatMap(gr => years.map(k=>gr.values[k])));
                    const h = max > 0 ? Math.max(2, Math.round((v / max) * 140)) : 2;
                    bar.style.height = h + 'px';
                    bar.setAttribute('data-value', formatter(v));
                    barsWrap.appendChild(bar);
                });
                gEl.appendChild(barsWrap);
                const lab = document.createElement('div');
                lab.className = 'mini-label';
                lab.textContent = g.label;
                gEl.appendChild(lab);
                body.appendChild(gEl);
            });
        };

        build('co2Chart', [
            { label: 'Heat Pump', className: 'color-heatpump', values: {5:hp.annualKWh*0.000394*5,10:hp.annualKWh*0.000394*10,15:hp.annualKWh*0.000394*15} },
            { label: 'Furnace', className: 'color-furnace', values: {5:furnace.annualTherms*0.0053*5,10:furnace.annualTherms*0.0053*10,15:furnace.annualTherms*0.0053*15} },
            { label: 'Hybrid', className: 'color-hybrid', values: {5:(hybrid.annualTherms*0.0053+hybrid.annualKWh*0.000394)*5,10:(hybrid.annualTherms*0.0053+hybrid.annualKWh*0.000394)*10,15:(hybrid.annualTherms*0.0053+hybrid.annualKWh*0.000394)*15} }
        ], v => (Math.round(v*100)/100).toString());
    }

    // Calculate efficiencies
    const heatPumpHeatingEff = (heatPumpCOP * 3.412).toFixed(1) + '%';
    const furnaceHeatingEff = furnaceEfficiency + '%';

    document.getElementById('heatPumpHeatingEff').textContent = heatPumpHeatingEff;
    document.getElementById('furnaceHeatingEff').textContent = furnaceHeatingEff;
    const hpce = document.getElementById('heatPumpCoolingEff');
    if (hpce) hpce.parentElement.style.display = 'none';
    const fce = document.getElementById('furnaceCoolingEff');
    if (fce) fce.parentElement.style.display = 'none';

    // Hybrid system details
    const heatPumpEfficiency = calculateHeatPumpEfficiency(heatingDesign, crossoverTemp, hdd);
    const heatPumpUsage = (heatPumpEfficiency * 100).toFixed(0) + '%';
    const furnaceUsage = ((1 - heatPumpEfficiency) * 100).toFixed(0) + '%';
    
    document.getElementById('crossoverTemp').textContent = crossoverTemp + '°F';
    document.getElementById('hybridHeatPumpUsage').textContent = heatPumpUsage;
    document.getElementById('hybridFurnaceUsage').textContent = furnaceUsage;
    document.getElementById('hybridHeatingEff').textContent = 'Mixed (see above)';
    const hce = document.getElementById('hybridCoolingEff');
    if (hce) hce.parentElement.style.display = 'none';

}

// Use this if you ALREADY have a percent (0..100)
function setHybridSplit(hpPercent){
    const el = document.getElementById('hybridSplit');
    if(!el){ console.warn('hybridSplit element not found'); return; }
    const hp = el.querySelector('.hs__hp');
    const fn = el.querySelector('.hs__fn');
    const hpLabel = document.getElementById('hpLabel');
    const fnLabel = document.getElementById('furnaceLabel');
    if(!Number.isFinite(hpPercent)){
        return setHybridSplitDefault();
    }
    hpPercent = Math.max(0, Math.min(100, hpPercent));
    const fnPercent = 100 - hpPercent;
    el.setAttribute('data-state','populated');
    hp.style.width = hpPercent + '%';
    fn.style.width = fnPercent + '%';
    if(hpLabel) hpLabel.textContent = `Heat Pump ${hpPercent.toFixed(0)}%`;
    if(fnLabel) fnLabel.textContent = `Furnace ${fnPercent.toFixed(0)}%`;
}

// Use this if you have LOADS/BTUs/HOURS instead of a percent
function updateHybridSplitFromLoads(hpLoad, furnaceLoad){
    const hp = Number(hpLoad);
    const fn = Number(furnaceLoad);
    if(!(hp >= 0) || !(fn >= 0)){
        return setHybridSplitDefault();
    }
    const total = hp + fn;
    if(total <= 0){
        return setHybridSplitDefault();
    }
    const hpPct = (hp / total) * 100;
    setHybridSplit(hpPct);
}

function setHybridSplitDefault(){
    const el = document.getElementById('hybridSplit');
    if(!el) return;
    el.setAttribute('data-state','default');
    const hp = el.querySelector('.hs__hp');
    const fn = el.querySelector('.hs__fn');
    const hpLabel = document.getElementById('hpLabel');
    const fnLabel = document.getElementById('furnaceLabel');
    if(hp) hp.style.width = '50%';
    if(fn) fn.style.width = '50%';
    if(hpLabel) hpLabel.textContent = 'Heat Pump';
    if(fnLabel) fnLabel.textContent = 'Furnace';
}

// Clean Hybrid Split Bar Implementation
function updateHybridSplitBar(heatPumpEfficiency, heatingDesign, crossoverTemp) {
    if (heatPumpEfficiency === null || heatPumpEfficiency === undefined || heatPumpEfficiency < 0 || heatPumpEfficiency > 1) {
        return setHybridSplitDefault();
    }
    const hpPercent = heatPumpEfficiency * 100;
    setHybridSplit(hpPercent);
}

function toggleTCO() {
    const on = document.getElementById('includeTCO').checked;
    document.getElementById('card-ownership').style.display = on ? '' : 'none';
    // Toggle TCO lines under boxes
    const lines = document.querySelectorAll('.tco-line');
    lines.forEach(el => el.style.display = on ? '' : 'none');
    if (on) recalculateIfDataAvailable();
}

function parseMoney(inputId) {
    const el = document.getElementById(inputId);
    if (!el) return 0;
    const n = Number(String(el.value).replace(/[^0-9.\-]/g, ''));
    return Number.isFinite(n) ? n : 0;
}

function npvOfSeries(years, ratePct, annualSeries) {
    const r = (Number(ratePct) || 0) / 100;
    let npv = 0;
    for (let y = 1; y <= years; y++) {
        const cf = annualSeries[y-1] || 0;
        npv += cf / Math.pow(1 + r, y);
    }
    return npv;
}

function computeCarbonCost(annualTons, pricePerTon) {
    const p = Number(pricePerTon) || 0;
    return (annualTons || 0) * p;
}

function computeTCO(results) {
    const enabled = document.getElementById('includeTCO') && document.getElementById('includeTCO').checked;
    if (!enabled) return;
    const years = Math.max(1, Math.min(30, Number(document.getElementById('tcoYears').value) || 15));
    const rate = Number(document.getElementById('tcoDiscount').value) || 0;

    const install = {
        heatPump: parseMoney('tcoInstallHP'),
        furnace: parseMoney('tcoInstallF'),
        hybrid: parseMoney('tcoInstallH')
    };
    const maint = {
        heatPump: parseMoney('tcoMaintHP'),
        furnace: parseMoney('tcoMaintF'),
        hybrid: parseMoney('tcoMaintH')
    };
    const rebate = {
        heatPump: parseMoney('tcoRebateHP'),
        furnace: parseMoney('tcoRebateF'),
        hybrid: parseMoney('tcoRebateH')
    };
    const carbonPrice = Number(document.getElementById('tcoCarbonPrice').value) || 0;

    // Annual run costs from existing results
    const annualRun = {
        heatPump: results.heatPump.total,
        furnace: results.furnace.total,
        hybrid: results.hybrid.total
    };
    // Annual emissions (metric tons) derived from existing labels if available later; default 0
    const annualTons = { heatPump: 0, furnace: 0, hybrid: 0 };

    const series = {};
    ['heatPump', 'furnace', 'hybrid'].forEach(k => {
        const carbonCost = computeCarbonCost(annualTons[k], carbonPrice);
        const annual = (annualRun[k] + maint[k] + carbonCost);
        series[k] = Array.from({ length: years }, () => annual);
    });

    const tco = {};
    Object.keys(series).forEach(k => {
        const upfront = Math.max(0, install[k] - rebate[k]);
        const pv = npvOfSeries(years, rate, series[k]);
        tco[k] = upfront + pv;
    });

    // Update UI
    document.querySelectorAll('.tco-years').forEach(el => el.textContent = String(years));
    const fmt = (v) => '$' + Math.round(v).toLocaleString();
    const elHP = document.getElementById('tcoHeatPump'); if (elHP) elHP.textContent = `TCO (NPV, ${years} yrs): ${fmt(tco.heatPump)}`;
    const elF  = document.getElementById('tcoFurnace'); if (elF) elF.textContent = `TCO (NPV, ${years} yrs): ${fmt(tco.furnace)}`;
    const elH  = document.getElementById('tcoHybrid'); if (elH) elH.textContent = `TCO (NPV, ${years} yrs): ${fmt(tco.hybrid)}`;
}

// Recalc hook: extend existing pipeline without breaking defaults
const _origDisplaySystemResults = displaySystemResults;
displaySystemResults = function(results) {
    _origDisplaySystemResults(results);
    computeTCO(results);
};

// Wire inputs to recalc
function wireTcoInputs() {
    const ids = ['tcoYears','tcoDiscount','tcoInstallHP','tcoInstallF','tcoInstallH','tcoMaintHP','tcoMaintF','tcoMaintH','tcoRebateHP','tcoRebateF','tcoRebateH','tcoCarbonPrice'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', recalculateIfDataAvailable);
    });
}
document.addEventListener('DOMContentLoaded', wireTcoInputs);
