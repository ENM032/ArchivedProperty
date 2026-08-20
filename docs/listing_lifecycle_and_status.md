# Listing Lifecycle & Status Handling

## 1. Why Portals Keep "Under Offer" and "Sold" Listings Online

Real estate portals (such as Private Property, Property24, Zillow, Rightmove) often keep property pages viewable even after a deal is in progress or completed. They do this for several strategic reasons:
1. **SEO & Search Indexing**: Keeping URLs alive retains inbound links and search engine rankings.
2. **Lead Generation**: Portals display "Under Offer" or "Sold" banners while presenting nearby active listings to keep home-seekers browsing.
3. **Market Comparables & Price History**: Historical sale prices and marketing timelines serve as valuation benchmarks.
4. **Deal Fall-Through Protection**: Properties marked "Under Offer" can return to "Active" if bond approval fails or suspensive conditions are unmet.

---

## 2. Status Detection & Normalization

`property-archiver` continuously tracks the lifecycle state of every listing through a multi-layer detector:

### Lifecycle States
- **`active`**: Property is currently on the market and available for purchase/rent.
- **`under_offer`**: An offer has been accepted; suspensive conditions (e.g. mortgage approval, property sale) are pending.
- **`sold`**: The transfer/transaction is finalized, or the agency marked the listing as sold.
- **`pending`**: Contract pending or awaiting verification.
- **`withdrawn`**: Property taken off the market.

### Visual Badges & Feature Flags
Alongside `listing_status`, the schema preserves discrete boolean flags and raw badges:
- `status_badges`: `["Under Offer", "Reduced", "On Show", "Auction"]`
- `is_under_offer`: `true | false`
- `is_sold`: `true | false`
- `is_on_show`: `true | false` (includes `on_show_details` with date & time if available)
- `is_price_reduced`: `true | false`

---

## 3. Extraction Hierarchy for Statuses

1. **Embedded Application State (`bundleParams`)**:
   - `bundleParams.isUnderOffer`
   - `bundleParams.isSold` / `bundleParams.listingStatus`
   - `bundleParams.isOnShow`
   - `bundleParams.badges` / `bundleParams.tags`
2. **DOM Visual Badges & Ribbons**:
   - Elements with classes matching `badge`, `banner`, `ribbon`, `tag`, `label`, `listing-banners`, `.listing-details__badge`.
   - String matching for `"Under Offer"`, `"Offer Pending"`, `"Under Contract"`, `"Sold"`, `"On Show"`, `"Price Reduced"`, `"Auction"`.
3. **OpenGraph & SEO Meta Tags**:
   - Status prefixes in `og:title` or `og:description` (e.g. `[Under Offer] 4 Bedroom House in Rivonia`).

---

## 4. Longitudinal Tracking & Change Detection

When archiving the same listing across time, `property-archiver compare <archive_v1> <archive_v2>` detects lifecycle transitions:

```bash
property-archiver compare ./archive/listings/T4710876_jul ./archive/listings/T4710876_aug
```

Output:
```
Listing Changes Detected:
  • Status Transition: active -> under_offer
  • New Badges: Under Offer
```
