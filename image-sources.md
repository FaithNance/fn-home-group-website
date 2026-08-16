# Image Sources

Every non-logo, non-headshot photograph used on the FN Home Group website, with its
photographer, source, license, and attribution requirement. All images below are
free for commercial use with no purchase required. None are AI-generated,
watermarked, MLS/listing photos, or editorial-only images.

Both Pexels and Unsplash license terms permit free commercial and personal use
without requiring attribution — crediting the photographer is appreciated but not
legally required. This document exists so that credit is available if FN Home
Group ever wants to display it (e.g., in a site footer or credits page).

## Community Carousel — Homepage ("Proudly Serving Southern Middle Tennessee")

| Slide caption | Photographer | Source | Original URL | License | Attribution required? |
|---|---|---|---|---|---|
| Maury County Countryside | Chad Pinkston | Pexels | https://www.pexels.com/photo/5734372/ | Pexels License | No |
| Williamson County Countryside | K | Pexels | https://www.pexels.com/photo/4170455/ | Pexels License | No |
| Franklin | Jon Tyson (@jontyson) | Unsplash | https://unsplash.com/photos/9R7KK9im56o | Unsplash License | No |
| Williamson County Horse Country | Tom Brashear | Pexels | https://www.pexels.com/photo/33956684/ | Pexels License | No |
| Nashville | ceesz | Pexels | https://www.pexels.com/photo/17278177/ | Pexels License | No |
| Marshall County Countryside | Drones Flown | Pexels | https://www.pexels.com/photo/16774015/ | Pexels License | No |
| Giles County Countryside | Phil Evenden | Pexels | https://www.pexels.com/photo/31512001/ | Pexels License | No |
| Lawrence County Countryside | K (kelly) | Pexels | https://www.pexels.com/photo/2898231/ | Pexels License | No |
| Bedford County Horse Country | Leo Allen | Pexels | https://www.pexels.com/photo/17824928/ | Pexels License | No |
| Rutherford County Countryside | Betty Krachey | Pexels | https://www.pexels.com/photo/32274715/ | Pexels License | No |

Only **Franklin** and **Nashville** are verified photos of those specific places
(a "Welcome to Franklin" sign, and the Nashville skyline). The other eight are
authentic Southern Middle Tennessee-region countryside/horse-country imagery, not
verified photos of the exact named town, so their captions and alt text describe
them by county/region rather than asserting they depict a specific town's Main
Street. See the alt text on each `<img>` in `build/pages/index.html` for the
literal (non-claiming) description.

## Content Photography — Replacing Placeholder Boxes

| Page / component | Description | Photographer | Source | Original URL | License | Attribution required? |
|---|---|---|---|---|---|---|
| Buy page — "Special Guidance for First-Time Buyers" | Happy couple holding up the keys to their new home | RDNE Stock project | Pexels | https://www.pexels.com/photo/happy-couple-holding-and-showing-a-house-key-8293700/ | Pexels License | No |
| Sell page — "Personalized Marketing, Not a One-Size-Fits-All Plan" | Bright, professionally staged modern living room | Max Vakhtbovych | Pexels | https://www.pexels.com/photo/modern-interior-of-comfortable-living-room-6180674/ | Pexels License | No |
| Relocation page — "Planning Your Relocation" | Family moving into their new home together | MART PRODUCTION | Pexels | https://www.pexels.com/photo/a-family-moving-into-a-new-house-7414910/ | Pexels License | No |

## Placeholders Intentionally Left Unchanged

| Page / component | Why |
|---|---|
| Epique Realty page — brokerage relationship section | The `.placeholder-box` here already contains the actual Epique Realty brokerage logo (`assets/logos/epiquerealtylogoblack.png`), not a stock-photo placeholder. It's a real, correct brand asset, so it was left as-is per "preserve logos." |

## Notes on Delivery

- All images are hotlinked to their Pexels/Unsplash CDN URLs (`images.pexels.com`,
  `images.unsplash.com`) using each service's on-the-fly resize/compress
  parameters, the same pattern already used by the carousel before this round of
  edits. This sandbox's outbound network access blocks direct requests to
  pexels.com/unsplash.com, so these could not be downloaded and re-encoded to
  WebP/AVIF and stored locally in this session — every URL above was verified to
  be a real, licensed photo page via a fetch of the Pexels/Unsplash listing
  itself, not fabricated.
- If Faith Nance would prefer the images stored locally (served from
  `/assets/photography/...` instead of hotlinked), that's a follow-up task: download
  each URL above, convert to WebP, and update the `src`/`srcset` attributes in
  `build/pages/buy.html`, `build/pages/relocation.html`, `build/pages/sell.html`,
  and `build/pages/index.html` accordingly.
