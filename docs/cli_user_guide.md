# CLI User Guide & Ergonomics

## 1. Archiving Made Simple

`property-archiver` is designed for friction-free ingestion. You can archive listings in multiple convenient ways:

### Option A: Short Listing ID (Recommended)
You don't need to copy 150-character URLs. Just pass the listing ID:
```bash
property-archiver fetch T4710876
```
*(The archiver automatically resolves `https://www.privateproperty.co.za/T4710876` and follows the canonical redirect).*

### Option B: System Clipboard (`-c` / `--clipboard`)
Copy any listing URL in your browser and run:
```bash
property-archiver fetch -c
```
*(Or simply run `property-archiver fetch` with no arguments, and it will automatically inspect your clipboard).*

### Option C: Multiple Targets & Wildcards
Archive multiple listings or local HTML snapshots in a single command:
```bash
# Multiple IDs / URLs
property-archiver fetch T4710876 T4710877 https://www.privateproperty.co.za/...

# Wildcard glob of local snapshots
property-archiver fetch ./snapshots/*.html
```

---

## 2. Inspecting, Validating & Diffing

### Inspect an Archive
```bash
property-archiver inspect ./archive/listings/T4710876
```

### Validate SHA-256 Checksums
```bash
property-archiver validate ./archive/listings/T4710876
```

### Compare Snapshots (Price Drops & Status Changes)
```bash
property-archiver compare ./archive/listings/T4710876_jul ./archive/listings/T4710876_aug
```
