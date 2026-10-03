#!/usr/bin/env python3
"""THE CATALOG, the pulse's public half (the-release-infrastructure-this-week,
"The explorer, re-read"): one static page per subject, from the library's
committed JSON and this run's renders, with the 1080 bake as a free download --
the whole offer until itch, the only store, exists for the finer builds.

    tools/catalog.py out/<date>      # writes out/<date>/catalog/

Environment (all optional to build; tools/publish.sh needs them to deploy):
    CATALOG_PUBLIC_BASE  where the objects are served from, ending in / (default
                         `objects/`, beside the pages)
    EDGE_ZONE            the owner's domain: the request form posts to agent A's
                         public intake on it (its local URL until then)
    ITCH_URL             the pay-what-you-want page for the finer builds; empty
                         until the store exists (stage 1), and the pages then
                         read "free at 1080; finer builds soon"
    TURNSTILE_SITEKEY    the intake's Turnstile widget, when set

What it reads, and decides nothing about (the owner's decisions, 2026-10-03):
  - the bake (asset-explorer's tools/bake-library.gd via tools/bake.sh): every
    rung's glTF and, when the bake carries it, the impostor end and its atlas.
    The ladder end is part of the asset: a subject whose committed ladder ends
    in an impostor is offered for download only when its bake carries that rung
    and its atlas, never as an asset missing its end;
  - the library's scorecard (`tools/scorecard.py --json`), for the two numbers
    a public page shows: the draw cost at the 1080 baseline (`src_cost`) and the
    error at the finest band the scorecard counts as covered (`error_px`);
  - the committed JSON: each subject's ladder and card (class, size, rungs, how
    the ladder ends, taxon, use, and `provenance`: plate, contributor, licence),
    `plates/manifest.json` (each plate's name, kind and `licence`), and the
    runtime's licence (`ops/runtime/runtime.toml`, its LICENSE);
  - the run's close-ups (the library's tools/closeup.sh), as the renders.

What it writes: objects/<sha256[:16]>.<ext> (every glTF, atlas, render, zip:
named by content, so an unchanged byte is never uploaded twice), one page per
subject and an index, attribution/<subject>.txt (the file each download carries,
on its own for the itch builds to carry too), and objects.json for publish.
"""
import hashlib
import html
import importlib.util
import json
import os
import subprocess
import sys
import tomllib
import zipfile
import io
from pathlib import Path

# The pulse's own page style and image encoder, from tools/site.py (loaded by
# path: `site` is also the name of a standard-library module).
_spec = importlib.util.spec_from_file_location("pulse_site", Path(__file__).resolve().parent / "site.py")
_site = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_site)
CSS, small_jpeg = _site.CSS, _site.small_jpeg

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
ZIP_DATE = (1980, 1, 1, 0, 0, 0)

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
.nums { display: flex; flex-wrap: wrap; gap: 8px 24px; margin: 8px 0; }
.nums div { min-width: 0; } .nums b { display: block; font-size: 1.2em; font-variant-numeric: tabular-nums; }
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


def edge_urls():
    """The intake URL from agent A's table in the library's ops/edge/README.md:
    its public URL with EDGE_ZONE filled in when the zone is set, its local
    `wrangler dev` URL until then (and publish refuses a page on a local URL)."""
    readme = LIB / "ops" / "edge" / "README.md"
    zone = os.environ.get("EDGE_ZONE", "")
    urls = {"intake": "", "from": "no ops/edge/README.md in the library at this pin: no request form"}
    if readme.exists():
        for line in readme.read_text().splitlines():
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and cells[0].lower().startswith("intake"):
                urls["intake"] = cells[1].replace("<zone>", zone) if zone else cells[2]
                urls["from"] = "ops/edge/README.md (%s)" % ("zone " + zone if zone else "local, EDGE_ZONE unset")
                break
    return urls


def runtime_licence():
    """The open licence of the runtime subset, by name and text, as the library
    names it (ops/runtime/runtime.toml); the pulse chooses none."""
    toml = LIB / "ops" / "runtime" / "runtime.toml"
    if not toml.exists():
        return None, None
    cfg = tomllib.loads(toml.read_text())
    text = LIB / cfg.get("licence_file", "ops/runtime/LICENSE")
    return cfg.get("licence"), (text.read_text() if text.exists() else None)


