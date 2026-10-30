#!/usr/bin/env python3
"""Publish one blog post on this site.

Usage (from the repo root):
    python3 scripts/add_post.py path/to/post.json            # build + validate
    python3 scripts/add_post.py path/to/post.json --check    # validate only, write nothing

post.json fields:
  slug        url slug, lowercase-hyphenated, must not already exist under blog/
  nav         short label used in breadcrumbs and "Keep reading" links
  title       <title> tag, ideally 50-65 characters
  desc        meta description, ideally 130-160 characters
  h1          the on-page headline
  quick       2-3 sentence direct answer shown in a "Quick answer" box (for snippets / AI answers)
  lead        1-2 sentence intro under the quick answer
  disclosure  true for posts that compare or rank SendLove against other sites
  body        article HTML (h2/h3/p/ul/ol/table/blockquote only). Placeholders:
                {sendlove}  -> tracked link to https://sendlove.io/
                {weddings}  -> tracked link to https://sendlove.io/weddings
  faq         list of [question, answer] pairs (4-6)
  related     list of existing blog slugs on THIS site (2-3)
  guides      optional list of existing guide page slugs on THIS site
  cta         optional "weddings" to point the end box at sendlove.io/weddings
  date        optional YYYY-MM-DD (defaults to today)

Also rebuilds blog/index.html, the "From the blog" block on the home page, and sitemap.xml.
"""
import datetime, glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

home = open("index.html", encoding="utf-8").read()
BASE = re.search(r'<link rel="canonical" href="(https://[^/"]+)/?"', home).group(1)
KEY = BASE.split("//")[1].split(".")[0]
SITE = {
    "sendvirtualgifts": dict(name="Send Virtual Gifts", blog_title="Virtual gift blog",
        blog_desc="Honest guides and ideas for sending virtual gifts: the best sites, long-distance gifts, gifts for your boyfriend or girlfriend, wedding invitations, and what to write.",
        disc='<p class="note"><strong>Quick disclosure:</strong> this site is run by the people behind SendLove, which is one of the options in this article. We\'ve tried to be fair about where the others do a better job, and we say so when they do.</p>'),
    "senddigitalgift": dict(name="Send Digital Gift", blog_title="Digital gift blog",
        blog_desc="Practical guides to digital gifts that aren't gift cards: the best sites, long-distance gifts, digital wedding invitations, and gifts for partners, friends and family.",
        disc='<p class="note"><strong>Heads-up:</strong> this site is made by the SendLove team, and SendLove appears in this article. We\'ve tried to be straight about what each option is good at, including the ones that aren\'t ours.</p>'),
}[KEY]

BLOG_CSS_MARK = ".note{"
esc = lambda s: html.escape(s, quote=True)
utm = lambda path, c: f"https://sendlove.io{path}?utm_source={KEY}&amp;utm_medium=referral&amp;utm_campaign=blog-{c}"

def parts():
    style = re.search(r"<style>(.*?)</style>", home, re.S).group(1)
    head = re.search(r'(<meta name="theme-color".*?</script>)', home, re.S).group(1)
    head = re.sub(r'<script type="application/ld\+json">.*?</script>', "", head, flags=re.S)
    header = re.search(r"<body>\s*(.*?)\s*<main>", home, re.S).group(1)
    footer = re.search(r'(<footer class="site-foot">.*?</footer>)', home, re.S).group(1)
    return style, head, header, footer

def page(title, desc, url, ld, body, og="article"):
    style, head, header, footer = parts()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{og}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
{head}
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
</script>
<style>
{style}
</style>
</head>
<body>

{header}

<main>
{body}
</main>

{footer}

