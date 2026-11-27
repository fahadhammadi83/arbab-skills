# Boosters: optional tools that make the scan stronger

The skill works fully without any of these. When the user's Claude has one of these tools connected, use it at the step named below. When a tool is missing, skip that booster without asking the user to install anything mid-run, and mention once at the end what it would have added.

**How to tell if a booster is on:** look at your own tool list. Tool names vary by setup, so match on the ending:

| Booster | It's on if you have a tool ending in | What it adds | Who pays |
|---|---|---|---|
| **Google Maps (Apify)** | `call-actor` (plus `fetch-actor-details`, `get-dataset-items`) | Builds the business list when the user has none | The user's Apify account, per place |
| **Firecrawl** | `firecrawl_scrape` | Reads pages the way a browser shows them, including buttons loaded by script, so verification is more accurate | The user's Firecrawl credits |
| **Oriane** | `oriane_search_profiles` / `oriane_search_contents` | The business's Instagram activity: followers, how often they post, their best reel | The user's Oriane plan |

Start every run with one line: `Boosters: Google Maps on/off · Firecrawl on/off · Oriane on/off`.

**Money rule (all boosters):** a booster that costs money runs only after you've told the user the expected cost and they've said yes in chat. Never start a paid run on your own, even on a schedule. A scheduled night run uses the free scan only, unless the user wrote a spending cap into the task.

---

## 1 · Google Maps list (Apify), at Step 1 when there's no list

1. Ask for the **sector or sectors** (search terms like "barber shop", "freight forwarder", "dental clinic") and **one city or area**.
2. Call `fetch-actor-details` on `compass/crawler-google-places` with `pricing: true` to read the user's real price per place (it depends on their Apify tier).
3. **Quote before running:** places = terms × places per term. Cost = places × price per place, plus any filter add-on per place. Example: 10 terms × 50 places = 500 places. At USD 0.003 a place that's about USD 1.50, and the "with website" filter adds USD 0.001 a place, so about USD 2.00. Wait for the user's yes.
4. Run `call-actor` with `actor: "compass/crawler-google-places"`, `waitSecs: 0`, and `callOptions.maxTotalChargeUsd` set to the quoted amount. Input:
   ```json
   {
     "searchStringsArray": ["barber shop", "freight forwarder"],
     "locationQuery": "Dubai, United Arab Emirates",
     "maxCrawledPlacesPerSearch": 50,
     "language": "en",
     "skipClosedPlaces": true,
     "maxReviews": 0,
     "maxImages": 0,
     "scrapeReviewsPersonalData": false
   }
   ```
   - Add `"website": "withWebsite"` only if the user sells something for businesses that already have a site, such as SEO.
   - Keep listings **without** a website for web-build offers: "no website" is the strongest gap.
   - **Never switch on** the add-ons that return personal data: business leads enrichment, reviewers' data, image authors. Company-level data is enough, and privacy law protects the rest.
5. Poll the run with `get-actor-run` until it's finished. Fetch the items with `get-dataset-items`, save them as `prospect-scan/places-<date>.json`, then go to Step 2 with `--list prospect-scan/places-<date>.json`. The scanner reads Apify exports directly.
6. Tell the user the real cost from the run, not just your estimate.

## 2 · Firecrawl, at Step 3 (verifying the top picks)

Use `firecrawl_scrape` instead of a plain page fetch to open each pick's homepage:
```json
{ "url": "<homepage>", "formats": ["markdown", "links"], "onlyMainContent": false, "proxy": "basic" }
```
- **What to check:** in the links, look for `wa.me` or `api.whatsapp.com` (WhatsApp), `tel:` links, booking tools (Calendly, Fresha, Booksy, Zoho Bookings, "Book now"), an Arabic version (`/ar/`, a language switch), Instagram links and a contact form.
- **When the page has little content,** also check its `/contact` page. This often rescues a "No WhatsApp" signal that was wrong.
- **Cap:** 15 scrapes per run, about one credit each. Say how many credits you used.
- **Use the `basic` proxy only.** Never use stealth or enhanced proxies to get past a site that blocks robots. If a site shows a bot check, captcha or login, drop it. A blocked site stays blocked.

## 3 · Oriane, at Step 3 (Instagram angle for the top picks)

For each pick with an Instagram handle (the scan saves it in the `instagram` field, or it's the listing's only website):
1. `oriane_search_profiles` with `{"operator": "and", "filters": {"platform": {"includes": ["instagram"]}, "handle": {"exactMatch": {"values": ["<handle>"]}}}}` and `projection: "basic"`. This gives followers and post count.
2. `oriane_search_contents` with `profileHandle` set to the handle and `publishedAt.after` set to 30 days ago, `sort: "publishedAt"`, `limit: 20`. This gives posts in the last 30 days, the newest date, and the best views.
3. Turn what you find into **one extra line per business**, only when it sharpens the pitch:
   - "Posts 4 times a week to 12K followers, but the bio link goes to a site with no booking": busy audience, nowhere to convert.
   - "Last post was 3 months ago": the account has gone quiet (good for a content offer).
   - "Their best reel got 40K views; the site linked from the bio is down": attention with nowhere to land.
4. **Coverage is partial and numbers can lag.** Oriane indexes a slice of Instagram: many small businesses aren't in it, and follower counts can be out of date. Say "per Oriane" next to any number, and never build the whole pitch on it.
5. **Business accounts only.** If the handle is clearly a person's private account, skip it. Not indexed in Oriane? Write "Instagram: not found in Oriane" and never guess numbers.

---

## Output when boosters ran
At the top of `<date>_top5.md`, under the run's numbers, add:
```
Boosters: Google Maps on (500 places, USD 2.10) · Firecrawl on (9 credits) · Oriane off
```
Then, in each business block, add a line `Instagram: ...` when Oriane found something.