def committed(gid):
    """A subject's committed ladder and card, by its generator id."""
    group, name = gid.split("/", 1)
    base = LIB / "generators" / group / name.replace("-", "_")
    load = lambda p: json.loads(p.read_text()) if p.exists() else {}
    return load(Path(str(base) + ".ladder.json")), load(Path(str(base) + ".card.json"))


def facts_of(L, C):
    rows = [("class", L.get("class")), ("size", "%.2f m" % L["extent_m"] if L.get("extent_m") else None),
            ("rungs", L.get("mesh_rungs")), ("ladder ends", L.get("ladder_end")),
            ("taxon", C.get("taxon")), ("use", C.get("use"))]
    return [(k, v) for k, v in rows if v not in (None, "")]


def two_numbers(row):
    """The draw cost at the 1080 baseline and the error at the finest band the
    scorecard counts as covered: the library's numbers, picked, never computed."""
    if not row:
        return None, None
    covered = [b for b in row.get("bands", []) if b.get("covered")]
    finest = min(covered, key=lambda b: b["band"]) if covered else None
    return row.get("src_cost"), (finest["band"], finest.get("error_px")) if finest else None


def attribution(key, gid, rev, licence, C, plates, files):
    """ATTRIBUTION.txt in the library's own form (tools/attribution.gd): the
    plates the subject's card cites, each with its name, kind, contributor and
    licence from plates/manifest.json."""
    out = ["ATTRIBUTION -- %s, from the asset-generators library" % key,
           "",
           "Generated by asset-pulse from the library's provenance at commit %s." % rev,
           "Never edited by hand: regenerate it.",
           "",
           "The files in this download are under the %s licence in LICENSE," % (licence or "library's"),
           "the open licence of the library's runtime subset.",
           "",
           "%s rests on the plates listed below: photographs, drawings and traced" % gid,
           "outlines the library measured. No plate's bytes are in this download; each",
           "is cited by sha256. Credit the contributors under each plate's licence.",
           ""]
    rows = C.get("provenance") or []
    if not rows:
        out.append("  no plate cited")
    for row in sorted(rows, key=lambda r: r.get("plate", "")):
        h = row.get("plate", "")
        p = plates.get(h, {})
        out.append("  plate %s  %s  %s  contributed by %s  licence: %s" % (
            h[:12], p.get("original_name") or "?", p.get("kind") or "?",
            row.get("contributed_by") or p.get("contributed_by") or "?",
            p.get("licence") or row.get("licence") or "?"))
    out += ["", "Files in this download:"] + ["  %s" % f for f in files]
    return "\n".join(out) + "\n"


