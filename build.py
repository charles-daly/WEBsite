#!/usr/bin/env python3
"""Static site generator for the Charles Daly Conseil website.

Edit content in this file, then run:  python3 build.py
Output goes to ./site, which Cloudflare Pages serves as-is (no build command needed).
"""
import json, re, shutil
from pathlib import Path
from datetime import date

# ---------------------------------------------------------------------------
# Site settings: change these in one place
# ---------------------------------------------------------------------------
SITE_URL = "https://www.charlesdaly.fr"      # final domain, no trailing slash
NAME = "Charles Daly"
BRAND = "Charles Daly Conseil"
EMAIL = "contact@charlesdaly.fr"
PHONE = ""                                     # e.g. "+33 6 00 00 00 00"; hidden while empty
LINKEDIN = ""                                  # full profile URL; hidden while empty
CITY = "Chartres"
REGION = "Centre-Val de Loire"
DAY_RATE = 700
UPDATED = date.today().isoformat()

# Mentions légales: fill in once the company is registered
LEGAL = {
    "form": "[forme juridique et capital à compléter]",
    "address": "[adresse du siège à compléter]",
    "siren": "[SIREN / RCS à compléter]",
    "vat": "[numéro de TVA intracommunautaire à compléter]",
}

ROOT = Path(__file__).parent
OUT = ROOT / "site"

# ---------------------------------------------------------------------------
# French typography: non-breaking spaces before : ; ! ? and in amounts
# ---------------------------------------------------------------------------
NBSP, NNBSP = " ", " "

def fr_text(s):
    s = re.sub(r" ([:])", NBSP + r"\1", s)
    s = re.sub(r" ([;!?])", NNBSP + r"\1", s)
    s = re.sub(r"« ", "«" + NBSP, s)
    s = re.sub(r" »", NBSP + "»", s)
    s = re.sub(r"(\d) (\d{3})", r"\1" + NNBSP + r"\2", s)
    s = re.sub(r"(\d) €", r"\1" + NBSP + "€", s)
    s = re.sub(r"(\d) (jours?|%)", r"\1" + NBSP + r"\2", s)
    return s

def fr_html(html):
    return re.sub(r">([^<]+)<", lambda m: ">" + fr_text(m.group(1)) + "<", html)

def eur(n, lang):
    return f"{n:,}".replace(",", " ") + " €" if lang == "fr" else f"€{n:,}"

# ---------------------------------------------------------------------------
# Page map: key -> paths per language
# ---------------------------------------------------------------------------
PATHS = {
    "home":      {"fr": "/", "en": "/en/"},
    "einv":      {"fr": "/facturation-electronique/", "en": "/en/e-invoicing/"},
    "stat":      {"fr": "/conformite-statutaire/", "en": "/en/statutory-compliance/"},
    "ap":        {"fr": "/automatisation-comptabilite-fournisseurs/", "en": "/en/accounts-payable-automation/"},
    "entity":    {"fr": "/nouvelle-entite-juridique/", "en": "/en/new-legal-entity/"},
    "offers":    {"fr": "/offres-et-tarifs/", "en": "/en/services-and-rates/"},
    "legal":     {"fr": "/mentions-legales/", "en": "/en/legal-notice/"},
    "privacy":   {"fr": "/confidentialite/", "en": "/en/privacy/"},
}

T = {  # shared interface strings
    "fr": {
        "nav": [("Expertises", "/#expertises"), ("Offres et tarifs", PATHS["offers"]["fr"]), ("Méthode", "/#methode"), ("Contact", "/#contact")],
        "other": "EN", "other_label": "English version",
        "tagline": "Consultant indépendant Dynamics 365 Finance & Operations",
        "foot_exp": "Expertises", "foot_info": "Informations", "foot_contact": "Contact",
        "legal": "Mentions légales", "privacy": "Confidentialité", "offers": "Offres et tarifs",
        "rights": f"© {date.today().year} {BRAND}",
        "home": "Accueil", "cta": "Parler de votre projet", "see_offers": "Voir les offres et tarifs",
        "skip": "Aller au contenu",
    },
    "en": {
        "nav": [("Expertise", "/en/#expertise"), ("Services and rates", PATHS["offers"]["en"]), ("Approach", "/en/#approach"), ("Contact", "/en/#contact")],
        "other": "FR", "other_label": "Version française",
        "tagline": "Independent Dynamics 365 Finance & Operations consultant",
        "foot_exp": "Expertise", "foot_info": "Information", "foot_contact": "Contact",
        "legal": "Legal notice", "privacy": "Privacy", "offers": "Services and rates",
        "rights": f"© {date.today().year} {BRAND}",
        "home": "Home", "cta": "Discuss your project", "see_offers": "See services and rates",
        "skip": "Skip to content",
    },
}

SERVICE_TITLES = {
    "einv":   {"fr": "Facturation électronique", "en": "Electronic invoicing"},
    "stat":   {"fr": "Conformité statutaire", "en": "Statutory compliance"},
    "ap":     {"fr": "Automatisation fournisseurs", "en": "Accounts payable automation"},
    "entity": {"fr": "Nouvelle entité juridique", "en": "New legal entity"},
}

# ---------------------------------------------------------------------------
# Offers data (both languages)
# ---------------------------------------------------------------------------
RETAINERS = [
    {"fr": "Essentiel", "en": "Essential", "days": 2, "fee": 1300, "rate": 650,
     "resp": {"fr": "Jour ouvré suivant", "en": "Next business day"}},
    {"fr": "Standard", "en": "Standard", "days": 4, "fee": 2500, "rate": 625, "key": True,
     "resp": {"fr": "Sous 4 heures ouvrées", "en": "Within 4 business hours"}},
    {"fr": "Étendu", "en": "Extended", "days": 6, "fee": 3600, "rate": 600,
     "resp": {"fr": "Le jour même, priorité en clôture", "en": "Same business day, priority at period-end"}},
]

PACKAGES = {
    "einv": {"days": 5, "price": 4000, "from": False,
             "fr": ("Diagnostic facturation électronique", "France, Belgique ou Allemagne. Analyse des écarts par rapport à l'obligation, revue des formats ER et des flux avec la plateforme, plan de remédiation priorisé."),
             "en": ("E-invoicing health check", "France, Belgium or Germany. Gap assessment against the mandate, review of ER formats and platform flows, prioritised remediation plan.")},
    "entity": {"days": 12, "price": 9500, "from": True,
             "fr": ("Nouvelle entité juridique", "Comptabilité, taxes, souches de numérotation, interco et à-nouveaux paramétrés, testés et mis en production. Adapté aux acquisitions."),
             "en": ("New legal entity", "Ledger, tax, number sequences, intercompany and opening balances configured, tested and taken live. Suited to acquisitions.")},
    "er": {"days": 4, "price": 3500, "from": True,
             "fr": ("Format Electronic Reporting", "Un format ER créé ou modifié, testé de bout en bout et documenté pour votre équipe support."),
             "en": ("Electronic Reporting format", "One ER format built or changed, tested end to end and documented for your support team.")},
    "close": {"days": 3, "price": 2400, "from": False,
             "fr": ("Accompagnement clôture annuelle", "Check-list de clôture, revue préalable du paramétrage comptable et accompagnement pendant le traitement de clôture."),
             "en": ("Year-end close support", "Close checklist, pre-close review of ledger settings and support through the closing run.")},
}

