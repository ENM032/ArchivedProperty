# Geographic Hierarchy & Sorting Guide

## 1. South African Real Estate Hierarchy

`property-archiver` models listings according to the geographic hierarchy of South African property portals:

```
Province (e.g. Gauteng, Western Cape, KwaZulu-Natal)
  └── Area / City / Metro (e.g. Sandton, Midrand, Cape Town, Durban North)
      └── Suburb (e.g. Rivonia, Kyalami Hills, Camps Bay)
          └── Listing ID (e.g. T4710876)
```

---

## 2. CLI Geographic Tree (`property-archiver tree`)

View your entire archived portfolio structured as an interactive tree in the terminal:

```bash
# View complete portfolio hierarchy tree
property-archiver tree

# Filter by province
property-archiver tree --province=Gauteng

# Filter by area / city
property-archiver tree --area=Sandton

# Filter by suburb and status
property-archiver tree --suburb=Rivonia --status=active
```

### Sample Output:
```
🇿🇦 South Africa (1 listings | R 4 999 000 total | Avg R 4 999 000)
└── 📍 Gauteng (1 listings | Avg R 4 999 000)
    └── 🏙️ Sandton (1 listings)
        └── 🏡 Rivonia (1 listings)
            └── 🏷️ [T4710876] R 4 999 000 - 4 Bedroom House in Rivonia (4.0b/3.5ba | 1983m²) [ACTIVE] (56 imgs)
```
