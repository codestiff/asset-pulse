#!/usr/bin/env python3
"""THE CATALOG, the pulse's public half (the-release-infrastructure-this-week,
"The explorer, re-read"): a card per subject, its renders, a 3D look at its
1080 rung 0, and a free download, from the same run as the private page.

    tools/catalog.py out/<date>      # writes out/<date>/catalog/

    CATALOG_ASSET_BASE=https://.../  where the objects are served from (default
                                     `objects/`, beside the page; publish sets
                                     the catalog bucket's public URL)

What it reads, and decides nothing about:
  - the bake (the explorer's tools/bake-library.gd, via tools/bake.sh): every
    rung's glTF, the impostor atlas, each parameter's provenance;
  - the run's close-ups (the library's tools/closeup.sh), as the renders;
  - the library's plates/manifest.json, for what a measured parameter was
    measured off.

What it writes:
  - objects/<sha256[:16]>.<ext>: every glTF, atlas, render and zip, named by
    content, so a byte that did not change is not uploaded twice;
  - one page per subject and an index, static, one script tag (model-viewer);
  - objects.json, the list publish uploads to the catalog bucket.

No cost rows, no scores, no derivation: that is the private page's. The zip is
every rung's glTF, the atlas when the subject has one, and ATTRIBUTION.txt
generated from provenance under the attribution licence in catalog.json.
"""
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import importlib.util  # noqa: E402

# The pulse's own page style and image encoder, from tools/site.py (loaded by
# path: `site` is also the name of a standard-library module).
_spec = importlib.util.spec_from_file_location("pulse_site", Path(__file__).resolve().parent / "site.py")
_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_site)
CSS, small_jpeg = _site.CSS, _site.small_jpeg

ROOT = Path(__file__).resolve().parent.parent
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")

EXTRA_CSS = """
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.card { border: 1px solid var(--line); border-radius: 6px; padding: 10px; min-width: 0; }
.card h3 { margin: 4px 0; font-size: 1em; overflow-wrap: anywhere; }
.card img { margin: 0; aspect-ratio: 1 / 1; object-fit: cover; width: 100%; background: rgba(127,127,127,.08); }
.noimg { aspect-ratio: 1 / 1; display: flex; align-items: center; justify-content: center;
  background: rgba(127,127,127,.08); color: var(--mute); font-size: 13px; }
model-viewer { width: 100%; height: 360px; background: rgba(127,127,127,.08); }
.button { display: inline-block; padding: 8px 14px; border: 1px solid var(--fg); border-radius: 6px;
  text-decoration: none; margin: 4px 8px 4px 0; }
form { display: grid; gap: 8px; max-width: 480px; }
input, textarea { font: inherit; padding: 6px; max-width: 100%; }
fieldset { border: 1px solid var(--line); border-radius: 6px; }
.shots { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 8px; }
"""


def page(title, body, head=""):
    return ("<!doctype html><html lang=en><head><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>%s</title><style>%s%s</style>%s</head><body>%s</body></html>"
            % (html.escape(title), CSS, EXTRA_CSS, head, body))


class Objects:
    """Content-addressed files: the name is the first 16 hex of the sha256."""

    def __init__(self, folder, base):
        self.folder, self.base, self.listed = folder, base, {}
        folder.mkdir(parents=True, exist_ok=True)

    def put(self, data, ext, kind):
        name = "%s%s" % (hashlib.sha256(data).hexdigest()[:16], ext)
        path = self.folder / name
        if not path.exists():
            path.write_bytes(data)
        self.listed[name] = {"bytes": len(data), "kind": kind}
        return self.base + name


def edge_urls(cfg):
    """The intake URL from agent A's table in the library's ops/edge/README.md:
    its public URL with EDGE_ZONE filled in when the zone is set, its local
    `wrangler dev` URL until then (and publish refuses a page on a local URL)."""
    readme = ROOT / "library" / "ops" / "edge" / "README.md"
    zone = os.environ.get("EDGE_ZONE", "")
    urls = {"intake": "", "from": "no ops/edge/README.md in the library at this pin: no request form"}
    if readme.exists():
        for line in readme.read_text().splitlines():
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0].lower().startswith("intake"):
                public, local = cells[1], cells[2]
                urls["intake"] = public.replace("<zone>", zone) if zone else local
                urls["from"] = "ops/edge/README.md (%s)" % ("zone " + zone if zone else "local, EDGE_ZONE unset")
                break
    return urls


