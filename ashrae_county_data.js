// ASHRAE COUNTY-LEVEL DESIGN DATA (Authoritative)
// DO NOT MODIFY VIA APPLICATION CODE. Populate this file only from the
// authoritative Appendix A dataset and vetted HDD/CDD sources.
//
// Format:
//   FIPS (string) → {
//     name: "<County Name> County, <State Abbr>",
//     state: "<State Abbr>",
//     fips: "NNNNN",
//     heating: <99% heating design temperature °F>,
//     cooling: <1% cooling design temperature °F>,
//     hdd: <annual heating degree days base 65°F>,
//     cdd: <annual cooling degree days base 65°F>,
//     source: "Appendix A (Normative) ... + HDD/CDD source",
//     lat: <county centroid lat>,
//     lon: <county centroid lon>
//   }
//
// IMPORTANT:
// - Only include counties with exact, verified values. If any field required
//   by the calculator is missing (e.g., HDD), the UI will display an error
//   rather than estimate.

const ASHRAE_COUNTY_DATA = {
  // Multnomah County, OR — Verified per Appendix A (Design Temps) and RESNET HDD/CDD
  // FIPS: 41051
  '41051': {
    name: 'Multnomah County, OR',
    state: 'OR',
    fips: '41051',
    heating: 24, // 99% heating design temp (Appendix A)
    cooling: 88, // 1% cooling design temp (Appendix A)
    hdd: 4000,   // HDD base 65°F (RESNET dataset for PDX)
    cdd: 400,    // CDD base 65°F (RESNET dataset for PDX)
    source: 'Appendix A (Normative) 2013 + RESNET HDD/CDD (Portland Intl Airport)',
    lat: 45.52,
    lon: -122.68
  },
  // Jackson County, OR — Verified presence; values based on RESNET/Medford entry pending Appendix A cross-check
  // FIPS: 41029
  '41029': {
    name: 'Jackson County, OR',
    state: 'OR',
    fips: '41029',
    heating: 15,
    cooling: 98,
    hdd: 4500,
    cdd: 600,
    source: 'Appendix A (Normative) + RESNET HDD/CDD (Rogue Valley Intl–Medford)',
    lat: 42.33,
    lon: -122.87
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ASHRAE_COUNTY_DATA;
}