</body>
</html>
"""

def existing_posts():
    out = []
    for f in glob.glob("blog/*/index.html"):
        h = open(f, encoding="utf-8").read()
        slug = f.split("/")[1]
        d = re.search(r'"datePublished": "([0-9-]+)"', h)
        out.append(dict(slug=slug, h1=html.unescape(re.search(r"<h1>(.*?)</h1>", h, re.S).group(1)),
                        nav=html.unescape(re.search(r'<div class="crumbs">.*?› .*?› (.*?)</div>', h, re.S).group(1)),
                        desc=html.unescape(re.search(r'<meta name="description" content="(.*?)">', h).group(1)),
                        date=d.group(1) if d else "2026-01-01"))
    out.sort(key=lambda p: (p["date"], p["slug"]), reverse=True)
    return out

def words(h): return len(re.sub(r"<[^>]+>", " ", h).split())

def validate_post(p, posts):
    errs = []
    for k in ["slug", "nav", "title", "desc", "h1", "quick", "lead", "body", "faq", "related"]:
        if not p.get(k): errs.append(f"missing field: {k}")
    if errs: return errs
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p["slug"]): errs.append("slug must be lowercase-hyphenated")
    if any(x["slug"] == p["slug"] for x in posts): errs.append("slug already exists")
    if not 30 <= len(p["title"]) <= 70: errs.append(f"title length {len(p['title'])} (aim 50-65)")
    if not 100 <= len(p["desc"]) <= 170: errs.append(f"desc length {len(p['desc'])} (aim 130-160)")
    n = words(p["body"])
    if n < 1300: errs.append(f"body only {n} words; write at least 1,300 (target 1,500-2,200)")
    if not 4 <= len(p["faq"]) <= 7: errs.append("faq needs 4-6 questions")
    alltext = " ".join([p["title"], p["desc"], p["h1"], p["quick"], p["lead"], re.sub(r"<[^>]+>", " ", p["body"])] + [q + " " + a for q, a in p["faq"]])
    if "$" in alltext or re.search(r"\b\d+(\.\d+)?\s?(USD|CAD|dollars?)\b", alltext, re.I): errs.append("no prices allowed anywhere")
    if re.search(r"no (sign[- ]?up|account)|without (an )?account|account (is )?(not )?(needed|required)", alltext, re.I):
        errs.append("don't make claims about accounts/sign-up")
    if re.search(r"\b(delve|tapestry|in today's|whether you're|game[- ]changer|unlock the|elevate your|seamless(ly)?)\b", alltext, re.I):
        errs.append("contains stock AI phrasing (delve/tapestry/in today's/whether you're/game-changer/unlock/elevate/seamless)")
    if alltext.count("—") > 3: errs.append("too many em dashes; use commas or periods")
    if not re.search(r"\{(sendlove|weddings)\}", p["body"]): errs.append("body should link to SendLove at least once ({sendlove} or {weddings})")
    for s in p["related"]:
        if not os.path.exists(f"blog/{s}/index.html"): errs.append(f"related slug not found: {s}")
    for g in p.get("guides", []):
        if not os.path.exists(f"{g}/index.html"): errs.append(f"guide not found: {g}")
    for href in re.findall(r'href="(/[^"#]*)"', p["body"]):
        t = href.strip("/"); t = t if "." in t.rsplit("/", 1)[-1] else ((t + "/index.html") if t else "index.html")
        if not os.path.exists(t): errs.append(f"broken internal link in body: {href}")
    if "<h1" in p["body"]: errs.append("body must not contain <h1>")
    return errs

def render_post(p):
    date = p.get("date") or datetime.date.today().isoformat()
    url = f"{BASE}/blog/{p['slug']}/"
    by = {x["slug"]: x for x in existing_posts()}
    body = p["body"].strip().replace("{sendlove}", utm("/", p["slug"])).replace("{weddings}", utm("/weddings", p["slug"]))
    related = "".join(f'<a href="/blog/{s}/">{esc(by[s]["nav"])} →</a>' for s in p["related"] if s in by)
    related += "".join(f'<a href="/{g}/">Guide: {esc(g.replace("-", " ").capitalize())} →</a>' for g in p.get("guides", []))
    faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in p["faq"])
    if p.get("cta") == "weddings":
        cta = ("Make your wedding invitation", "Add your names, date, venue and photos, preview it, and send each guest their own link.", utm("/weddings", p["slug"] + "-cta"), "See wedding invitations on SendLove")
    else:
        cta = ("Make one in a few minutes", "Pick a gift, add your words and photos, and send it as a link.", utm("/", p["slug"] + "-cta"), "View gifts on SendLove")
    nice = datetime.date.fromisoformat(date).strftime("%B %-d, %Y")
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "BlogPosting", "headline": p["title"], "description": p["desc"], "url": url, "mainEntityOfPage": url,
         "datePublished": date, "dateModified": date, "inLanguage": "en", "image": f"{BASE}/og-image.png",
         "author": {"@type": "Organization", "name": "SendLove team", "url": "https://sendlove.io/"},
         "publisher": {"@type": "Organization", "name": SITE["name"], "logo": {"@type": "ImageObject", "url": f"{BASE}/icon-512.png"}}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": BASE + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["nav"], "item": url}]},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in p["faq"]]}]}
    art = f"""  <article class="article">
    <div class="crumbs"><a href="/">Home</a> › <a href="/blog/">Blog</a> › {esc(p['nav'])}</div>
    <h1>{esc(p['h1'])}</h1>
    <p class="meta">By the SendLove team · <time datetime="{date}">{nice}</time></p>
    <div class="quick"><strong>Quick answer</strong><p>{esc(p['quick'])}</p></div>
    <p class="lead">{esc(p['lead'])}</p>
    {SITE['disc'] if p.get('disclosure') else ''}
{body}
    <div class="inline-cta">
      <h2 style="margin-top:0">{cta[0]}</h2>
      <p>{cta[1]}</p>
      <a class="btn" href="{cta[2]}">{cta[3]}</a>
    </div>
    <section class="faq" style="padding:0">
      <h2>Frequently asked questions</h2>
      {faq}
    </section>
    <h2>Keep reading</h2>
    <div class="related">{related}</div>
  </article>"""
    return page(p["title"], p["desc"], url, ld, art)

def rebuild_shared():
    global home
    posts = existing_posts()
    cards = "".join(f'<a href="/blog/{p["slug"]}/"><b>{esc(p["h1"][0].upper() + p["h1"][1:])}</b><span>{esc(p["desc"])}</span></a>' for p in posts)
    url = f"{BASE}/blog/"
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": SITE["blog_title"], "url": url, "description": SITE["blog_desc"],
          "blogPost": [{"@type": "BlogPosting", "headline": p["h1"], "url": f"{BASE}/blog/{p['slug']}/", "datePublished": p["date"]} for p in posts]}
    body = f"""  <section class="article" style="max-width:1080px">
    <div class="crumbs"><a href="/">Home</a> › Blog</div>
    <h1>{esc(SITE['blog_title'])}</h1>
    <p class="lead">{esc(SITE['blog_desc'])}</p>
    <div class="posts">{cards}</div>
  </section>"""
    open("blog/index.html", "w", encoding="utf-8").write(page(SITE["blog_title"] + " – " + SITE["name"], SITE["blog_desc"], url, ld, body, "website"))
    feat = "".join(f'<a href="/blog/{p["slug"]}/"><b>{esc(p["nav"])}</b><span>{esc(p["desc"][:110].rsplit(" ", 1)[0])}…</span></a>' for p in posts[:6])
    block = (f'\n<!--blog-start-->\n  <section>\n    <div class="wrap">\n      <h2>From the blog</h2>\n      <div class="posts">{feat}</div>\n'
             f'      <p style="margin-top:18px"><a href="/blog/">All articles →</a></p>\n    </div>\n  </section>\n<!--blog-end-->\n')
    home = re.sub(r"\n<!--blog-start-->.*?<!--blog-end-->\n", block, home, flags=re.S)
    open("index.html", "w", encoding="utf-8").write(home)
    sm = open("sitemap.xml", encoding="utf-8").read()
    sm = re.sub(r"\s*<url><loc>[^<]*/blog/[^<]*</loc>.*?</url>", "", sm)
    add = f"  <url><loc>{url}</loc><lastmod>{posts[0]['date']}</lastmod></url>\n"
    add += "".join(f"  <url><loc>{BASE}/blog/{p['slug']}/</loc><lastmod>{p['date']}</lastmod></url>\n" for p in posts)
    sm = sm.replace("</urlset>", add + "</urlset>")
    open("sitemap.xml", "w", encoding="utf-8").write(sm)

def check_site():
    errs = []
    for f in glob.glob("**/index.html", recursive=True):
        h = open(f, encoding="utf-8").read()
        for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
            try: json.loads(ld)
            except Exception as e: errs.append(f"{f}: bad JSON-LD {e}")
        for href in re.findall(r'href="(/[^"#]*)"', h):
            t = href.strip("/"); t = t if "." in t.rsplit("/", 1)[-1] else ((t + "/index.html") if t else "index.html")
            if not os.path.exists(t): errs.append(f"{f}: broken link {href}")
        if h.count("<h1") != 1: errs.append(f"{f}: needs exactly one h1")
        if "{sendlove}" in h or "{weddings}" in h: errs.append(f"{f}: unresolved placeholder")
    return errs

if __name__ == "__main__":
    p = json.load(open(sys.argv[1], encoding="utf-8"))
    errs = validate_post(p, existing_posts())
    if errs:
        print("NOT PUBLISHED. Fix these:\n- " + "\n- ".join(errs)); sys.exit(1)
    if "--check" in sys.argv:
        print(f"OK: {words(p['body'])} words, ready to publish"); sys.exit(0)
    out = render_post(p)
    os.makedirs(f"blog/{p['slug']}", exist_ok=True)
    open(f"blog/{p['slug']}/index.html", "w", encoding="utf-8").write(out)
    rebuild_shared()
    errs = check_site()
    if errs:
        print("SITE CHECK FAILED:\n- " + "\n- ".join(errs)); sys.exit(1)
    print(f"Published {BASE}/blog/{p['slug']}/ ({words(p['body'])} words). Blog index, home page block and sitemap updated.")