def deterministic_zip(members):
    """Fixed dates and order: the same bytes give the same zip and hash."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(members):
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return buf.getvalue()


def renders_of(run, gid):
    d = run / gid.replace("/", "_")
    return sorted(d.glob("*closeup*.png")) if d.exists() else []


def scorecard_rows():
    r = subprocess.run([sys.executable, "tools/scorecard.py", "--json"], cwd=LIB, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip().startswith("{"):
        return {}
    d = json.loads(r.stdout)
    return {s["id"]: s for s in d.get("subjects", [])} if isinstance(d.get("subjects"), list) else {}


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    run = Path(argv[1]).resolve()
    cfg = json.loads((ROOT / "catalog.json").read_text())
    bake_dir = LIB / "build" / "artifacts"
    if not (bake_dir / "manifest.json").exists():
        sys.exit("catalog: no bake at %s -- run tools/bake.sh" % bake_dir)
    bake = json.loads((bake_dir / "manifest.json").read_text())
    plates = json.loads((LIB / "plates" / "manifest.json").read_text()).get("plates", {})
    rev = subprocess.run(["git", "-C", str(LIB), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True).stdout.strip() or "?"
    licence, licence_text = runtime_licence()
    scores = scorecard_rows()
    urls = edge_urls()
    itch = os.environ.get("ITCH_URL", "")
    site = run / "catalog"
    (site / "s").mkdir(parents=True, exist_ok=True)
    (site / "attribution").mkdir(exist_ok=True)
    objs = Objects(site / "objects", os.environ.get("CATALOG_PUBLIC_BASE", "objects/"))
    rel = lambda u: u if "://" in u else "../" + u   # subject pages live one level down

    cards, gaps_all = [], []
    for e in sorted(bake.get("entries", []), key=lambda e: e["key"]):
        key, gid = e["key"], e.get("generator", e["key"])
        slug = key.replace("/", "_")
        L, C = committed(gid)
        rungs = sorted(e.get("rungs", []), key=lambda r: int(r.get("rung", 0)))
        members, listed, rung0, gaps = [], [], None, []
        for r in rungs:
            g = r.get("gltf") or r.get("file")
            if not g or not (bake_dir / g).exists():
                gaps.append("rung %s: no glTF in this bake" % r.get("rung"))
                continue
            data = (bake_dir / g).read_bytes()
            name = "%s/rung%d.glb" % (slug, int(r["rung"]))
            members.append((name, data))
            listed.append("%s  (%s triangles%s)" % (name, r.get("triangles", "?"), ", the impostor" if r.get("impostor") else ""))
            if int(r["rung"]) == 0:
                rung0 = objs.put(data, ".glb", "gltf")
            if r.get("impostor"):
                atlas = r.get("atlas_file")
                if atlas and (bake_dir / atlas).exists():
                    members.append(("%s/%s" % (slug, Path(atlas).name), (bake_dir / atlas).read_bytes()))
                    listed.append("%s/%s  (the impostor's atlas)" % (slug, Path(atlas).name))
                else:
                    gaps.append("rung %s is the impostor and this bake has no atlas for it" % r.get("rung"))
        # THE LADDER END IS PART OF THE ASSET (the owner, 2026-10-03).
        if L.get("ladder_end") == "impostor" and not any(
                r.get("impostor") and r.get("atlas_file") for r in rungs):
            gaps.append("its ladder ends in an impostor, and this bake does not carry the impostor rung with its atlas")
        offered = bool(members) and not gaps
        text = attribution(key, gid, rev, licence, C, plates,
                           [m.split("  ")[0] for m in listed] + ["ATTRIBUTION.txt"] + (["LICENSE"] if licence_text else []))
        (site / "attribution" / ("%s.txt" % slug)).write_text(text)
        zip_url, zipped = None, b""
        if offered:
            members.append(("ATTRIBUTION.txt", text.encode()))
            if licence_text:
                members.append(("LICENSE", licence_text.encode()))
            zipped = deterministic_zip(members)
            zip_url = objs.put(zipped, ".zip", "zip")
        else:
            gaps_all += ["%s: %s" % (key, g) for g in gaps]

        shots = []
        for png in renders_of(run, gid):
            tmp = site / ".shot.jpg"
            small_jpeg(png, tmp)
            shots.append(objs.put(tmp.read_bytes(), ".jpg", "render"))
            tmp.unlink()
        thumb = ("<img src='%s' alt='%s' loading=lazy>" % (html.escape(shots[0]), html.escape(key))
                 if shots else "<div class=noimg>no render this run</div>")
        dl = ("<a href='%s' download='%s.zip'>free download</a>" % (html.escape(zip_url), slug)
              if zip_url else "<span>download waits on its impostor</span>")
        cards.append("<div class=card><a href='s/%s.html'>%s</a><h3><a href='s/%s.html'>%s</a></h3>"
                     "<p class=mute>%d rung(s) &middot; %s</p></div>" % (slug, thumb, slug, html.escape(key), len(rungs), dl))

        body = ["<p><a href='../index.html'>&larr; every subject</a></p><h1>%s</h1>" % html.escape(key)]
        if rung0:
            body.append("<model-viewer src='%s' alt='%s, its 1080 rung 0' camera-controls auto-rotate "
                        "shadow-intensity=1 loading=lazy></model-viewer>" % (html.escape(rel(rung0)), html.escape(key)))
        # THE TWO NUMBERS (the owner, 2026-10-03), the scorecard's, for the
        # generator's default build.
        cost, err = two_numbers(scores.get(gid))
        default = key == gid.replace("/", "-")
        if cost is not None:
            body.append("<div class=nums><div>draw cost at the 1080 baseline<b>%s</b></div>"
                        "<div>error at the finest affordable band<b>%s</b></div></div>%s" % (
                            "{:,}".format(cost),
                            ("%.1f px (band %d)" % (err[1], err[0])) if err and err[1] is not None else "no band affordable",
                            "" if default else "<p class=mute>for %s's default build; this is a variant of it</p>" % html.escape(gid)))
        # THE STORE IS ITCH AND ONLY ITCH, and it does not exist until stage 1's
        # number holds (the-release-infrastructure-this-week, revised
        # 2026-10-03): an empty ITCH_URL reads as the plan's own words.
        paid = ("<a class=button href='%s' rel=noopener target=_blank>finer builds: pay what you want on itch</a>"
                % html.escape(itch)) if itch else "<span class=mute>free at 1080; finer builds soon</span>"
        if zip_url:
            body.append("<p><a class=button href='%s' download='%s.zip'>free download, the 1080 bake (%d KB)</a>%s</p>" % (
                html.escape(rel(zip_url)), slug, (len(zipped) + 1023) // 1024, paid))
            body.append("<p class=mute>Every rung's glTF of its 1080 ladder%s, ATTRIBUTION.txt and the %s LICENSE.%s</p>" % (
                            " down to its impostor and atlas" if L.get("ladder_end") == "impostor" else "",
                            html.escape(licence or "library's"),
                            " Builds for finer screens are pay-what-you-want on itch and carry the same attribution."
                            if itch else ""))
        else:
            body.append("<p class=warn>No download yet: %s. The ladder's end is part of the asset, so it is not "
                        "offered without it.</p><p>%s</p>" % (html.escape("; ".join(gaps)), paid))
        facts = facts_of(L, C)
        if facts:
            body.append("<div class=wrap><table>%s</table></div>" % "".join(
                "<tr><th>%s</th><td style='text-align:left'>%s</td></tr>" % (html.escape(k), html.escape(str(v)))
                for k, v in facts))
        if shots:
            body.append("<h2>renders</h2><div class=shots>%s</div>" % "".join(
                "<img src='%s' alt='%s' loading=lazy>" % (html.escape(rel(s)), html.escape(key)) for s in shots))
        body.append("<h2>credits</h2><pre>%s</pre>" % html.escape(text))
        (site / "s" / ("%s.html" % slug)).write_text(page(key, "".join(body), head=(
            "<script type=module src='%s'></script>" % html.escape(cfg["model_viewer"]))))

    sitekey = os.environ.get("TURNSTILE_SITEKEY", "")
    request = (
        "<h2>request a subject</h2>"
        "<p>Missing something? Send a photo and a line about it; requests are read by a person.</p>"
        "<form id=request method=post enctype='multipart/form-data' action='%s'>"
        "<label>What is it? <input name=text required maxlength=2000></label>"
        "<label>A photo (JPEG, PNG or WebP, up to 10 MB) <input name=photo type=file "
        "accept='image/jpeg,image/png,image/webp' required></label>"
        "<label>How to credit you (optional) <input name=contributed_by maxlength=200></label>"
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
        % (html.escape(urls["intake"]),
           ("<div class=cf-turnstile data-sitekey='%s'></div>" % html.escape(sitekey)) if sitekey else "")
    ) if urls["intake"] else ""
    head_index = ("<script src='https://challenges.cloudflare.com/turnstile/v0/api.js' async defer></script>"
                  if (sitekey and request) else "")
    offered = sum(1 for c in cards if "free download" in c)
    index = ["<h1>%s</h1><p class=mute>%d subjects, library %s; %d free to download with their attribution "
             "file.</p>" % (html.escape(cfg["title"]), len(cards), html.escape(rev), offered),
             "<div class=grid>%s</div>" % "".join(cards), request]
    (site / "index.html").write_text(page(cfg["title"], "".join(index), head=head_index))
    (site / "objects.json").write_text(json.dumps({"library": rev, "base": objs.base, "edge": urls, "itch": itch,
                                                   "objects": objs.listed}, indent=1, sort_keys=True))
    for g in gaps_all:
        print("catalog: GAP %s" % g)
    print("catalog: %d subject(s), %d with a download, %d object(s) (%d KB) in %s; intake from %s; itch %s" % (
        len(cards), offered, len(objs.listed), sum(o["bytes"] for o in objs.listed.values()) // 1024, site,
        urls["from"], "set" if itch else "unset"))


if __name__ == "__main__":
    main(sys.argv)