def plate_line(h, plates):
    p = plates.get(h)
    if not p:
        return "plate sha256 %s (not in the library's plates/manifest.json)" % h
    return "plate %s (sha256 %s), %s, licence: %s" % (
        p.get("original_name") or "unnamed", h, p.get("kind") or "?", p.get("licence") or "not recorded")


def attribution(entry, rev, cfg, plates, files):
    sid = entry["key"]
    out = ["%s" % sid,
           "from the asset library, %s, library commit %s" % (cfg["credit"], rev),
           "",
           "Licence: %s" % cfg["licence"],
           "         %s" % cfg["licence_url"],
           "Credit it as: \"%s\" by %s, %s" % (sid, cfg["credit"], cfg["licence"].split("(")[-1].rstrip(")")),
           "",
           "What it rests on (the generator's parameters that are not our own choice,",
           "from its provenance as the bake recorded it):"]
    sourced, chosen = [], 0
    for p in entry.get("parameters", []):
        prov = p.get("provenance", "chosen")
        if prov == "chosen":
            chosen += 1
            continue
        src = str(p.get("source") or "")
        hashes = HEX64.findall(src)
        what = "; ".join(plate_line(h, plates) for h in hashes) if hashes else (src or "no source recorded")
        label = "" if what.lower().startswith(prov) else prov + ": "
        sourced.append("  - %s (%s%s): %s%s" % (
            p.get("name"), json.dumps(p.get("default")), (" " + p["unit"]) if p.get("unit") else "", label, what))
    out += sourced or ["  (none: every parameter is chosen)"]
    out += ["", "%d further parameter(s) are chosen: our own values, with no outside source." % chosen,
            "", "Files in this download:"]
    out += ["  %s" % f for f in files]
    return "\n".join(out) + "\n"