def price_txt(p, lang):
    base = eur(p["price"], lang)
    if p["from"]:
        return ("à partir de " if lang == "fr" else "from ") + base
    return base

def retainer_table(lang):
    h = {"fr": ("Formule", "Jours par mois", "Forfait mensuel", "Taux effectif", "Délai de réponse", "Recommandé"),
         "en": ("Tier", "Days per month", "Monthly fee", "Effective day rate", "Response time", "Recommended")}[lang]
    rows = ""
    for r in RETAINERS:
        tag = f' <span class="tag">{h[5]}</span>' if r.get("key") else ""
        cls = ' class="key"' if r.get("key") else ""
        rows += (f'<tr{cls}><td>{r[lang]}{tag}</td><td class="r">{r["days"]}</td>'
                 f'<td class="r">{eur(r["fee"], lang)}</td><td class="r">{eur(r["rate"], lang)}</td><td>{r["resp"][lang]}</td></tr>')
    return (f'<div class="tbl"><table><thead><tr><th>{h[0]}</th><th class="r">{h[1]}</th><th class="r">{h[2]}</th>'
            f'<th class="r">{h[3]}</th><th>{h[4]}</th></tr></thead><tbody>{rows}</tbody></table></div>')

def package_table(lang):
    h = {"fr": ("Forfait", "Ce que vous recevez", "Charge", "Prix", "jours"),
         "en": ("Package", "What you receive", "Effort", "Price", "days")}[lang]
    rows = ""
    for k in ("einv", "entity", "er", "close"):
        p = PACKAGES[k]
        name, desc = p[lang]
        rows += (f'<tr><td><b>{name}</b></td><td>{desc}</td><td class="r">{p["days"]} {h[4]}</td>'
                 f'<td class="r">{price_txt(p, lang)}</td></tr>')
    return (f'<div class="tbl"><table><thead><tr><th style="width:200px">{h[0]}</th><th>{h[1]}</th>'
            f'<th class="r">{h[2]}</th><th class="r">{h[3]}</th></tr></thead><tbody>{rows}</tbody></table></div>')

# ---------------------------------------------------------------------------
# Shared blocks
# ---------------------------------------------------------------------------
def head_block(eyebrow, h2, id_=None):
    return f'<div class="head"><div class="eyebrow">{eyebrow}</div><h2>{h2}</h2></div><div class="title-rule"></div>'

def figures(lang):
    if lang == "fr":
        items = [("26", "Entités juridiques passées en facturation électronique le 1er septembre 2026"),
                 ("3", "Pays dans le périmètre facturation électronique : France, Belgique et Allemagne"),
                 ("Comptable", "De formation, donc chaque besoin part du grand livre, pas de l'écran")]
    else:
        items = [("26", "Legal entities taken live on French e-invoicing on 1 September 2026"),
                 ("3", "Countries in e-invoicing scope: France, Belgium and Germany"),
                 ("Accountant", "By background, so requirements start from the ledger, not the screen")]
    inner = "".join(f'<div class="fig"><b>{a}</b><span>{b}</span></div>' for a, b in items)
    return f'<div class="figures"><div class="wrap">{inner}</div></div>'

def steps(lang):
    if lang == "fr":
        s = [("Appel de cadrage", "Trente minutes sur vos entités, vos échéances et votre paramétrage actuel. Sans frais."),
             ("Proposition écrite", "Livrables, critères de recette, prix et jalons sur deux pages, sous trois jours ouvrés."),
             ("Réalisation", "Paramétrage et tests dans votre environnement, avec un point d'avancement hebdomadaire. Toute évolution est chiffrée avant de démarrer."),
             ("Transfert", "Une documentation exploitable par votre équipe support, et un forfait de support en option pour la suite.")]
    else:
        s = [("Scoping call", "Thirty minutes on your entities, deadlines and current configuration. No charge."),
             ("Written proposal", "Deliverables, acceptance criteria, price and milestones on two pages, within three business days."),
             ("Delivery", "Configuration and testing in your environment, with a weekly status note. Changes are quoted before they start."),
             ("Handover", "Documentation your support team can run with, and an optional retainer for what comes next.")]
    return '<ol class="steps">' + "".join(f"<li><h3>{a}</h3><p>{b}</p></li>" for a, b in s) + "</ol>"

def terms(lang):
    if lang == "fr":
        t = ["Forfaits facturés 30 % au démarrage, 40 % à mi-parcours et 30 % à la recette.",
             f"Demandes d'évolution chiffrées à {eur(DAY_RATE, lang)} par jour avant tout démarrage.",
             "Développements (X++, intégrations) chiffrés à part avec un développeur partenaire.",
             "Responsabilité plafonnée au montant des honoraires perçus pour la mission.",
             f"Déplacements hors {REGION} et Île-de-France facturés au réel.",
             "Tous les prix en euros, hors TVA."]
    else:
        t = ["Fixed price invoiced 30% at start, 40% at mid-point and 30% on acceptance.",
             f"Change requests quoted at {eur(DAY_RATE, lang)} per day before work starts.",
             "Code changes (X++, integrations) quoted separately with a partner developer.",
             "Liability capped at the fees paid under the engagement.",
             f"Travel outside {REGION} and Île-de-France billed at cost.",
             "All prices in euros, excluding VAT."]
    return '<ul class="terms">' + "".join(f"<li>{x}</li>" for x in t) + "</ul>"

def contact_block(lang):
    rows = f'<div><dt>{"E-mail" if lang=="fr" else "Email"}</dt><dd><a href="mailto:{EMAIL}">{EMAIL}</a></dd></div>'
    if PHONE:
        rows += f'<div><dt>{"Téléphone" if lang=="fr" else "Phone"}</dt><dd><a href="tel:{PHONE.replace(" ","")}">{PHONE}</a></dd></div>'
    if LINKEDIN:
        rows += f'<div><dt>LinkedIn</dt><dd><a href="{LINKEDIN}" rel="me">{"Profil LinkedIn" if lang=="fr" else "LinkedIn profile"}</a></dd></div>'
    rows += f'<div><dt>{"Basé à" if lang=="fr" else "Based in"}</dt><dd>{CITY}, France</dd></div>'
    rows += f'<div><dt>{"Langues" if lang=="fr" else "Languages"}</dt><dd>{"Français et anglais" if lang=="fr" else "English and French"}</dd></div>'
    if lang == "fr":
        eyebrow, h2 = "Contact", "Indiquez votre échéance et votre nombre d'entités : je réponds sous un jour ouvré"
        p = ("Le plus rapide est un court e-mail précisant les pays concernés, le nombre d'entités juridiques et la date de mise en production visée. "
             "Les propositions sont rédigées en français ou en anglais.")
    else:
        eyebrow, h2 = "Contact", "Tell me your deadline and entity count, and I will reply within one business day"
        p = ("The quickest start is a short email with the countries in scope, the number of legal entities and the date you need to be live. "
             "Proposals are available in English or French.")
    anchor = "contact"
    return (f'<section class="block last" id="{anchor}"><div class="wrap">{head_block(eyebrow, h2)}'
            f'<div class="contact-grid"><div class="prose"><p>{p}</p>'
            f'<p><a class="btn solid" href="mailto:{EMAIL}">{T[lang]["cta"]}</a></p></div>'
            f'<dl class="dl">{rows}</dl></div></div></section>')

