#!/usr/bin/env python3
"""Static mirror of ridiculouslyhopeful.com — crawl same-domain pages + assets,
rewrite links to relative, save into site/ for static hosting (Caddy on Railway)."""
import os, re, sys, time, hashlib, subprocess
from urllib.parse import urljoin, urlparse, urldefrag
from bs4 import BeautifulSoup

START = "https://ridiculouslyhopeful.com/"
HOST = urlparse(START).netloc
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MAX_PAGES = 200

seen_pages, queued = set(), set()
saved_assets = {}   # url -> local relative path


class Resp:
    def __init__(self, status, headers, content):
        self.status_code = status
        self.headers = headers
        self.content = content
    @property
    def text(self):
        return self.content.decode("utf-8", "replace")


def curl_get(url):
    """Fetch via curl (Cloudflare accepts it where python-requests gets 403)."""
    body = os.path.join("/tmp", "rh_" + hashlib.md5(url.encode()).hexdigest())
    # NOTE: Cloudflare 403s a spoofed browser UA but allows curl's default UA.
    args = ["curl", "-sSL", "--max-time", "40",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            "-w", "%{http_code} %{content_type}", "-o", body, url]
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=60)
        meta = out.stdout.strip().split(" ", 1)
        status = int(meta[0]) if meta and meta[0].isdigit() else 0
        ctype = meta[1] if len(meta) > 1 else ""
        content = b""
        if os.path.exists(body):
            with open(body, "rb") as f:
                content = f.read()
            os.remove(body)
        return Resp(status, {"content-type": ctype}, content)
    except Exception as e:
        print(f"  ! curl err {url}: {e}")
        return Resp(0, {"content-type": ""}, b"")


def is_internal(u):
    n = urlparse(u).netloc
    return n == "" or n == HOST


def local_path_for_page(url):
    """Map a page URL to a local file path under OUT."""
    p = urlparse(url)
    path = p.path
    if path.endswith("/") or path == "":
        path = path + "index.html"
    elif not os.path.splitext(path)[1]:
        path = path + "/index.html"
    return path.lstrip("/")


def local_path_for_asset(url):
    p = urlparse(url)
    path = p.path.lstrip("/")
    if not path or path.endswith("/"):
        path = path + "index.html"
    if p.query:  # keep query-versioned assets distinct
        root, ext = os.path.splitext(path)
        path = root + "_" + hashlib.md5(p.query.encode()).hexdigest()[:6] + ext
    return path


def save(relpath, content, binary=False):
    full = os.path.join(OUT, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "wb" if binary else "w", encoding=None if binary else "utf-8") as f:
        f.write(content)


def fetch(url):
    r = curl_get(url)
    if r.status_code != 200:
        print(f"  ! {r.status_code} {url}"); return None
    return r


def grab_asset(url, from_page_relpath):
    url, _ = urldefrag(url)
    if url in saved_assets:
        return rel(from_page_relpath, saved_assets[url])
    if not is_internal(url):
        return url  # leave external (fonts/CDN) absolute
    r = fetch(url)
    if not r:
        return url
    relpath = local_path_for_asset(url)
    save(relpath, r.content, binary=True)
    saved_assets[url] = relpath
    print(f"  asset {relpath}")
    return rel(from_page_relpath, relpath)


def rel(from_relpath, to_relpath):
    """Relative link from one local file to another."""
    return os.path.relpath(to_relpath, os.path.dirname(from_relpath)) or "."


def process_page(url):
    url, _ = urldefrag(url)
    if url in seen_pages or len(seen_pages) >= MAX_PAGES:
        return
    seen_pages.add(url)
    r = fetch(url)
    if not r or "text/html" not in r.headers.get("content-type", ""):
        return
    page_rel = local_path_for_page(url)
    print(f"PAGE {page_rel}  ({len(seen_pages)})")
    soup = BeautifulSoup(r.text, "html.parser")

    # assets: css, js, img, source, link icons
    for tag, attr in [("link", "href"), ("script", "src"), ("img", "src"),
                      ("source", "src"), ("img", "data-src"), ("source", "srcset")]:
        for t in soup.find_all(tag):
            v = t.get(attr)
            if not v:
                continue
            if attr == "srcset":
                newparts = []
                for part in v.split(","):
                    seg = part.strip().split(" ")
                    au = urljoin(url, seg[0])
                    newparts.append(" ".join([grab_asset(au, page_rel)] + seg[1:]))
                t[attr] = ", ".join(newparts)
            else:
                au = urljoin(url, v)
                if urlparse(au).scheme in ("http", "https"):
                    t[attr] = grab_asset(au, page_rel)

    # internal page links -> queue + rewrite to relative
    for a in soup.find_all("a", href=True):
        href = a["href"]
        au, _ = urldefrag(urljoin(url, href))
        if not au.startswith("http"):
            continue
        if is_internal(au):
            path = urlparse(au).path
            # only follow html-ish pages (skip files w/ non-html extensions)
            ext = os.path.splitext(path)[1].lower()
            if ext and ext not in (".html", ".php", ""):
                continue
            if au not in seen_pages and au not in queued:
                queued.add(au)
            a["href"] = rel(page_rel, local_path_for_page(au))

    save(page_rel, str(soup))


def main():
    queued.add(START)
    while queued and len(seen_pages) < MAX_PAGES:
        url = queued.pop()
        process_page(url)
        time.sleep(0.3)
    print(f"\nDONE: {len(seen_pages)} pages, {len(saved_assets)} assets -> {OUT}")


if __name__ == "__main__":
    main()