def deterministic_zip(members):
    """members: [(name, bytes)]. Fixed dates and order, so the same bytes give
    the same zip and the same hash."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(members):
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return buf.getvalue()


def facts_of(gid):
    """What the library's committed JSON says about a subject: its ladder
    (class, size, how many rungs, how the ladder ends) and its card (taxon, use)."""
    group, name = gid.split("/", 1)
    base = ROOT / "library" / "generators" / group / name.replace("-", "_")
    lad, card = Path(str(base) + ".ladder.json"), Path(str(base) + ".card.json")
    L = json.loads(lad.read_text()) if lad.exists() else {}
    C = json.loads(card.read_text()) if card.exists() else {}
    rows = [("class", L.get("class")), ("size", "%.2f m" % L["extent_m"] if L.get("extent_m") else None),
            ("rungs", L.get("mesh_rungs")), ("ladder ends", L.get("ladder_end")),
            ("taxon", C.get("taxon")), ("use", C.get("use")), ("rendered as", L.get("authority"))]
    return [(k, v) for k, v in rows if v not in (None, "")]


def sheets_of(run, gid):
    d = run / gid.replace("/", "_")
    return sorted(d.glob("sheet-p*.jpg")) if d.exists() else []


def renders_of(run, gid):
    d = run / gid.replace("/", "_")
    return sorted(p for p in d.glob("*closeup*.png")) if d.exists() else []


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    run = Path(argv[1]).resolve()
    cfg = json.loads((ROOT / "catalog.json").read_text())
    bake_dir = ROOT / "library" / "build" / "artifacts"
    mf = bake_dir / "manifest.json"
    if not mf.exists():
        sys.exit("catalog: no bake at %s -- run tools/bake.sh" % mf)
    bake = json.loads(mf.read_text())
    plates = json.loads((ROOT / "library" / "plates" / "manifest.json").read_text()).get("plates", {})
    rev = subprocess.run(["git", "-C", str(ROOT / "library"), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or "?"
    urls = edge_urls(cfg)
    site = run / "catalog"
    (site / "s").mkdir(parents=True, exist_ok=True)
    base = os.environ.get("CATALOG_ASSET_BASE", "objects/")
    objs = Objects(site / "objects", base)
    rel = lambda u: u if "://" in u else "../" + u   # subject pages live one level down

    cards, missing = [], []
    for e in sorted(bake.get("entries", []), key=lambda e: e["key"]):
        key, gid = e["key"], e.get("generator", e["key"])
        slug = key.replace("/", "_")
        rungs = sorted(e.get("rungs", []), key=lambda r: int(r.get("rung", 0)))
        members, listed, rung0, gaps = [], [], None, []
        for r in rungs:
            g = r.get("gltf") or r.get("file")
            if not g or not (bake_dir / g).exists():
                missing.append("%s r%s: no glTF" % (key, r.get("rung")))
                continue
            data = (bake_dir / g).read_bytes()
            name = "%s/rung%d.glb" % (slug, int(r["rung"]))
            members.append((name, data))
            listed.append("%s  (%s triangles)" % (name, r.get("triangles", "?")))
            if int(r["rung"]) == 0:
                rung0 = objs.put(data, ".glb", "gltf")
            atlas = r.get("atlas_file")
            if r.get("impostor") and not atlas:
                missing.append("%s r%s: an impostor rung with no atlas (it draws untextured)" % (key, r.get("rung")))
                gaps.append("rung %s is an impostor and this bake has no atlas for it: it draws untextured"
                            % r.get("rung"))
            if atlas:
                if (bake_dir / atlas).exists():
                    aname = "%s/%s" % (slug, Path(atlas).name)
                    if aname not in [m[0] for m in members]:
                        members.append((aname, (bake_dir / atlas).read_bytes()))
                        listed.append("%s  (the impostor atlas)" % aname)
                else:
                    missing.append("%s r%s: atlas %s not on disk" % (key, r.get("rung"), atlas))
        if not members:
            continue
        text = attribution(e, rev, cfg, plates, listed + ["ATTRIBUTION.txt"])
        if gaps:
            text += "\nKnown gaps in this download:\n" + "".join("  - %s\n" % g for g in gaps)
        members.append(("ATTRIBUTION.txt", text.encode()))
        # The same file on its own, for the finer builds on itch to carry too.
        (site / "attribution").mkdir(exist_ok=True)
        (site / "attribution" / ("%s.txt" % slug)).write_text(text)
        zipped = deterministic_zip(members)
        zip_url = objs.put(zipped, ".zip", "zip")

        shots = []
        for png in renders_of(run, gid):
            tmp = site / ".shot.jpg"
            small_jpeg(png, tmp)
            shots.append(objs.put(tmp.read_bytes(), ".jpg", "render"))
            tmp.unlink()
        sheets = []
        for jpg in sheets_of(run, gid):
            tmp = site / ".sheet.jpg"
            small_jpeg(jpg, tmp)
            sheets.append(objs.put(tmp.read_bytes(), ".jpg", "sheet"))
            tmp.unlink()
        thumb = ("<img src='%s' alt='%s' loading=lazy>" % (html.escape(shots[0]), html.escape(key))
                 if shots else "<div class=noimg>no render this run</div>")
        cards.append("<div class=card><a href='s/%s.html'>%s</a><h3><a href='s/%s.html'>%s</a></h3>"
                     "<p class=mute>%d rung(s) &middot; %s</p></div>" % (
                         slug, thumb, slug, html.escape(key), len(rungs),
                         "<a href='%s' download='%s.zip'>free download</a>" % (html.escape(zip_url), slug)))

        body = ["<p><a href='../index.html'>&larr; every subject</a></p><h1>%s</h1>" % html.escape(key)]
        if rung0:
            body.append("<model-viewer src='%s' alt='%s, its 1080 rung 0' camera-controls auto-rotate "
                        "shadow-intensity=1 loading=lazy></model-viewer>" % (html.escape(rel(rung0)), html.escape(key)))
        else:
            body.append("<p class=bad>no rung 0 glTF in this bake</p>")
        itch = cfg.get("itch_url", "")
        paid = ("<a class=button href='%s' rel=noopener target=_blank>finer builds: pay what you want on itch</a>"
                % html.escape(itch)) if itch else "<span class=mute>finer builds: pay what you want on itch (the page is not up yet)</span>"
        body.append("<p><a class=button href='%s' download='%s.zip'>free download, the 1080 bake (%d KB)</a>%s</p>" % (
            html.escape(rel(zip_url)), slug, (len(zipped) + 1023) // 1024, paid))
        body.append("<p class=mute>Every rung's glTF of its 1080 ladder%s and ATTRIBUTION.txt, under %s. "
                    "Builds for finer screens are pay-what-you-want on itch, and carry the same attribution file.</p>" % (
                        ", the impostor atlas" if any(r.get("atlas_file") for r in rungs) else "",
                        "<a href='%s'>%s</a>" % (html.escape(cfg["licence_url"]), html.escape(cfg["licence"]))))
        facts = facts_of(gid)
        if facts:
            body.append("<div class=wrap><table>%s</table></div>" % "".join(
                "<tr><th>%s</th><td style='text-align:left'>%s</td></tr>" % (html.escape(k), html.escape(str(v)))
                for k, v in facts))
        for g in gaps:
            body.append("<p class=warn>%s</p>" % html.escape(g))
        if shots:
            body.append("<h2>renders</h2><div class=shots>%s</div>" % "".join(
                "<img src='%s' alt='%s' loading=lazy>" % (html.escape(rel(s)), html.escape(key)) for s in shots))
        if sheets:
            body.append("<h2>its bands</h2><p class=mute>The library's per-band sheet: each band drawn as shipped "
                        "beside the rung derived from rung 0.</p>%s" % "".join(
                "<img src='%s' alt='%s, band sheet' loading=lazy>" % (html.escape(rel(x)), html.escape(key)) for x in sheets))
        body.append("<h2>where it comes from</h2><pre>%s</pre>" % html.escape(text))
        (site / "s" / ("%s.html" % slug)).write_text(page(key, "".join(body), head=(
            "<script type=module src='%s'></script>" % html.escape(cfg["model_viewer"]))))

    sitekey = os.environ.get("TURNSTILE_SITEKEY", "")
    turnstile = ("<div class=cf-turnstile data-sitekey='%s'></div>" % html.escape(sitekey)) if sitekey else ""
    request = (
        "<h2>request a subject</h2>"
        "<p>Missing something? Send a photo and a line about it; requests are read by a person.</p>"
        "<form id=request method=post enctype='multipart/form-data' action='%s'>"
        "<label>What is it? <input name=text required maxlength=2000></label>"
        "<label>A photo (JPEG, PNG or WebP, up to 10 MB) <input name=photo type=file "
        "accept='image/jpeg,image/png,image/webp' required></label>"
        "<label>How to reach you (optional) <input name=contact maxlength=200></label>"
        "<fieldset><legend>I took this photo and grant it under</legend>"
        "<label><input name=licence type=radio value=CC-BY-4.0 required checked> CC BY 4.0 (credit me)</label> "
        "<label><input name=licence type=radio value=CC0-1.0> CC0 (no credit needed)</label></fieldset>"
        "%s<button type=submit>Send the request</button><p id=sent class=mute></p></form>"
        "<script>document.getElementById('request').addEventListener('submit',async e=>{e.preventDefault();"
        "const f=e.target,s=document.getElementById('sent');s.textContent='sending...';"
        "try{const r=await fetch(f.action,{method:'POST',body:new FormData(f)});const t=await r.text();"
        "let j={};try{j=JSON.parse(t)}catch(_){}"
        "s.textContent=r.ok?'Received, thank you.':'Not accepted: '+(j.reason||('HTTP '+r.status));}"
        "catch(x){s.textContent='Could not reach the request desk: '+x.message;}});</script>"
        % (html.escape(urls["intake"]), turnstile)) if urls["intake"] else ""
    head_index = "<script src='https://challenges.cloudflare.com/turnstile/v0/api.js' async defer></script>" if (sitekey and request) else ""
    index = ["<h1>%s</h1><p class=mute>%d subjects, library %s. Every one is a free download "
             "with its attribution file.</p>" % (html.escape(cfg["title"]), len(cards), html.escape(rev)),
             "<div class=grid>%s</div>" % "".join(cards), request]
    (site / "index.html").write_text(page(cfg["title"], "".join(index), head=head_index))
    (site / "objects.json").write_text(json.dumps({"library": rev, "base": base, "edge": urls,
                                                   "objects": objs.listed}, indent=1, sort_keys=True))
    for m in missing:
        print("catalog: GAP %s" % m)
    print("catalog: %d subject(s), %d object(s) (%d KB) in %s; edge URLs from %s" % (
        len(cards), len(objs.listed), sum(o["bytes"] for o in objs.listed.values()) // 1024, site, urls["from"]))


if __name__ == "__main__":
    main(sys.argv)