def cta_band(lang):
    if lang == "fr":
        h2 = "Un projet ou une échéance réglementaire à tenir ? Parlons-en."
        p = "Appel de cadrage de trente minutes, sans frais, puis une proposition écrite sous trois jours ouvrés."
    else:
        h2 = "Facing a deadline or a new entity to bring live? Let's talk."
        p = "A free thirty-minute scoping call, then a written proposal within three business days."
    return (f'<section class="block last"><div class="wrap"><div class="offer"><div class="prose">'
            f'<h2 class="sub" style="font-size:22px;line-height:28px;font-weight:400">{h2}</h2><p>{p}</p></div>'
            f'<a class="btn solid" href="mailto:{EMAIL}">{T[lang]["cta"]}</a></div></div></section>')

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
def header(lang, key):
    t = T[lang]
    other = "en" if lang == "fr" else "fr"
    links = ""
    for label, href in t["nav"]:
        cur = ' aria-current="page"' if href == PATHS.get(key, {}).get(lang) else ""
        links += f'<a href="{href}"{cur}>{label}</a>'
    links += (f'<a class="lang" href="{PATHS[key][other]}" hreflang="{other}" lang="{other}" '
              f'aria-label="{t["other_label"]}">{t["other"]}</a>')
    sub = "Conseil" if lang == "fr" else "Conseil"
    return (f'<a class="skip" href="#main">{t["skip"]}</a>'
            f'<header class="top"><div class="wrap"><a class="brand" href="{PATHS["home"][lang]}">{NAME} <span>{sub}</span></a>'
            f'<nav aria-label="{"Navigation principale" if lang=="fr" else "Main navigation"}">{links}</nav></div></header>')

def footer(lang):
    t = T[lang]
    exp = "".join(f'<li><a href="{PATHS[k][lang]}">{SERVICE_TITLES[k][lang]}</a></li>' for k in SERVICE_TITLES)
    info = (f'<li><a href="{PATHS["offers"][lang]}">{t["offers"]}</a></li>'
            f'<li><a href="{PATHS["legal"][lang]}">{t["legal"]}</a></li>'
            f'<li><a href="{PATHS["privacy"][lang]}">{t["privacy"]}</a></li>')
    cont = f'<li><a href="mailto:{EMAIL}">{EMAIL}</a></li><li>{CITY}, France</li>'
    if LINKEDIN:
        cont += f'<li><a href="{LINKEDIN}" rel="me">LinkedIn</a></li>'
    return (f'<footer><div class="wrap">'
            f'<div><h2>{BRAND}</h2><p>{t["tagline"]}.</p></div>'
            f'<div><h2>{t["foot_exp"]}</h2><ul>{exp}</ul></div>'
            f'<div><h2>{t["foot_info"]}</h2><ul>{info}</ul></div>'
            f'<div><h2>{t["foot_contact"]}</h2><ul>{cont}</ul></div>'
            f'<div class="base"><span>{t["rights"]}</span><span>{"Prix hors TVA" if lang=="fr" else "Prices exclude VAT"}</span></div>'
            f'</div></footer>')

def person_ld():
    p = {"@type": "Person", "@id": SITE_URL + "/#person", "name": NAME,
         "jobTitle": "Consultant fonctionnel Dynamics 365 Finance & Operations",
         "knowsLanguage": ["fr", "en"],
         "knowsAbout": ["Microsoft Dynamics 365 Finance & Operations", "Facturation électronique", "Electronic Reporting",
                        "FEC", "DAS-2", "IFRS 16", "Automatisation de la comptabilité fournisseurs", "Intégration d'entités juridiques"]}
    if LINKEDIN:
        p["sameAs"] = [LINKEDIN]
    return p

def org_ld(lang):
    o = {"@type": "ProfessionalService", "@id": SITE_URL + "/#business", "name": BRAND, "url": SITE_URL + "/",
         "image": SITE_URL + "/assets/og.png", "email": EMAIL,
         "founder": {"@id": SITE_URL + "/#person"},
         "address": {"@type": "PostalAddress", "addressLocality": CITY, "addressRegion": REGION, "addressCountry": "FR"},
         "areaServed": [{"@type": "Country", "name": c} for c in ("France", "Belgium", "Germany")] + [{"@type": "Place", "name": "EMEA"}],
         "availableLanguage": ["fr", "en"], "priceRange": "€€€",
         "description": DESCRIPTIONS["home"][lang]}
    if PHONE:
        o["telephone"] = PHONE
    return o

def breadcrumb_ld(lang, key, title):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": T[lang]["home"], "item": SITE_URL + PATHS["home"][lang]},
        {"@type": "ListItem", "position": 2, "name": title, "item": SITE_URL + PATHS[key][lang]}]}

def faq_ld(faqs):
    return {"@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}

def page(lang, key, title, desc, body, ld=None, noindex=False):
    url = SITE_URL + PATHS[key][lang] if key in PATHS else SITE_URL + "/404.html"
    alts = ""
    if key in PATHS:
        alts = (f'<link rel="alternate" hreflang="fr" href="{SITE_URL}{PATHS[key]["fr"]}">'
                f'<link rel="alternate" hreflang="en" href="{SITE_URL}{PATHS[key]["en"]}">'
                f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}{PATHS[key]["fr"]}">')
    ld_html = ""
    if ld:
        ld_html = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False) + "</script>"
    if lang == "fr":
        body = fr_html(body)
        title, desc = fr_text(title), fr_text(desc)
    robots = '<meta name="robots" content="noindex">' if noindex else '<meta name="robots" content="index,follow,max-image-preview:large">'
    full_title = title if key == "home" else f"{title} | {BRAND}"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{desc}">
{robots}
<link rel="canonical" href="{url}">
{alts}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="{"fr_FR" if lang=="fr" else "en_GB"}">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE_URL}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1f3864">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/libre-franklin-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/styles.css">
{ld_html}
</head>
<body>
{header(lang, key if key in PATHS else "home")}
<main id="main">
{body}
</main>
{footer(lang)}
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------
DESCRIPTIONS = {
    "home": {"fr": "Consultant indépendant Dynamics 365 Finance & Operations, comptable de formation. Facturation électronique, conformité statutaire, automatisation fournisseurs et nouvelles entités, en France et en EMEA.",
             "en": "Independent Dynamics 365 Finance & Operations consultant and accountant by background. E-invoicing, statutory compliance, AP automation and new legal entities across France and EMEA."},
    "einv": {"fr": "Mise en conformité facturation électronique dans Dynamics 365 Finance : plateforme agréée, Factur-X, statuts du cycle de vie, formats ER. France, Belgique et Allemagne.",
             "en": "E-invoicing compliance in Dynamics 365 Finance: approved platform integration, Factur-X, lifecycle statuses and ER formats for France, Belgium and Germany."},
    "stat": {"fr": "FEC, DAS-2, reporting belge et IFRS 16 dans Dynamics 365 Finance : paramétrage, formats Electronic Reporting et contrôles avant dépôt.",
             "en": "FEC, DAS-2, Belgian reporting and IFRS 16 in Dynamics 365 Finance: configuration, Electronic Reporting formats and pre-filing checks."},
    "ap":   {"fr": "Automatisation de la comptabilité fournisseurs dans Dynamics 365 Finance : OCR, rapprochement à trois voies, workflow d'approbation et rapprochement auxiliaire-général.",
             "en": "Accounts payable automation in Dynamics 365 Finance: OCR capture, three-way matching, approval workflow and subledger-to-ledger reconciliation."},
    "entity": {"fr": "Création d'une nouvelle entité juridique dans Dynamics 365 Finance après une acquisition : comptabilité, taxes, interco, à-nouveaux et mise en production. Forfait à partir de 9 500 €.",
               "en": "Bringing a new legal entity live in Dynamics 365 Finance after an acquisition: ledger, tax, intercompany, opening balances and go-live. Fixed price from €9,500."},
    "offers": {"fr": "Forfaits de support mensuels et projets au forfait pour Dynamics 365 Finance & Operations. Tarifs publics, hors TVA, et conditions d'intervention.",
               "en": "Monthly support retainers and fixed-price projects for Dynamics 365 Finance & Operations. Published rates excluding VAT, and terms of engagement."},
    "legal": {"fr": f"Mentions légales du site {BRAND}.", "en": f"Legal notice for the {BRAND} website."},
    "privacy": {"fr": f"Politique de confidentialité du site {BRAND} : aucun cookie, mesure d'audience anonyme.",
                "en": f"Privacy policy for the {BRAND} website: no cookies, anonymous visitor statistics."},
}

