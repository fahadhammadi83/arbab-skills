# How to do each check

Score by the `_rubric` in `checks.json`. Write the evidence as one plain sentence with the number you saw, for example: "4.7 stars from 212 Google reviews, profile verified."

## Optional boosters
| Booster | On if you have a tool ending in | Use it for |
|---|---|---|
| Firecrawl | `firecrawl_scrape`, `firecrawl_search` | Reading pages as a browser shows them (script-loaded buttons), and Google-style searches |
| Oriane | `oriane_search_contents` | Counting Instagram posting days exactly (cadence) |
| Apify | `call-actor` | One Google Maps lookup for the profile's rating and review count (about USD 0.005; quote it and wait for a yes) |

Without boosters, use web search and page fetches. A check you can't do stays "not tested".

## 1 · Google Business Profile (gbp)
- **How:** search "<business name> <city>" and read the profile panel: rating, review count, verified badge.
- **With Apify:** run `compass/crawler-google-places` with `searchStringsArray: ["<business name>"]`, `locationQuery: "<city, country>"`, `maxCrawledPlacesPerSearch: 1`, `maxReviews: 0`, `scrapeReviewsPersonalData: false`. Read `totalScore` and `reviewsCount`. Confirm it's the right business by matching the website or address.
- **Not found** after a real search scores 0, with the evidence "No Google Business Profile found for <search>". **Couldn't search at all** is not tested.

## 2 · Phone speed (speed)
Filled by the tool when Lighthouse ran. If it didn't, leave it as not tested. Never estimate speed by eye.

## 3 · Search visibility in the customers' language (local_search)
- **Language:** in the Gulf, the customers' language is usually Arabic. Elsewhere, use the main local language.
- **Searches:** write three searches a real buyer would type in that language, for the business's trade and city. For example, for a Dubai salon: <bdi dir="rtl">«صالون نسائي دبي»</bdi>, <bdi dir="rtl">«أفضل صالون في دبي»</bdi>, <bdi dir="rtl">«حجز صالون دبي»</bdi>.
- **How:** run each search (web search, or `firecrawl_search` with the location set to the country) and note the business's best position in the top 20.
- **Evidence:** name the three searches and the best position.
- **Results look personalised or blocked?** Mark it not tested.

## 4 · WhatsApp path (whatsapp)
Always "not tested". The tool scores 5 when a WhatsApp link is on the site, 0 when there's none. **Never send a test message.**

## 5 · Proof on the site (proof)
- **How:** look at the first screen and the main pages. Are there named real clients, real numbers (projects, years, results), testimonials, or review widgets?
- **Score:** named clients with numbers = 10 · numbers without names = 5 · testimonials without numbers = 4 · nothing = 2.
- **Then** set `not_tested` to false and write what you saw.

## 6 · Instagram activity (cadence)
- **How:** the tool lists the Instagram handle(s) linked from the site in `auto.site.instagram`. No link? Search "<business name> instagram" and confirm it's theirs.
- **With Oriane:** call `oriane_search_contents` with `profileHandle` set to the handle, `publishedAt.after` set to 30 days ago, `limit: 100`, and `projection: "basic"`. Count the **distinct days** with a post. Oriane's coverage is partial: not found there doesn't mean no account.
- **Without Oriane:** if you can see the public grid and its dates, count the posting days. If you can't, mark it not tested.
- **Score:** 20+ days = 10 · 12-19 = 7 · 4-11 = 4 · 1-3 = 1 · no account = 0.

## 7 · Lead capture (lead_capture)
The tool pre-scores this from the homepage. Confirm it by eye:
- Is there a contact form? A WhatsApp button, and does it open with a message typed in? A booking tool?
- With Firecrawl, read the links on the homepage and `/contact`.
- Correct the score if the tool missed something, and say what you found.

## The three fixes
- **Impact first:** the fix that brings in customers fastest. Usually the lowest-scoring check that is quickest to fix.
- **Write for an owner,** not a developer. "Add a WhatsApp button that opens with 'Hi, I'd like to book'", not "implement a click-to-chat CTA".
- **Effort is honest:** an hour, a day, a week.
