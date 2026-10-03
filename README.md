# Charles Daly Conseil website

Static bilingual site (French first, English under `/en/`) in the Navy and Brass style.

## Structure
- `build.py`: all page content and settings (domain, email, phone, LinkedIn, legal details, prices).
- `static/`: stylesheet, self-hosted fonts, icons, social image, Cloudflare `_headers`.
- `site/`: generated output. This is what gets deployed. Do not edit by hand.

## Making a change
1. Edit `build.py` (or `static/assets/styles.css`).
2. Run `python3 build.py`. It fails if an em or en dash slips into a page.
3. Commit and push. Cloudflare Pages redeploys automatically.

## Cloudflare Pages settings
- Framework preset: None
- Build command: (leave empty)
- Build output directory: `site`
- Production branch: `main`

## Before going live
- Set `SITE_URL` and `EMAIL` in `build.py` to the real domain, then rebuild.
- Fill in `LEGAL` (legal form, capital, address, SIREN, VAT) for the mentions légales.
- Optionally set `PHONE` and `LINKEDIN`.
- Turn on Cloudflare Web Analytics (cookie-free) for the site.
- Submit `https://<domain>/sitemap.xml` in Google Search Console.