AREAS = {
    "fr": [("einv", ["Obligation française B2B : plateforme agréée, statuts du cycle de vie, motifs de refus",
                     "Factur-X et UBL générés par Electronic Reporting",
                     "Déploiements Belgique et Allemagne sur le même modèle"]),
           ("stat", ["Fichier des écritures comptables (FEC) et déclarations DAS-2",
                     "Reporting statutaire belge",
                     "IFRS 16 avec le module Asset leasing"]),
           ("ap",   ["Capture OCR alimentant le journal des factures fournisseurs",
                     "Rapprochement à trois voies avec commande et accusé de réception",
                     "Rapprochement auxiliaire et grand livre dans un contexte SOX"]),
           ("entity", ["Nouvelles entités : comptabilité, taxes, souches et interco",
                       "À-nouveaux et bascule des sociétés acquises",
                       "Évaluation des plateformes après une fusion"])],
    "en": [("einv", ["French B2B mandate: approved platform, lifecycle statuses and rejection reasons",
                     "Factur-X and UBL output through Electronic Reporting",
                     "Belgian and German rollouts on the same template"]),
           ("stat", ["FEC audit file and DAS-2 declarations for France",
                     "Belgian statutory reporting",
                     "IFRS 16 lease accounting with Asset leasing"]),
           ("ap",   ["OCR capture feeding the vendor invoice journal",
                     "Three-way matching against purchase order and product receipt",
                     "Subledger-to-ledger reconciliation in a SOX context"]),
           ("entity", ["New legal entities: ledger, tax, number sequences and intercompany",
                       "Opening balances and cutover for acquired businesses",
                       "Platform assessments after a merger"])],
}

def home(lang):
    if lang == "fr":
        eyebrow = "Dynamics 365 Finance & Operations · Finance et conformité"
        h1 = "Un comptable qui paramètre D365 F&O, pour des processus financiers qui passent l'audit et démarrent à temps"
        lede = ("Conseil fonctionnel indépendant pour les directions financières en France et en EMEA. "
                "Facturation électronique, reporting statutaire, automatisation fournisseurs et nouvelles entités, en support mensuel ou au forfait.")
        meta = f"Basé près de {CITY} · Sur site en {REGION} et Île-de-France · À distance en EMEA · Français et anglais"
        exp_eb, exp_h2 = "Expertises", "Quatre domaines financiers où une erreur de paramétrage coûte le plus cher, et où j'ai livré en production"
        more = "En savoir plus"
        off_eb, off_h2 = "Offres et tarifs · 2026-2027", "Un support mensuel engagé ou un projet au périmètre défini, avec des prix connus d'avance"
        ret_h3 = "Forfaits de support : un volume de jours fixe chaque mois, à un taux réduit en échange de l'engagement"
        pkg_h3 = "Projets au forfait : des livrables définis, facturés par jalon"
        meth_eb, meth_h2 = "Méthode", "Chaque mission est cadrée par ses livrables et ses critères de recette avant toute facturation"
        exp_id, meth_id = "expertises", "methode"
    else:
        eyebrow = "Dynamics 365 Finance & Operations · Finance and compliance"
        h1 = "An accountant who configures D365 F&O, so your finance processes pass audit and go live on time"
        lede = ("Independent functional consulting for finance teams across France and EMEA. "
                "E-invoicing mandates, statutory reporting, AP automation and new legal entities, as monthly support or fixed-price projects.")
        meta = f"Based near {CITY} · On site in {REGION} and Île-de-France · Remote across EMEA · English and French"
        exp_eb, exp_h2 = "Expertise", "Four finance areas where configuration mistakes cost the most, and where I have delivered in production"
        more = "Read more"
        off_eb, off_h2 = "Services and rates · 2026-2027", "Buy committed monthly support or a fixed-scope project, both priced up front"
        ret_h3 = "Support retainers: a fixed block of days each month, at a lower rate for the commitment"
        pkg_h3 = "Fixed-price packages: defined deliverables, invoiced by milestone"
        meth_eb, meth_h2 = "Approach", "Every engagement is scoped by deliverables and acceptance criteria before any work is billed"
        exp_id, meth_id = "expertise", "approach"

    areas = ""
    for k, items in AREAS[lang]:
        lis = "".join(f"<li>{i}</li>" for i in items)
        areas += (f'<div class="area"><h3><a href="{PATHS[k][lang]}">{SERVICE_TITLES[k][lang]}</a></h3>'
                  f'<ul>{lis}</ul><a class="more" href="{PATHS[k][lang]}">{more}</a></div>')

    body = f"""
<section class="cover"><div class="wrap">
<div class="eyebrow">{eyebrow}</div>
<h1>{h1}</h1>
<div class="accent-rule" aria-hidden="true"></div>
<p class="lede">{lede}</p>
<div class="cta-row"><a class="btn" href="#contact">{T[lang]["cta"]}</a><a class="link-on-navy" href="{PATHS["offers"][lang]}">{T[lang]["see_offers"]}</a></div>
<p class="meta">{meta}</p>
</div></section>
{figures(lang)}
<section class="block" id="{exp_id}"><div class="wrap">{head_block(exp_eb, exp_h2)}<div class="areas">{areas}</div></div></section>
<section class="block"><div class="wrap">{head_block(off_eb, off_h2)}
<h3 class="sub">{ret_h3}</h3>{retainer_table(lang)}
<div class="gap"></div>
<h3 class="sub">{pkg_h3}</h3>{package_table(lang)}
<p class="note"><a href="{PATHS["offers"][lang]}">{T[lang]["see_offers"]}</a></p>
</div></section>
<section class="block" id="{meth_id}"><div class="wrap">{head_block(meth_eb, meth_h2)}{steps(lang)}</div></section>
{contact_block(lang)}
"""
    title = (f"{NAME} | Consultant Dynamics 365 Finance, facturation électronique" if lang == "fr"
             else f"{NAME} | Dynamics 365 Finance consultant, e-invoicing and compliance")
    ld = [org_ld(lang), person_ld(), {"@type": "WebSite", "@id": SITE_URL + "/#website", "url": SITE_URL + "/", "name": BRAND,
                                      "inLanguage": ["fr", "en"], "publisher": {"@id": SITE_URL + "/#business"}}]
    return page(lang, "home", title, DESCRIPTIONS["home"][lang], body, ld)

