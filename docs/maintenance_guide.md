# Maintenance & Developer Guide

## 1. Where to Make Changes When the Website Changes

All extraction logic specific to Private Property South Africa is isolated in:
`property_archiver/extractors/private_property.py`

Generic crawling, hashing, storage, security, and CLI logic are decoupled from portal-specific parsing.

---

## 2. Common Maintenance Scenarios

### Scenario A: Private Property Changes JSON-LD Schema
If the site updates its schema from `@type: "Residence"` to `@type: "SingleFamilyResidence"`, `@type: "Place"`, or a custom format:
1. Open `property_archiver/extractors/private_property.py`.
2. Locate `_extract_json_ld()`.
3. Add the new `@type` identifier to the filter list:
   ```python
   if data_type in ("Residence", "SingleFamilyResidence", "RealEstateListing", "House", "Place", "NewType"):
       residence_block = data
   ```

### Scenario B: CSS Class Names Renamed
If the site changes markup classes (e.g. from `.property-details__list-item` to `.listing-spec__row`):
1. Update selector regexes in `_extract_details()` and `_extract_features()`.
2. Use flexible regexes (e.g. `re.compile(r"property-details|listing-spec|spec-item", re.I)`).

### Scenario C: Image CDN URLs Shift
If the image URL pattern changes from `images.pp.co.za/listing/{id}/{hash}/{w}/{h}/...`:
1. Inspect the new image URL format in a browser.
2. Update `PP_IMG_HASH_RE` in `property_archiver/extractors/private_property.py` and `property_archiver/images/downloader.py`.

---

## 3. Adding a New Property Portal Extractor

1. Create a new file `property_archiver/extractors/my_portal.py`.
2. Inherit from `BaseExtractor`:
   ```python
   from property_archiver.extractors.base import BaseExtractor
   from property_archiver.models.listing import ListingRecord

   class MyPortalExtractor(BaseExtractor):
       PORTAL_NAME = "myportal.co.za"

       def can_handle(self, url_or_html: str) -> bool:
           return "myportal.co.za" in url_or_html.lower()

       def extract(self, html: str, url: str) -> ListingRecord:
           # Implement extraction logic
           ...
   ```
3. Register the new extractor in `property_archiver/extractors/__init__.py`:
   ```python
   EXTRACTORS: list[BaseExtractor] = [
       PrivatePropertyExtractor(),
       MyPortalExtractor(),
   ]
   ```
