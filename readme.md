# FN Home Group Website

A static website for **Faith Nance, REALTOR&reg;**, founder of **FN Home Group**, brokered by **Epique Realty**, serving Southern Middle Tennessee. Built with clean HTML, CSS, and vanilla JavaScript, ready to deploy on Netlify.

---

## 1. How This Project Is Organized

```
/                       <- The deployable website (this is what goes to Netlify)
  index.html            <- Home page
  meetfaith.html, buy.html, sell.html, homevalue.html, relocation.html, ...
  communities/          <- Generated community pages (one per community)
  resources/            <- Generated article pages (one per resource article)
  legal/                <- Privacy Policy, Terms of Use, Fair Housing, etc.
  assets/               <- styles.css, script.js, images, icons
  sitemap.xml, robots.txt, netlify.toml, 404.html, success.html

/build/                 <- SOURCE FILES used to generate the site above. Edit here, not in the root.
  templates/base.html   <- Page shell (<head>, meta tags, schema)
  templates/nav.html    <- Shared navigation (appears on every page)
  templates/footer.html <- Shared footer (appears on every page)
  templates/community-fragment.html   <- Template used for every community page
  templates/article-fragment.html     <- Template used for every resource article
  pages/                <- One fragment file per hand-authored page (Home, Buy, Sell, etc.)
  data/communities.json <- Content for each community page
  data/articles.json    <- Content for each resource article
  data/site-config.json <- Central reference for agent/brokerage/contact info
  scripts/generate.py   <- The generator script that builds everything in the root folder
```

**Why it's built this way:** editing 40+ HTML pages by hand every time the phone number or nav menu changes would be error-prone. Instead, shared pieces (navigation, footer, page shell, SEO tags) live in one place in `/build/templates/`, and community/article pages are generated from simple data files. Run the generator and it rebuilds the whole site consistently.

---

## 2. How to Preview the Site Locally

You need Python 3 installed (used only to run the generator and a simple local server; nothing server-side is required to host the site).

```bash
# From the project's root folder:
python3 build/scripts/generate.py   # rebuilds all HTML pages from /build

# Then start a simple local server:
python3 -m http.server 8080
```

Open `http://localhost:8080` in your browser. Because this is a fully static site with relative links throughout, you can also just double-click `index.html` and open it directly in a browser (no server needed) — every stylesheet, script, and image resolves correctly either way. Forms still require a real deploy (e.g. Netlify) to actually submit, since there's no backend running locally.

---

## 3. How to Upload the Site to Netlify

