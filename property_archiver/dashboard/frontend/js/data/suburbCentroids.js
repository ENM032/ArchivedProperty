/**
 * Offline Geographic Centroid Lookup Table for South African Suburbs & Metros.
 * Provides fallback coordinates when portal HTML omits explicit GPS tags.
 */
export const SUBURB_CENTROIDS = {
    // Gauteng - Sandton & Johannesburg
    "rivonia": [-26.0544, 28.0587],
    "bryanston": [-26.0528, 28.0211],
    "sandton": [-26.1076, 28.0567],
    "morningside": [-26.0850, 28.0600],
    "lonehill": [-26.0180, 28.0220],
    "fourways": [-26.0150, 28.0050],
    "paulshof": [-26.0350, 28.0480],
    "sunninghill": [-26.0300, 28.0700],
    "douglasdale": [-26.0300, 27.9900],
    "rosebank": [-26.1450, 28.0400],
    "hyde park": [-26.1250, 28.0350],
    "sandhurst": [-26.1180, 28.0420],
    "craighall park": [-26.1300, 28.0250],
    "parkhurst": [-26.1380, 28.0180],
    "randburg": [-26.0950, 27.9950],
    "midrand": [-25.9980, 28.1260],
    "centurion": [-25.8600, 28.1890],
    "pretoria": [-25.7479, 28.2293],
    "vanderbijlpark": [-26.7115, 27.8380],
    "vanderbijlpark_se6": [-26.7150, 27.8450],
    "vanderbijlpark_se8": [-26.7200, 27.8500],
    "vanderbijlpark_sw5": [-26.7050, 27.8250],

    // KwaZulu-Natal - North Coast & Durban
    "ballito": [-29.5390, 31.2140],
    "ballito central": [-29.5390, 31.2140],
    "caledon estate": [-29.5250, 31.2050],
    "zimbali estate": [-29.5600, 31.1950],
    "zimbali": [-29.5600, 31.1950],
    "palm lakes estate": [-29.4700, 31.2400],
    "sheffield beach": [-29.4950, 31.2500],
    "lalela estate": [-29.4850, 31.2350],
    "umhlanga": [-29.7280, 31.0850],
    "umhlanga rocks": [-29.7280, 31.0850],
    "la lucia": [-29.7500, 31.0650],
    "durban north": [-29.7800, 31.0450],
    "durban": [-29.8587, 31.0218],

    // Western Cape - Cape Town & Garden Route
    "cape town": [-33.9249, 18.4241],
    "camps bay": [-33.9510, 18.3780],
    "sea point": [-33.9180, 18.3880],
    "constantia": [-34.0250, 18.4350],
    "knysna": [-34.0350, 23.0480],
    "knysna central": [-34.0350, 23.0480],
    "brenton on lake": [-34.0600, 23.0150],
    "eastford country estate": [-34.0200, 23.0350],
    "george": [-33.9630, 22.4617],
    "levalia": [-33.9700, 22.4850],

    // Eastern Cape
    "port elizabeth": [-33.9608, 25.6022],
    "port elizabeth central": [-33.9608, 25.6022],
    "gqeberha": [-33.9608, 25.6022],
    "summerstrand": [-33.9850, 25.6650],
    "humewood": [-33.9750, 25.6450]
};

export function getFallbackCoordinates(item) {
    const sub = (item.location?.suburb || item.geo_hierarchy?.suburb || "").toLowerCase().trim();
    const area = (item.location?.region || item.location?.city || item.geo_hierarchy?.area || "").toLowerCase().trim();

    const targetKey = SUBURB_CENTROIDS[sub] ? sub : (SUBURB_CENTROIDS[area] ? area : null);
    if (!targetKey) return null;

    const [baseLat, baseLng] = SUBURB_CENTROIDS[targetKey];
    
    // Deterministic slight pseudo-random jitter based on listing ID string hash
    const hash = (item.listing_id || "0").split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
    const jitterLat = ((hash % 100) - 50) * 0.00008;
    const jitterLng = (((hash * 7) % 100) - 50) * 0.00008;

    return [baseLat + jitterLat, baseLng + jitterLng];
}