# Service pages ---------------------------------------------------------------
SERVICES = {
  "einv": {
    "fr": {
      "title": "Facturation électronique dans Dynamics 365 Finance",
      "h1": "Votre facturation électronique conforme dans D365 Finance, sans bloquer la clôture ni les paiements",
      "lede": "L'obligation française impose à toutes les entreprises de recevoir des factures électroniques depuis le 1er septembre 2026. Les PME et microentreprises devront aussi les émettre au 1er septembre 2027. J'ai mis 26 entités en production à la première échéance.",
      "what_h2": "Ce que je prends en charge, de l'analyse des écarts à la mise en production",
      "points": [("Intégration plateforme agréée", "Flux d'émission et de réception entre D365 et votre plateforme agréée (ex-PDP), y compris par API JSON."),
                 ("Cycle de vie des factures", "Statuts déposée, rejetée, refusée, encaissée remontés dans D365, avec les motifs de refus côté fournisseurs."),
                 ("Formats Electronic Reporting", "Factur-X, UBL et CII générés et testés par ER, avec les mentions obligatoires de la réforme."),
                 ("Données de référence", "SIREN, adresses de facturation et codes de routage contrôlés avant la bascule."),
                 ("Belgique et Allemagne", "Peppol en Belgique et XRechnung ou ZUGFeRD en Allemagne, sur le même modèle de déploiement."),
                 ("Recette et bascule", "Plan de tests par entité, suivi des anomalies et accompagnement le jour de la mise en production.")],
      "pkg": "einv",
      "faq": [("Mon entreprise est-elle concernée dès septembre 2026 ?", "Oui pour la réception : toutes les entreprises assujetties à la TVA en France doivent pouvoir recevoir des factures électroniques depuis le 1er septembre 2026. L'émission est obligatoire à cette date pour les grandes entreprises et les ETI, et au 1er septembre 2027 pour les PME et microentreprises."),
              ("Faut-il un développement X++ ?", "Rarement pour le cœur du sujet. Les formats passent par Electronic Reporting et les échanges par la plateforme agréée. Quand une intégration demande du code, je la chiffre à part avec un développeur partenaire."),
              ("Que contient le diagnostic à 4 000 € ?", "Cinq jours d'analyse des écarts par rapport à l'obligation, une revue de vos formats ER et de vos flux avec la plateforme, puis un plan de remédiation priorisé et chiffré.")],
    },
    "en": {
      "title": "E-invoicing in Dynamics 365 Finance",
      "h1": "E-invoicing compliance in D365 Finance that does not hold up your close or your payments",
      "lede": "Since 1 September 2026, every French company must be able to receive electronic invoices. SMEs and micro-businesses must also issue them from 1 September 2027. I took 26 legal entities live for the first deadline.",
      "what_h2": "What I cover, from gap assessment to go-live",
      "points": [("Approved platform integration", "Outbound and inbound flows between D365 and your approved platform (formerly PDP), including JSON APIs."),
                 ("Invoice lifecycle", "Submitted, rejected, refused and paid statuses brought back into D365, with refusal reasons on vendor invoices."),
                 ("Electronic Reporting formats", "Factur-X, UBL and CII generated and tested through ER, with the mandatory fields the reform adds."),
                 ("Master data", "SIREN numbers, billing addresses and routing codes checked before cutover."),
                 ("Belgium and Germany", "Peppol for Belgium and XRechnung or ZUGFeRD for Germany, on the same rollout template."),
                 ("Testing and cutover", "Test plan per entity, defect tracking and support on go-live day.")],
      "pkg": "einv",
      "faq": [("Does the September 2026 deadline apply to my company?", "For receiving, yes: every VAT-registered company in France must be able to receive electronic invoices from 1 September 2026. Issuing became mandatory on that date for large and mid-sized companies, and applies to SMEs and micro-businesses from 1 September 2027."),
              ("Do I need X++ development?", "Rarely for the core work. Formats run through Electronic Reporting and exchanges go through the approved platform. Where an integration needs code, I quote it separately with a partner developer."),
              ("What does the €4,000 health check include?", "Five days of gap assessment against the mandate, a review of your ER formats and platform flows, and a prioritised, costed remediation plan.")],
    },
  },
  "stat": {
    "fr": {
      "title": "Conformité statutaire dans Dynamics 365 Finance",
      "h1": "Des déclarations statutaires produites par D365 Finance, contrôlées avant dépôt et défendables en contrôle fiscal",
      "lede": "Un FEC rejeté ou une DAS-2 incomplète coûte une pénalité et du temps. Je paramètre et je teste les formats statutaires pour qu'ils sortent justes du système, sans retraitement sous Excel.",
      "what_h2": "Les obligations que je paramètre et que je fais vérifier avant chaque échéance",
      "points": [("Fichier des écritures comptables", "FEC conforme à l'article A47 A-1 du LPF, testé avec l'outil de contrôle de l'administration."),
                 ("DAS-2", "Honoraires et commissions identifiés à la source sur les fournisseurs, puis déclaration générée par ER."),
                 ("Reporting belge", "Listing clients, relevé intracommunautaire et déclarations TVA pour les entités belges."),
                 ("IFRS 16", "Contrats de location dans Asset leasing : droits d'utilisation, dettes locatives et écritures périodiques."),
                 ("Formats Electronic Reporting", "Formats Microsoft adaptés ou créés quand le standard ne suffit pas, avec une documentation pour votre support."),
                 ("Clôture annuelle", "Check-list, revue du paramétrage et accompagnement pendant le traitement de clôture.")],
      "pkg": "er",
      "faq": [("Le FEC standard de D365 est-il suffisant ?", "Il couvre la structure attendue, mais les écarts viennent souvent du paramétrage : libellés, journaux, dates de lettrage ou écritures de simulation. Je le teste sur vos données réelles avant la demande de l'administration."),
              ("Pouvez-vous intervenir uniquement pour la clôture ?", "Oui. L'accompagnement clôture annuelle est un forfait de trois jours à 2 400 € hors TVA."),
              ("Travaillez-vous sur d'autres pays ?", "La France et la Belgique sont mes pays de référence. Pour les autres pays EMEA, j'interviens sur la partie paramétrage D365 avec votre conseil local.")],
    },
    "en": {
      "title": "Statutory compliance in Dynamics 365 Finance",
      "h1": "Statutory filings produced by D365 Finance, checked before submission and defensible in a tax audit",
      "lede": "A rejected FEC file or an incomplete DAS-2 costs a penalty and staff time. I configure and test statutory formats so they come out of the system right, without rework in Excel.",
      "what_h2": "The obligations I configure and check before every deadline",
      "points": [("FEC audit file", "FEC compliant with article A47 A-1 of the French tax procedure code, tested with the tax authority's checking tool."),
                 ("DAS-2", "Fees and commissions flagged at source on vendors, then the declaration generated through ER."),
                 ("Belgian reporting", "Annual customer listing, intra-community listing and VAT returns for Belgian entities."),
                 ("IFRS 16", "Leases in Asset leasing: right-of-use assets, lease liabilities and periodic entries."),
                 ("Electronic Reporting formats", "Microsoft formats adapted or new ones built where the standard falls short, documented for your support team."),
                 ("Year-end close", "Checklist, configuration review and support through the closing run.")],
      "pkg": "er",
      "faq": [("Is the standard D365 FEC enough?", "It covers the required structure, but gaps usually come from configuration: descriptions, journals, settlement dates or simulation entries. I test it on your real data before the tax authority asks for it."),
              ("Can you help with year-end close only?", "Yes. Year-end close support is a three-day package at €2,400 excluding VAT."),
              ("Do you cover other countries?", "France and Belgium are my core countries. For other EMEA countries I handle the D365 configuration alongside your local adviser.")],
    },
  },
  "ap": {
    "fr": {
      "title": "Automatisation de la comptabilité fournisseurs dans D365 Finance",
      "h1": "Une comptabilité fournisseurs automatisée dans D365 Finance, de la capture OCR au paiement",
      "lede": "Chaque facture saisie à la main ralentit la clôture et augmente le risque de doublon. J'automatise la chaîne fournisseurs dans D365 pour que l'équipe ne traite plus que les exceptions.",
      "what_h2": "La chaîne fournisseurs que je mets en place, étape par étape",
      "points": [("Capture OCR", "Factures lues par votre outil de capture et créées dans le journal des factures fournisseurs, sans ressaisie."),
                 ("Rapprochement à trois voies", "Facture, commande et accusé de réception rapprochés avec des tolérances de prix et de quantité adaptées."),
                 ("Workflow d'approbation", "Circuits par montant, entité et centre de coût, avec délégation pendant les absences."),
                 ("Motifs de refus", "Refus tracés et renvoyés au fournisseur, en cohérence avec la facturation électronique."),
                 ("Rapprochement auxiliaire", "Auxiliaire fournisseurs et grand livre rapprochés chaque mois, avec une piste d'audit SOX."),
                 ("Indicateurs", "Délai de traitement, taux de rapprochement automatique et factures en attente suivis par entité.")],
      "pkg": None,
      "faq": [("Quel outil OCR utilisez-vous ?", "Celui que vous avez déjà, ou celui fourni par votre plateforme agréée. J'ai travaillé avec YOOZ. Mon rôle porte sur le paramétrage D365 et sur l'intégration."),
              ("Le rapprochement à trois voies est-il obligatoire ?", "Non. Il convient aux achats sur commande. Pour les frais généraux sans commande, un workflow d'approbation bien conçu suffit souvent."),
              ("Comment est chiffré ce type de projet ?", f"Au forfait après l'appel de cadrage, ou au taux journalier de {DAY_RATE} € pour un rôle dans un projet plus large.")],
    },
    "en": {
      "title": "Accounts payable automation in D365 Finance",
      "h1": "Accounts payable automated in D365 Finance, from OCR capture to payment",
      "lede": "Every invoice keyed by hand slows the close and raises the risk of duplicates. I automate the payables chain in D365 so your team only handles exceptions.",
      "what_h2": "The payables chain I put in place, step by step",
      "points": [("OCR capture", "Invoices read by your capture tool and created in the vendor invoice journal, with no rekeying."),
                 ("Three-way matching", "Invoice, purchase order and product receipt matched with price and quantity tolerances that fit your business."),
                 ("Approval workflow", "Routing by amount, entity and cost centre, with delegation during absences."),
                 ("Refusal reasons", "Refusals tracked and sent back to the vendor, consistent with e-invoicing."),
                 ("Subledger reconciliation", "Vendor subledger and general ledger reconciled monthly, with a SOX audit trail."),
                 ("Measures", "Processing time, automatic match rate and invoices on hold tracked by entity.")],
      "pkg": None,
      "faq": [("Which OCR tool do you use?", "The one you already have, or the one your approved platform provides. I have worked with YOOZ. My role covers D365 configuration and the integration."),
              ("Is three-way matching required?", "No. It suits purchase-order spend. For overheads without a purchase order, a well-designed approval workflow is often enough."),
              ("How is this kind of project priced?", f"As a fixed price after the scoping call, or at a day rate of €{DAY_RATE} for a role in a wider project.")],
    },
  },
  "entity": {
    "fr": {
      "title": "Nouvelle entité juridique dans Dynamics 365 Finance",
      "h1": "Une société acquise opérationnelle dans D365 Finance en quelques semaines, à un prix fixé d'avance",
      "lede": "Après une acquisition, la nouvelle entité doit facturer, payer et consolider dès le premier mois. Je la paramètre, je la teste et je la mets en production avec vos équipes groupe et locales.",
      "what_h2": "Tout ce qu'une nouvelle entité doit avoir avant sa première clôture",
      "points": [("Comptabilité", "Plan de comptes, exercices, devises et dimensions financières alignés sur le groupe."),
                 ("Taxes", "Codes et groupes de taxes, déclarations TVA et paramètres locaux du pays."),
                 ("Souches et paramètres", "Souches de numérotation, journaux, conditions de paiement et modes de règlement."),
                 ("Interco", "Comptes et règles interco pour que les flux avec le groupe s'équilibrent automatiquement."),
                 ("À-nouveaux et bascule", "Reprise des soldes, des tiers et des encours, avec un contrôle de cohérence avant validation."),
                 ("Mise en production", "Recette avec les équipes locales, support pendant le premier mois et la première clôture.")],
      "pkg": "entity",
      "faq": [("Combien de temps faut-il ?", "Douze jours de travail pour une entité standard, répartis sur trois à six semaines selon la disponibilité de vos équipes et des données à reprendre."),
              ("Que se passe-t-il si l'entité est sur un autre ERP ?", "La reprise se fait depuis l'ancien système par fichiers de migration. J'ai accompagné des sociétés venant de Dynamics GP notamment."),
              ("Le prix de 9 500 € couvre-t-il tout ?", "Il couvre une entité standard dans un pays déjà paramétré dans votre environnement. Un nouveau pays, des flux spécifiques ou des développements font l'objet d'un devis complémentaire.")],
    },
    "en": {
      "title": "New legal entity in Dynamics 365 Finance",
      "h1": "An acquired company running in D365 Finance within weeks, at a price fixed up front",
      "lede": "After an acquisition, the new entity has to invoice, pay and consolidate from the first month. I configure it, test it and take it live with your group and local teams.",
      "what_h2": "Everything a new entity needs before its first close",
      "points": [("Ledger", "Chart of accounts, fiscal calendars, currencies and financial dimensions aligned with the group."),
                 ("Tax", "Sales tax codes and groups, VAT returns and local country settings."),
                 ("Number sequences and parameters", "Number sequences, journals, payment terms and methods of payment."),
                 ("Intercompany", "Intercompany accounts and rules so flows with the group balance automatically."),
                 ("Opening balances and cutover", "Balances, customers, vendors and open items migrated, with consistency checks before posting."),
                 ("Go-live", "Testing with local teams, then support through the first month and the first close.")],
      "pkg": "entity",
      "faq": [("How long does it take?", "Twelve working days for a standard entity, spread over three to six weeks depending on your teams' availability and the data to migrate."),
              ("What if the entity runs another ERP?", "Data comes across from the old system through migration files. I have supported companies coming from Dynamics GP, for example."),
              ("Does the €9,500 price cover everything?", "It covers a standard entity in a country already configured in your environment. A new country, specific flows or development are quoted separately.")],
    },
  },
}