**Option A — Drag and drop (fastest for a first deploy):**
1. Log in to [Netlify](https://app.netlify.com).
2. From your dashboard, go to **Sites** and drag the entire project folder (the one containing `index.html`, `assets/`, etc. — not the `build/` source folder) onto the deploy area.
3. Netlify will publish the site instantly at a random `*.netlify.app` URL.

**Option B — Connect a Git repository (recommended for ongoing updates):**
1. Push this project to a GitHub, GitLab, or Bitbucket repository.
2. In Netlify, choose **Add new site > Import an existing project** and connect the repository.
3. Build settings:
   - **Build command:** leave blank (or `python3 build/scripts/generate.py` if you want Netlify to run the generator on every deploy — see note below)
   - **Publish directory:** `.` (the repository root)
4. Click **Deploy site**.

> Note: if you want Netlify to automatically rebuild generated pages (communities/articles) whenever you edit files in `/build/`, set the **Build command** to `python3 build/scripts/generate.py`. Netlify's build image includes Python 3. If you'd rather keep things simple, just run the generator locally and commit the generated HTML files before pushing.

---

## 4. How to Connect the Custom Domain (www.fnhomegroup.com)

This project does not currently have ownership of or DNS access to `www.fnhomegroup.com` — that domain must be connected by whoever controls it (Faith or her domain registrar account).

1. In Netlify, go to **Site settings > Domain management > Add a custom domain**.
2. Enter `www.fnhomegroup.com` and follow the prompts.
3. Netlify will ask you to either:
   - Point your domain's nameservers to Netlify DNS (simplest, Netlify manages everything), **or**
   - Add specific DNS records at your current registrar (a `CNAME` record for `www` pointing to your Netlify site's `.netlify.app` address, and an `A`/`ALIAS` record for the root/apex domain `fnhomegroup.com` pointing to Netlify's load balancer IP, currently `75.2.60.5` — always confirm the current value in your Netlify dashboard, as it can change).
4. It's recommended to set `www.fnhomegroup.com` as the primary domain and redirect the bare `fnhomegroup.com` to it (Netlify has a one-click option for this under Domain management).

---

## 5. How to Configure DNS

Exact steps depend on where the domain is registered (e.g., GoDaddy, Namecheap, Google Domains, etc.):

1. Log in to the domain registrar's dashboard.
2. Find the DNS settings for `fnhomegroup.com`.
3. Add/update the records Netlify provides in Site settings > Domain management (typically a `CNAME` for `www` and an `A`/`ALIAS` record for the apex domain).
4. DNS changes can take anywhere from a few minutes to 24-48 hours to fully propagate.

---

## 6. How to Enable HTTPS

Once the domain is connected and DNS is pointing to Netlify:

1. Go to **Site settings > Domain management > HTTPS**.
2. Netlify automatically provisions a free SSL certificate (via Let's Encrypt) once DNS is verified.
3. Once issued, Netlify will serve the site over HTTPS and can automatically redirect HTTP traffic to HTTPS (toggle this on in the same settings panel).

---

## 7. How to Review Netlify Form Submissions

All forms on this site (Contact, Buyer Consultation, Seller Consultation, Home Value Request, Relocation Request, Buyer Guide Request, and each Community contact form) use **Netlify Forms** (`data-netlify="true"`).

1. Once deployed, go to your site in the Netlify dashboard.
2. Click the **Forms** tab. Netlify automatically detects each form by name (e.g., "contact," "buyer-consultation," "home-value-request," etc.) the first time it's deployed.
3. Submissions appear here in real time. You can export them, set up **email notifications** (Site settings > Forms > Form notifications > Add notification > Email), or connect a **Zapier/webhook** integration to send them elsewhere.
4. All forms include a hidden honeypot field (`bot-field`) for basic spam protection. For stronger protection, Netlify also offers built-in **Akismet spam filtering** and **reCAPTCHA 2** integration, which can be enabled per form in the Forms settings.

---

## 8. How to Replace Images and Logos

All images live in `/assets/images/`:

- `fnhomegrouplogo.png` — FN Home Group logo (used in nav and footer)
- `faithnanceheadshot.jpg` — Faith's headshot (Home + Meet Faith pages)
- `epiquerealtylogoblack.png` / `epique-logo.png` — Epique Realty brokerage logos
- Dashed placeholder boxes throughout the site mark where additional photos (listings, communities, lifestyle images) should go — replace the `<div class="placeholder-box">...</div>` with an `<img>` tag once real photos are available.

To replace an image:
1. Add the new image file to `/assets/images/` (keep file sizes reasonable — a few hundred KB max for web performance).
2. If you're editing a hand-authored page, update the `<img src="...">` in the matching file under `/build/pages/` (not the root — the root is regenerated).
3. If you're editing something used site-wide (like the logo in the nav/footer), update `/build/templates/nav.html` and `/build/templates/footer.html`.
4. Re-run `python3 build/scripts/generate.py` and redeploy.

Favicons were auto-generated from the FN Home Group logo and live in `/assets/icons/`. Replace them there (keeping the same filenames) if a dedicated favicon design is created later.

---

## 9. How to Update Contact Information

Contact details (phone, email, brokerage address) currently appear in:
- `/build/templates/footer.html` (site-wide footer)
- `/build/pages/contact.html`
- `/build/pages/epiquerealty.html`
- `/build/data/site-config.json` (reference/documentation copy — update this too so it stays accurate)

Update the text in those files, then run `python3 build/scripts/generate.py` and redeploy.

---

## 10. How to Add a New Community Page

1. Open `/build/data/communities.json`.
2. Copy an existing entry (e.g., the "springhill" block) and add a new one with a unique `slug` (used in the URL, e.g. `springhill` becomes `/communities/springhill.html`).
3. Fill in `name`, `meta_description`, `intro_line`, `overview`, `commute`, `housing`, `amenities`, and `links` (these can contain simple HTML like `<p>` and `<ul><li>` tags).
4. Add a card linking to the new page in `/build/pages/communities.html` (the directory page) so visitors can find it.
5. Run `python3 build/scripts/generate.py` — this creates `/communities/<slug>.html` automatically, with full SEO metadata and the shared nav/footer.
6. Redeploy.

---

## 11. How to Add a New Educational Article

1. Open `/build/data/articles.json`.
2. Copy an existing entry and add a new one with a unique `slug`.
3. Fill in `title`, `category`, `meta_description`, `summary`, and `body` (HTML allowed — use `<h2>` for subheadings and `<p>` for paragraphs).
4. Add a card linking to the new article in `/build/pages/resources.html` (the Resource Hub).
5. Run `python3 build/scripts/generate.py` — this creates `/resources/<slug>.html` automatically.
6. Redeploy.

**Important:** double-check that any double quotes inside article text are written as `&quot;` (not a plain `"` character), since the content lives inside a JSON file and unescaped quotes will break the build. Apostrophes (`'`) are fine as-is.

---

## 12. How to Connect a Future CRM or Email System

This site currently sends form submissions to the Netlify Forms dashboard only. To route leads into a CRM (e.g., Follow Up Boss, kvCORE, HubSpot) or email service:

- **Zapier / Make.com (easiest, no code):** Use Netlify's built-in Zapier integration (Site settings > Forms > Zapier) or set up a webhook (Site settings > Forms > Form notifications > Add notification > Outgoing webhook) that fires on every new submission, and connect that to your CRM's Zapier/Make trigger.
- **Direct webhook:** Most modern CRMs accept a webhook URL; Netlify can POST form submissions there directly via the same "Outgoing webhook" notification setting.
- **Email autoresponders:** Add an "Email notification" in the same Forms settings panel so Faith gets an email the moment someone submits a form, in addition to (or instead of) checking the dashboard.

No API keys or CRM credentials are stored in this codebase — all integrations should be configured through Netlify's dashboard, never hard-coded into the HTML/JS.

---

## 13. How to Edit SEO Metadata

Every hand-authored page has a small metadata block at the top of its source file in `/build/pages/` (and generated pages pull metadata from `/build/data/communities.json` / `articles.json`), formatted like this:

```
title: Page Title Here
description: A one- or two-sentence meta description.
canonical: /page-path.html
bodyclass: page-example
schema: none
---
<section>...actual page content...</section>
```

To change a page's title or meta description, edit the `title:` / `description:` lines at the top of that file, then run `python3 build/scripts/generate.py` and redeploy. The `schema:` field controls which structured data (JSON-LD) is injected — `person` for Faith's agent schema, `localbusiness` for the brokerage/business schema, or `none`.

---

## 14. How to Change a Scheduling Button's Calendly Event

Every scheduling button on the site links through a token instead of a
hard-coded Calendly address, and all of those tokens are defined in one place:
the `"scheduling_links"` block in `/build/data/site-config.json`.

Currently defined:

| Token | Calendly event |
| --- | --- |
| `{{SCHEDULE_GENERAL}}` | `/fnhomegroup/consultation` |
| `{{SCHEDULE_BUYER}}` | `/fnhomegroup/buyer-consultation` |
| `{{SCHEDULE_LISTING}}` | `/fnhomegroup/listing-consultation` |
| `{{SCHEDULE_AGENT_COLLABORATION}}` | `/fnhomegroup/agent-collaboration` |
| `{{SCHEDULE_ASK_A_REALTOR}}` | `/fnhomegroup/ask-a-realtor` |
| `{{SCHEDULE_PHONE_CALL}}` | `/fnhomegroup/phone-call` |
| `{{SCHEDULE_IN_HOME_MEETING}}` | `/fnhomegroup/in-home-meeting` |
| `{{SCHEDULE_REAL_ESTATE_GUIDANCE}}` | `/fnhomegroup/real-estate-guidance` |

To point an existing button at a different event, change that token's value in
`site-config.json` and run `python3 build/scripts/generate.py`. Every page that
uses the token is rewritten, so nothing can drift out of sync.

To add a scheduling button to a page, use the token in the `href` of a link in
`/build/pages/` or `/build/templates/`, keeping `target="_blank"` and
`rel="noopener noreferrer"` as the existing buttons do:

```html
<a class="btn btn-primary" href="{{SCHEDULE_PHONE_CALL}}" target="_blank" rel="noopener noreferrer">Label</a>
```

Two safety checks are built into the generator, and both stop the build rather
than publishing something wrong:

- an `href` using a `{{SCHEDULE_*}}` token that is not defined in
  `site-config.json` (a typo, for example) is rejected;
- any `calendly.com` address in a page that is not one of the public events
  listed above is rejected. This is what keeps Faith's private, client-only
  booking events (client check ins, contract timeline reviews, offer reviews)
  off the public site. Those private links are deliberately not stored anywhere
  in this project, because the whole project folder is what gets published.

Analytics needs no changes when a button is added or repointed: a single click
handler in `/assets/analytics.js` recognises any Calendly link and records one
`consultation_click` per click, only after a visitor has accepted analytics in
the privacy notice.

---

## 15. How to Redeploy After Making Changes

**If using drag-and-drop deploys:** run `python3 build/scripts/generate.py`, then drag the updated project root folder onto Netlify's deploy area again.

**If connected to Git:**
```bash
python3 build/scripts/generate.py
git add .
git commit -m "Update site content"
git push
```
Netlify will automatically rebuild and redeploy when it detects the new commit.

---

## Remaining Placeholders Faith Should Provide

- Final approved **Epique Realty license number** and any specific brokerage disclosures required by Tennessee real estate law
- **Social media URLs** (Facebook, Instagram, LinkedIn) — currently placeholder `#` links in the footer and Contact page
- **Client testimonials** — real, permissioned quotes (with names/initials as approved) to replace the placeholder cards on `/testimonials.html`
- **Preferred vendors** — approved lenders, inspectors, contractors, etc. for `/vendors.html`
- **Downloadable PDF guides and checklists** — the Buyer Guide, and all checklists referenced on the Client Resource Center (`/clientcenter.html`), currently exist as labeled placeholders
- **MLS/IDX home search integration** — a licensed IDX provider is needed to power live listing search (not included, since it requires an active data feed agreement)
- Additional **listing, community, and lifestyle photography** to replace the dashed placeholder image boxes throughout the site
- A final **attorney review** of the Privacy Policy, Terms of Use, and other legal pages before the site goes live
- Confirmation of the **final domain DNS access** for connecting www.fnhomegroup.com

---

## A Note on Compliance

This site was built with fair housing compliance, REALTOR&reg; trademark usage, and standard real estate disclosures in mind, but it has not been reviewed by an attorney. Please have Faith's legal counsel and/or Epique Realty's compliance team review the site — especially the Legal pages in `/legal/` — before publishing it live.
