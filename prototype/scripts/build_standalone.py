"""Create one self-contained, network-independent HTML entry point from source assets."""
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1] / "dist"


def read_utf8(path):
    # Preserve CRLF as well as LF so downloaded files retain their recorded hash.
    return path.read_bytes().decode("utf-8")


def script_json(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def main():
    embedded = {"./data/"+p.name: read_utf8(p) for p in sorted((ROOT / "data").glob("*.json"))}
    files = {p.name: read_utf8(p) for p in sorted((ROOT / "research").iterdir()) if p.is_file()}
    files["schema.md"] = read_utf8(ROOT / "schema.md")
    css = (ROOT / "style.css").read_text()
    engine = re.sub(r"(?m)^export ", "", (ROOT / "lib" / "engine.mjs").read_text())
    app = re.sub(r"(?m)^import .* from .*;\n", "", (ROOT / "app.mjs").read_text())
    script = "window.__SEVA_EMBEDDED__="+script_json(embedded)+";\nwindow.__SEVA_FILES__="+script_json(files)+";\n"+engine+"\n"+app
    assert "</script" not in script.lower(), "Embedded script contains an unsafe closing tag."
    html = (ROOT / "index.html").read_text()
    favicon = "data:image/svg+xml,"+quote((ROOT / "favicon.svg").read_text())
    html = html.replace('href="./favicon.svg"', 'href="'+favicon+'"')
    html = html.replace('<link rel="stylesheet" href="./style.css">', '<style>'+css+'</style>')
    html = html.replace('<script type="module" src="./app.mjs"></script>', '<script type="module">'+script+'</script>')
    (ROOT / "standalone.html").write_text(html)
    print(f"Built standalone.html: {len(html.encode('utf-8')):,} bytes; {len(files)} embedded documents; no external runtime assets.")


if __name__ == "__main__":
    main()