def service(lang, key):
    s = SERVICES[key][lang]
    title = SERVICE_TITLES[key][lang]
    pts = "".join(f"<li><b>{a}</b><span>{b}</span></li>" for a, b in s["points"])
    if s["pkg"]:
        p = PACKAGES[s["pkg"]]
        name, desc = p[lang]
        days = f'{p["days"]} {"jours" if lang=="fr" else "days"}'
        offer = (f'<div class="offer"><div class="prose"><h3 class="sub">{name}</h3><p>{desc}</p></div>'
                 f'<div class="price">{price_txt(p, lang)}<small>{days} · {"hors TVA" if lang=="fr" else "excl. VAT"}</small></div></div>')
        off_h2 = ("Un forfait au périmètre défini, pour démarrer sans risque budgétaire" if lang == "fr"
                  else "A fixed-scope package, so you start without budget risk")
    else:
        o_h = "Au forfait ou au taux journalier" if lang == "fr" else "Fixed price or day rate"
        o_p = ("Chiffré au forfait après l'appel de cadrage, ou en régie pour un rôle dans un projet plus large." if lang == "fr"
               else "Quoted as a fixed price after the scoping call, or on a day rate for a role in a wider project.")
        offer = (f'<div class="offer"><div class="prose"><h3 class="sub">{o_h}</h3>'
                 f'<p>{o_p}</p></div>'
                 f'<div class="price">{eur(DAY_RATE, lang)}<small>{"par jour · hors TVA" if lang=="fr" else "per day · excl. VAT"}</small></div></div>')
        off_h2 = ("Un prix connu avant de démarrer, au forfait ou au jour" if lang == "fr"
                  else "A price agreed before work starts, fixed or by the day")
    faq = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in s["faq"])
    faq_h2 = "Questions fréquentes" if lang == "fr" else "Frequently asked questions"
    eyebrow = ("Expertise · " if lang == "en" else "Expertise · ") + title
    crumb_label = "Fil d'Ariane" if lang == "fr" else "Breadcrumb"
    crumbs = f'<nav class="crumbs" aria-label="{crumb_label}"><a href="{PATHS["home"][lang]}">{T[lang]["home"]}</a> / {title}</nav>'
    body = f"""
<section class="cover sub"><div class="wrap">
{crumbs}
<div class="eyebrow">{eyebrow}</div>
<h1>{s["h1"]}</h1>
<div class="accent-rule" aria-hidden="true"></div>
<p class="lede">{s["lede"]}</p>
<div class="cta-row"><a class="btn" href="mailto:{EMAIL}">{T[lang]["cta"]}</a><a class="link-on-navy" href="{PATHS["offers"][lang]}">{T[lang]["see_offers"]}</a></div>
</div></section>
<section class="block"><div class="wrap">{head_block(title, s["what_h2"])}<ul class="points">{pts}</ul></div></section>
<section class="block"><div class="wrap">{head_block(T[lang]["offers"], off_h2)}{offer}</div></section>
<section class="block"><div class="wrap">{head_block("FAQ", faq_h2)}<div class="faq">{faq}</div></div></section>
{cta_band(lang)}
"""
    ld = [breadcrumb_ld(lang, key, title),
          {"@type": "Service", "name": s["title"], "serviceType": title, "provider": {"@id": SITE_URL + "/#business"},
           "areaServed": ["FR", "BE", "DE"], "description": DESCRIPTIONS[key][lang], "url": SITE_URL + PATHS[key][lang]},
          faq_ld([(fr_text(q) if lang == "fr" else q, fr_text(a) if lang == "fr" else a) for q, a in s["faq"]])]
    return page(lang, key, s["title"], DESCRIPTIONS[key][lang], body, ld)

def offers(lang):
    if lang == "fr":
        title = "Offres et tarifs"
        h1 = "Des tarifs publiés et des prix fixés avant de démarrer, en support mensuel ou au forfait"
        lede = f"Deux façons de travailler ensemble. Les forfaits de support réservent des jours chaque mois. Les projets au forfait livrent un résultat défini. Le taux journalier de référence est de {eur(DAY_RATE, lang)} hors TVA."
        ret_h2 = "Forfaits de support : un volume de jours fixe chaque mois, à un taux réduit en échange de l'engagement"
        ret_note = f"Couvre D365 F&O Finance fonctionnel, Electronic Reporting, clôtures et incidents de facturation électronique. Les jours non utilisés sont reportés d'un mois. Engagement de six mois, puis mensuel avec un mois de préavis. Jours supplémentaires à {eur(DAY_RATE, lang)}."
        pkg_h2 = "Projets au forfait : des livrables définis, un prix connu d'avance, facturés par jalon"
        pkg_note = f"Rôles projet, implémentations et missions de transition disponibles au taux journalier de {eur(DAY_RATE, lang)}."
        terms_h2 = "Des conditions simples, écrites dans chaque proposition"
        cap = "Prix indicatifs en euros hors TVA, confirmés dans chaque proposition."
        eb1, eb2, eb3 = "Support mensuel", "Projets au forfait", "Conditions"
    else:
        title = "Services and rates"
        h1 = "Published rates and prices fixed before work starts, as monthly support or fixed-price projects"
        lede = f"Two ways to work together. Retainers reserve days each month. Fixed-price packages deliver a defined result. The reference day rate is {eur(DAY_RATE, lang)} excluding VAT."
        ret_h2 = "Support retainers: a fixed block of days each month, at a lower rate for the commitment"
        ret_note = f"Covers functional F&O Finance, Electronic Reporting, period-end close and e-invoicing incidents. Unused days roll over for one month. Six-month minimum term, then monthly with one month's notice. Extra days at {eur(DAY_RATE, lang)}."
        pkg_h2 = "Fixed-price packages: defined deliverables, a price known up front, invoiced by milestone"
        pkg_note = f"Project roles, implementations and interim cover are available at a day rate of {eur(DAY_RATE, lang)}."
        terms_h2 = "Simple terms, written into every proposal"
        cap = "Indicative prices in euros excluding VAT, confirmed in each proposal."
        eb1, eb2, eb3 = "Monthly support", "Fixed-price projects", "Terms"
    body = f"""
<section class="cover sub"><div class="wrap">
<div class="eyebrow">{title} · 2026-2027</div>
<h1>{h1}</h1>
<div class="accent-rule" aria-hidden="true"></div>
<p class="lede">{lede}</p>
<div class="cta-row"><a class="btn" href="mailto:{EMAIL}">{T[lang]["cta"]}</a></div>
</div></section>
<section class="block"><div class="wrap">{head_block(eb1, ret_h2)}{retainer_table(lang)}<p class="note">{ret_note}</p></div></section>
<section class="block"><div class="wrap">{head_block(eb2, pkg_h2)}{package_table(lang)}<p class="note">{pkg_note}</p><p class="caption" style="margin-top:14px">{cap}</p></div></section>
<section class="block"><div class="wrap">{head_block(eb3, terms_h2)}{terms(lang)}</div></section>
<section class="block"><div class="wrap">{head_block("Méthode" if lang=="fr" else "Approach", "Chaque mission est cadrée par ses livrables avant toute facturation" if lang=="fr" else "Every engagement is scoped by deliverables before any work is billed")}{steps(lang)}</div></section>
{cta_band(lang)}
"""
    offers_ld = {"@type": "OfferCatalog", "name": f"{title} {BRAND}", "itemListElement": [
        {"@type": "Offer", "name": PACKAGES[k][lang][0], "description": PACKAGES[k][lang][1],
         "priceSpecification": {"@type": "PriceSpecification", "price": PACKAGES[k]["price"], "priceCurrency": "EUR",
                                "valueAddedTaxIncluded": False}} for k in PACKAGES]}
    return page(lang, "offers", title, DESCRIPTIONS["offers"][lang], body,
                [breadcrumb_ld(lang, "offers", title), offers_ld])

def legal(lang):
    host = "Cloudflare, Inc., 101 Townsend St, San Francisco, CA 94107, États-Unis (www.cloudflare.com)"
    if lang == "fr":
        title = "Mentions légales"
        content = f"""
<p>Conformément à l'article 6 de la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique.</p>
<h2>Éditeur du site</h2>
<ul><li>{BRAND}, {LEGAL["form"]}</li><li>Siège : {LEGAL["address"]}</li><li>{LEGAL["siren"]}</li><li>TVA : {LEGAL["vat"]}</li><li>E-mail : <a href="mailto:{EMAIL}">{EMAIL}</a></li></ul>
<h2>Directeur de la publication</h2><p>{NAME}</p>
<h2>Hébergement</h2><p>{host}</p>
<h2>Propriété intellectuelle</h2><p>Les textes et la présentation de ce site appartiennent à {BRAND}. Toute reproduction sans autorisation est interdite. Microsoft et Dynamics 365 sont des marques de Microsoft Corporation. {BRAND} est un conseil indépendant, sans lien avec Microsoft.</p>
<h2>Données personnelles</h2><p>Voir la <a href="{PATHS["privacy"]["fr"]}">politique de confidentialité</a>.</p>
"""
    else:
        title = "Legal notice"
        content = f"""
<p>Published under article 6 of French law no. 2004-575 of 21 June 2004 on confidence in the digital economy.</p>
<h2>Publisher</h2>
<ul><li>{BRAND}, {LEGAL["form"]}</li><li>Registered office: {LEGAL["address"]}</li><li>{LEGAL["siren"]}</li><li>VAT: {LEGAL["vat"]}</li><li>Email: <a href="mailto:{EMAIL}">{EMAIL}</a></li></ul>
<h2>Publication director</h2><p>{NAME}</p>
<h2>Hosting</h2><p>{host.replace("États-Unis", "United States")}</p>
<h2>Intellectual property</h2><p>The text and design of this site belong to {BRAND}. Reproduction without permission is prohibited. Microsoft and Dynamics 365 are trademarks of Microsoft Corporation. {BRAND} is an independent adviser with no affiliation to Microsoft.</p>
<h2>Personal data</h2><p>See the <a href="{PATHS["privacy"]["en"]}">privacy policy</a>.</p>
"""
    body = f'<section class="block last"><div class="wrap"><div class="head"><h1 style="font-size:32px;line-height:40px;color:var(--ink);font-weight:300">{title}</h1></div><div class="title-rule"></div><div class="legal">{content}</div></div></section>'
    return page(lang, "legal", title, DESCRIPTIONS["legal"][lang], body)

def privacy(lang):
    if lang == "fr":
        title = "Politique de confidentialité"
        content = f"""
<p>Ce site ne dépose aucun cookie et n'utilise aucun traceur publicitaire. Aucun bandeau de consentement n'est donc nécessaire.</p>
<h2>Mesure d'audience</h2><p>La fréquentation est mesurée de façon anonyme et agrégée par Cloudflare Web Analytics, sans cookie ni identifiant personnel.</p>
<h2>Polices de caractères</h2><p>Les polices sont hébergées sur ce site. Aucune requête n'est envoyée à un service tiers comme Google Fonts.</p>
<h2>Échanges par e-mail</h2><p>Si vous écrivez à <a href="mailto:{EMAIL}">{EMAIL}</a>, votre message et vos coordonnées servent uniquement à vous répondre et à préparer une éventuelle proposition. Ils sont conservés trois ans après le dernier échange, puis supprimés. Base légale : intérêt légitime et mesures précontractuelles.</p>
<h2>Vos droits</h2><p>Vous disposez d'un droit d'accès, de rectification, d'effacement, de limitation et d'opposition. Écrivez à <a href="mailto:{EMAIL}">{EMAIL}</a>. Vous pouvez aussi saisir la CNIL (www.cnil.fr).</p>
<h2>Responsable du traitement</h2><p>{BRAND}, représentée par {NAME}.</p>
<p class="caption">Dernière mise à jour : {UPDATED}</p>
"""
    else:
        title = "Privacy policy"
        content = f"""
<p>This site sets no cookies and uses no advertising trackers, so no consent banner is needed.</p>
<h2>Visitor statistics</h2><p>Traffic is measured anonymously and in aggregate by Cloudflare Web Analytics, with no cookies or personal identifiers.</p>
<h2>Fonts</h2><p>Fonts are hosted on this site. No request is sent to a third-party service such as Google Fonts.</p>
<h2>Email</h2><p>If you write to <a href="mailto:{EMAIL}">{EMAIL}</a>, your message and contact details are used only to reply and to prepare any proposal. They are kept for three years after the last exchange, then deleted. Legal basis: legitimate interest and pre-contractual steps.</p>
<h2>Your rights</h2><p>You have the right to access, correct, erase, restrict and object. Write to <a href="mailto:{EMAIL}">{EMAIL}</a>. You can also contact the CNIL, the French data protection authority (www.cnil.fr).</p>
<h2>Data controller</h2><p>{BRAND}, represented by {NAME}.</p>
<p class="caption">Last updated: {UPDATED}</p>
"""
    body = f'<section class="block last"><div class="wrap"><div class="head"><h1 style="font-size:32px;line-height:40px;color:var(--ink);font-weight:300">{title}</h1></div><div class="title-rule"></div><div class="legal">{content}</div></div></section>'
    return page(lang, "privacy", title, DESCRIPTIONS["privacy"][lang], body)

def not_found():
    body = (f'<section class="block last"><div class="wrap"><div class="head"><div class="eyebrow">Erreur 404 · Error 404</div>'
            f'<h1 style="font-size:32px;line-height:40px;color:var(--ink);font-weight:300">Cette page n\'existe pas. This page does not exist.</h1></div>'
            f'<div class="title-rule"></div><p><a href="/">Retour à l\'accueil</a> · <a href="/en/">Back to the home page</a></p></div></section>')
    return page("fr", "home", "Page introuvable", "Page introuvable.", body, noindex=True).replace(
        f'<link rel="canonical" href="{SITE_URL}/">', "")

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def write(path, html):
    target = OUT / path.lstrip("/")
    if path.endswith("/"):
        target = target / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")

def check_dashes():
    bad = []
    for f in OUT.rglob("*.html"):
        txt = f.read_text(encoding="utf-8")
        if "—" in txt or "–" in txt:
            bad.append(str(f.relative_to(ROOT)))
    if bad:
        raise SystemExit("Em or en dash found in: " + ", ".join(bad))

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)
    for lang in ("fr", "en"):
        write(PATHS["home"][lang], home(lang))
        for k in SERVICES:
            write(PATHS[k][lang], service(lang, k))
        write(PATHS["offers"][lang], offers(lang))
        write(PATHS["legal"][lang], legal(lang))
        write(PATHS["privacy"][lang], privacy(lang))
    (OUT / "404.html").write_text(not_found(), encoding="utf-8")

    urls = ""
    for k, langs in PATHS.items():
        for lang, p in langs.items():
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE_URL}{q}"/>' for l, q in langs.items())
            urls += f"<url><loc>{SITE_URL}{p}</loc><lastmod>{UPDATED}</lastmod>{alts}</url>\n"
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    check_dashes()
    print(f"Built {len(list(OUT.rglob('*.html')))} pages into {OUT}")

if __name__ == "__main__":
    main()
