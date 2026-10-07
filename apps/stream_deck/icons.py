"""Make original key tiles and preserve operator or real application artwork.

Pillow is optional. SVG output remains usable when it is unavailable; raster
art is embedded in the SVG rather than replaced with an approximation.
"""

from __future__ import annotations

import base64
import io
import os
import re
import subprocess
import tempfile
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError:
    Image = ImageDraw = ImageFont = ImageOps = None

SIZE = 144
PERSONAL_IDS = frozenset({
    "velour_youtube", "velour_core_international", "bandcamp", "soundcloud",
    "fourthwall", "vandal_bot", "calen_bot", "music_ground",
})
SLATE = "#263445"
WHITE = "#FFFFFF"
INK = "#17212D"
MAX_DOWNLOAD = 2 * 1024 * 1024
_cache: dict[tuple[str, str], tuple[bytes | None, str, str]] = {}
_missing_pillow_reported = False


def reset_cache() -> None:
    """Start a fresh generation run without retaining an earlier icon fetch."""
    global _missing_pillow_reported
    _cache.clear()
    _missing_pillow_reported = False


def _pillow_notice() -> None:
    global _missing_pillow_reported
    if Image is None and not _missing_pillow_reported:
        print("Pillow is unavailable; writing SVG icons only.")
        _missing_pillow_reported = True


def _font(size: int):
    if ImageFont is None:
        return None
    font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for filename in ("segoeuib.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(str(font_dir / filename), size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Older supported Pillow releases.
        return ImageFont.load_default()


def _rgb(colour: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", colour):
        colour = SLATE
    return tuple(int(colour[index:index + 2], 16) for index in (1, 3, 5))


def _lighter(colour: str) -> str:
    return "#" + "".join(f"{round(value + (255 - value) * .42):02X}" for value in _rgb(colour))


class _Canvas:
    """The same basic shapes are sent to both renderers."""

    def __init__(self, background: str):
        self.parts = [
            ('<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144" '
             'viewBox="0 0 144 144">'),
            f'<rect width="144" height="144" fill="{background}"/>',
        ]
        self.image = Image.new("RGB", (SIZE, SIZE), background) if Image else None
        self.draw = ImageDraw.Draw(self.image) if ImageDraw and self.image else None

    def rect(self, box, fill: str, outline: str | None = None, width: int = 3):
        x1, y1, x2, y2 = box
        self.parts.append(
            f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" '
            f'fill="{fill}" stroke="{outline or "none"}" stroke-width="{width}"/>'
        )
        if self.draw:
            self.draw.rectangle(box, fill=None if fill == "none" else fill,
                                outline=outline, width=width)

    def line(self, points, fill: str, width: int = 4):
        self.parts.append(
            f'<polyline points="{" ".join(f"{x},{y}" for x, y in points)}" '
            f'fill="none" stroke="{fill}" stroke-width="{width}" '
            'stroke-linecap="round" stroke-linejoin="round"/>'
        )
        if self.draw:
            self.draw.line(points, fill=fill, width=width, joint="curve")

    def polygon(self, points, fill: str):
        self.parts.append(
            f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}" fill="{fill}"/>'
        )
        if self.draw:
            self.draw.polygon(points, fill=fill)

    def circle(self, centre, radius: int, fill: str, outline: str | None = None, width=3):
        x, y = centre
        self.parts.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" '
            f'stroke="{outline or "none"}" stroke-width="{width}"/>'
        )
        if self.draw:
            self.draw.ellipse((x-radius, y-radius, x+radius, y+radius),
                              fill=None if fill == "none" else fill, outline=outline, width=width)

    def text(self, value: str, y: int, size: int, fill: str = WHITE):
        self.parts.append(
            f'<text x="72" y="{y}" text-anchor="middle" '
            f'font-family="Segoe UI,Arial,sans-serif" font-weight="600" '
            f'font-size="{size}" fill="{fill}">{escape(value)}</text>'
        )
        if self.draw:
            self.draw.text((72, y), value, font=_font(size), fill=fill, anchor="ms")

    def save(self, stem: Path) -> str:
        stem.with_suffix(".svg").write_text("".join(self.parts) + "</svg>", encoding="utf-8")
        if self.image:
            self.image.save(stem.with_suffix(".png"), format="PNG")
            return stem.with_suffix(".png").name
        return stem.with_suffix(".svg").name


def _lines(title: str, limit: int = 13) -> list[str]:
    """Wrap a compact key label without dropping any words."""
    lines: list[str] = []
    line = ""
    for word in title.split():
        if line and len(line) + len(word) + 1 > limit:
            lines.append(line)
            line = ""
        line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines or [""]


def _label(canvas: _Canvas, title: str, y=105, size=19, fill=WHITE, limit=13):
    lines = _lines(title, limit)
    if len(lines) > 2:
        size = min(size, 15)
        y = min(y, 97)
    for index, line in enumerate(lines):
        text_size = min(size, max(9, int(126 / max(len(line), 1) * 1.8)))
        canvas.text(line, y + index * (size + 3), text_size, fill)


def _glyph(canvas: _Canvas, key: dict, colour=WHITE):
    key_id = str(key.get("id", "")).lower()
    title = str(key.get("title", "")).lower()
    kind = key.get("kind")
    name = f"{key_id} {title}"
    if kind == "back" or key_id == "back":
        canvas.line([(101, 54), (43, 54), (65, 32)], colour, 6)
        canvas.line([(43, 54), (65, 76)], colour, 6)
    elif "ground" in name:
        canvas.line([(41, 51), (72, 27), (103, 51)], colour, 5)
        canvas.line([(48, 49), (48, 80), (96, 80), (96, 49)], colour, 4)
        canvas.rect((66, 61, 79, 80), colour)
    elif "plan" in name or "it's in" in name or "its_in" in name:
        canvas.rect((51, 29, 93, 80), "none", colour, 4)
        for y in (44, 55, 66):
            canvas.line([(60, y), (84, y)], colour, 3)
    elif "dictation" in name:
        canvas.rect((63, 26, 81, 60), "none", colour, 4)
        canvas.line([(54, 51), (54, 65), (62, 72), (82, 72), (90, 65), (90, 51)], colour)
        canvas.line([(72, 73), (72, 83)], colour)
        canvas.line([(61, 83), (83, 83)], colour)
    elif "screenshot" in name:
        for points in (
            [(42, 48), (42, 34), (57, 34)], [(87, 34), (102, 34), (102, 48)],
            [(42, 64), (42, 78), (57, 78)], [(87, 78), (102, 78), (102, 64)],
        ):
            canvas.line(points, colour)
        canvas.circle((72, 56), 11, "none", colour)
    elif "clipboard" in name:
        canvas.rect((51, 36, 93, 82), "none", colour, 4)
        canvas.rect((61, 29, 83, 42), SLATE, colour, 3)
    elif "session" in name or "reset" in name:
        canvas.circle((72, 56), 23, "none", colour, 4)
        canvas.line([(72, 41), (72, 71)], colour)
        canvas.line([(57, 56), (87, 56)], colour)
    elif "start" in name and "table" in name:
        canvas.polygon([(61, 32), (61, 80), (94, 56)], colour)
    elif kind == "switch":
        canvas.line([(42, 45), (100, 45), (86, 31)], colour)
        canvas.line([(100, 67), (42, 67), (56, 81)], colour)
    elif kind == "folder" or "current" in name or "more" in name:
        canvas.line([(42, 79), (42, 36), (65, 36), (73, 45), (101, 45),
                     (101, 79), (42, 79)], colour)
    else:
        # A neutral destination glyph, never a recreation of a service's logo.
        canvas.rect((47, 35, 96, 80), "none", colour, 4)
        canvas.line([(59, 68), (89, 41), (89, 57)], colour)
        canvas.line([(73, 41), (89, 41)], colour)


def _tile(key: dict, stem: Path, style: str) -> str:
    title = str(key.get("title") or key.get("id") or "Key")
    if style == "needs_art":
        canvas = _Canvas("#FF00D4")
        canvas.text("NEEDS ART", 46, 20, "#000000")
        _label(canvas, title, 88, 16, "#000000")
    elif style == "reserved":
        canvas = _Canvas(SLATE)
        _label(canvas, title, 44, 19)
        canvas.rect((0, 96, 144, 144), "#FFCC00")
        for offset in range(-48, 192, 30):
            canvas.polygon([(offset, 96), (offset+15, 96),
                            (offset-33, 144), (offset-48, 144)], "#111111")
    elif style == "ask":
        colour = str(key.get("color", key.get("colour", SLATE)))
        colour = colour if re.fullmatch(r"#[0-9a-fA-F]{6}", colour) else SLATE
        canvas = _Canvas(colour)
        canvas.rect((0, 0, 7, 144), _lighter(colour))
        _label(canvas, str(key.get("display_name") or title), 81, 25, limit=12)
    elif style == "website":
        canvas = _Canvas(SLATE)
        initial = next((letter.upper() for letter in title if letter.isalnum()), "?")
        canvas.text(initial, 74, 48, WHITE)
        _label(canvas, title, 108, 18, WHITE)
    elif style == "stop":
        canvas = _Canvas(WHITE)
        canvas.text("STOP", 85, 31, INK)
    else:
        background = str(key.get("color", key.get("colour", "#FFA050"))) \
            if style == "start" else SLATE
        canvas = _Canvas(background)
        _glyph(canvas, key)
        _label(canvas, title)
    return canvas.save(stem)


def _embedded_svg(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        'width="144" height="144" viewBox="0 0 144 144">'
        f'<image width="144" height="144" preserveAspectRatio="xMidYMid meet" '
        f'xlink:href="data:{mime};base64,{encoded}"/></svg>'
    )


def _raster_bytes(data: bytes) -> bytes:
    """Decode only real raster artwork, retaining aspect ratio and transparency."""
    if Image is None:
        return data
    with Image.open(io.BytesIO(data)) as source:
        source.load()
        artwork = ImageOps.contain(source.convert("RGBA"), (SIZE, SIZE), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    result.alpha_composite(artwork, ((SIZE-artwork.width)//2, (SIZE-artwork.height)//2))
    encoded = io.BytesIO()
    result.save(encoded, format="PNG")
    return encoded.getvalue()


def _write_art(data: bytes, stem: Path, mime="image/png") -> str:
    if Image is not None and mime != "image/svg+xml":
        data = _raster_bytes(data)
        stem.with_suffix(".png").write_bytes(data)
        mime = "image/png"
        image_name = stem.with_suffix(".png").name
    else:
        image_name = stem.with_suffix(".svg").name
    stem.with_suffix(".svg").write_text(_embedded_svg(data, mime), encoding="utf-8")
    return image_name


def _custom(key_id: str, directories: list[Path]) -> Path | None:
    # A key id is an identifier, never a path supplied to this module.
    if not re.fullmatch(r"[A-Za-z0-9_-]+", key_id):
        return None
    for directory in directories:
        # Match the written filename exactly, including on Windows. A supplied
        # Stop.png from another icon collection must not become the stop key's
        # custom stop.png merely because the filesystem ignores case.
        try:
            names = {entry.name: entry for entry in Path(directory).iterdir() if entry.is_file()}
        except OSError:
            continue
        for extension in (".png", ".svg"):
            candidate = names.get(key_id + extension)
            if candidate is not None:
                return candidate
    return None


class _IconLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        rel = str(attrs.get("rel", "")).lower().split()
        href = attrs.get("href")
        if tag.lower() != "link" or not href or not any("icon" in token for token in rel):
            return
        if "mask-icon" in rel or str(attrs.get("type", "")).lower() == "image/svg+xml":
            return
        sizes = [int(size) for size in re.findall(r"(\d+)x\d+", str(attrs.get("sizes") or ""))]
        score = max(sizes, default=180 if "apple-touch-icon" in rel else 32)
        self.links.append((score, href))


def _download(url: str) -> tuple[bytes, str]:
    if urlsplit(url).scheme not in {"http", "https"}:
        raise ValueError("Icon address must use HTTP or HTTPS")
    request = Request(url, headers={"User-Agent": "SecondSignal-StreamDeck/1.0"})
    with urlopen(request, timeout=5) as response:
        data = response.read(MAX_DOWNLOAD + 1)
        if len(data) > MAX_DOWNLOAD:
            raise ValueError("Icon exceeds the two-megabyte download limit")
        return data, response.geturl()


def _website_icon(target: str) -> tuple[bytes | None, str, str]:
    parts = urlsplit(target)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None, "", "Website target is not an HTTP or HTTPS address"
    # Local Table pages have original utility tiles; never query an icon service
    # with an address from the operator's own computer.
    if parts.hostname in {"localhost", "127.0.0.1", "::1"}:
        return None, "", "Local Table page uses a generated utility tile"
    root = f"{parts.scheme}://{parts.netloc}/"
    cache_key = ("website", root)
    if cache_key in _cache:
        return _cache[cache_key]
    candidates: list[str] = []
    try:
        markup, final_url = _download(root)
        parser = _IconLinks()
        parser.feed(markup.decode("utf-8", errors="replace"))
        candidates.extend(urljoin(final_url, link) for _, link in sorted(parser.links, reverse=True))
    except (OSError, ValueError, URLError):
        pass
    candidates.extend([urljoin(root, "apple-touch-icon.png"), urljoin(root, "favicon.ico")])
    candidates = list(dict.fromkeys(candidates))[:4]
    google = "https://www.google.com/s2/favicons?" + urlencode({"domain": parts.hostname, "sz": 128})
    candidates.append(google)
    small: tuple[bytes | None, str, str] | None = None
    for candidate in candidates:
        if urlsplit(candidate).path.lower().endswith(".svg"):
            continue
        try:
            data, final_url = _download(candidate)
            with Image.open(io.BytesIO(data)) as decoded:
                decoded.load()
                largest = max(decoded.size)
                # ICO files can hold more than one rendition.
                if decoded.format == "ICO" and hasattr(decoded, "ico"):
                    dimensions = max(decoded.ico.sizes(), key=lambda dimensions: dimensions[0])
                    if dimensions[0] > largest:
                        frame = decoded.ico.getimage(dimensions)
                        buffer = io.BytesIO()
                        frame.save(buffer, format="PNG")
                        data, largest = buffer.getvalue(), dimensions[0]
            found = (data, final_url, "")
            if largest >= 128:
                _cache[cache_key] = found
                return found
            small = small or found
        except (OSError, ValueError, URLError, Image.DecompressionBombError):
            continue
    result = small or (None, "", "The site and favicon service supplied no readable raster icon")
    _cache[cache_key] = result
    return result


def _program_icon(target: str, scratch: Path) -> tuple[bytes | None, str, str]:
    cache_key = ("program", target)
    if cache_key in _cache:
        return _cache[cache_key]
    if os.name != "nt":
        return None, "", "Program icon extraction requires Windows"
    if not Path(target).is_file():
        return None, "", "Program icon target does not exist"
    result: tuple[bytes | None, str, str]
    try:
        with tempfile.TemporaryDirectory(prefix="icon-", dir=scratch) as temp_dir:
            output = Path(temp_dir) / "program.png"
            # Use encoded PowerShell, with literal-string escaping. No terminal
            # or visible process window is opened for icon extraction.
            source_literal = target.replace("'", "''")
            output_literal = str(output).replace("'", "''")
            script = (
                "$ErrorActionPreference='Stop'; Add-Type -AssemblyName System.Drawing; "
                f"$iconSource='{source_literal}'; "
                "if ([IO.Path]::GetExtension($iconSource) -ieq '.lnk') { "
                "$shortcut=(New-Object -ComObject WScript.Shell).CreateShortcut($iconSource); "
                "if ($shortcut.TargetPath) { $iconSource=$shortcut.TargetPath }; "
                # A Chrome-installed app launches a shared executable but its
                # shortcut carries that app's own artwork. Split only a final
                # comma followed by an integer, preserving commas in paths.
                "$iconLocation=[Environment]::ExpandEnvironmentVariables("
                "[string]$shortcut.IconLocation).Trim(); "
                "if ($iconLocation -match '^(.*),\\s*(-?\\d+)\\s*$') { "
                "$iconLocation=$Matches[1] }; "
                "$iconLocation=$iconLocation.Trim().Trim('\"'); "
                "if ($iconLocation -and (Test-Path -LiteralPath $iconLocation -PathType Leaf)) { "
                "$iconSource=$iconLocation } }; "
                "if ([IO.Path]::GetExtension($iconSource) -ieq '.ico') { "
                "$icon=[Drawing.Icon]::new($iconSource) "
                "} else { $icon=[Drawing.Icon]::ExtractAssociatedIcon($iconSource) }; "
                "if ($null -eq $icon) { throw 'No associated icon' }; "
                "$bitmap=$icon.ToBitmap(); "
                f"$bitmap.Save('{output_literal}',[Drawing.Imaging.ImageFormat]::Png); "
                "$bitmap.Dispose(); $icon.Dispose()"
            )
            encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                 "-EncodedCommand", encoded], check=True, timeout=15,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            result = (output.read_bytes(), target, "")
    except (OSError, subprocess.SubprocessError):
        result = (None, "", "Windows could not extract a program icon")
    _cache[cache_key] = result
    return result


def render_icon(
    key: dict, image_stem: Path, *, offline: bool = False,
    custom_dirs: list[Path] | None = None,
) -> dict:
    """Write a 144px key image, an SVG companion, and return its provenance.

    ``image`` is a basename for the page's Images directory. ``source`` is
    operator, website, program, generated, or needs_art. ``fallback`` explains
    every unavailable external image. SVG-only custom art stays SVG because
    Pillow cannot rasterize SVG; a matching PNG can be supplied alongside it.
    No artwork from a reference profile is ever read by this module.
    """
    _pillow_notice()
    image_stem = Path(image_stem)
    image_stem.parent.mkdir(parents=True, exist_ok=True)
    key_id = str(key.get("id", ""))
    kind = key.get("kind", "reserved")
    target = str(key.get("icon_target") or key.get("target") or "")
    unresolved = str(key.get("target", "")).startswith("PLACEHOLDER:")
    directories = list(custom_dirs or [])
    own = _custom("reserved" if kind == "reserved" or unresolved else key_id, directories)
    report = {"image": "", "source": "generated", "needs_art": False}
    if own:
        mime = "image/svg+xml" if own.suffix.lower() == ".svg" else "image/png"
        try:
            report.update(image=_write_art(own.read_bytes(), image_stem, mime),
                          source="operator", source_file=str(own))
            if mime == "image/svg+xml" and Image is not None:
                report["fallback"] = "Custom SVG preserved; Pillow does not rasterize SVG"
            larger = own.with_name(own.stem + "@2x.png")
            if larger.is_file():
                report["source_2x"] = str(larger)
                report["larger_image"] = "Preserved in custom; this profile format uses 144px images"
            return report
        except (OSError, ValueError):
            report["fallback"] = "The matching custom artwork could not be read"
    if kind == "reserved" or unresolved:
        report["image"] = _tile(key, image_stem, "reserved")
        report["generated_style"] = "reserved"
        return report
    if key_id in PERSONAL_IDS:
        report.update(image=_tile(key, image_stem, "needs_art"), source="needs_art", needs_art=True)
        report["fallback"] = report.get("fallback", "Personal artwork is missing")
        return report
    title = str(key.get("title", "")).lower()
    style = "utility"
    if kind == "ask":
        style = "ask"
    elif key_id == "stop" or title == "stop":
        style = "stop"
    elif ("start" in key_id and "table" in key_id) or title == "start the table":
        style = "start"
    utility = style != "utility" or kind not in {"website", "open"} or any(
        token in key_id for token in ("ground", "plan", "current_push", "new_session", "reset")
    )
    if not utility:
        external_kind = "website" if kind == "website" else "program"
        program_candidate = Path(target).suffix.lower() in {".exe", ".lnk", ".appref-ms"}
        if kind == "website" or program_candidate:
            if offline and kind == "website":
                report["fallback"] = f"Offline: {external_kind} icon retrieval skipped"
            elif Image is None:
                report["fallback"] = f"Pillow unavailable: {external_kind} icon decoding skipped"
            else:
                data, source, reason = _website_icon(target) if kind == "website" \
                    else _program_icon(target, image_stem.parent)
                if data:
                    try:
                        report.update(image=_write_art(data, image_stem), source=external_kind)
                        report["source_url" if kind == "website" else "source_file"] = source
                        return report
                    except (OSError, ValueError):
                        reason = "The real icon could not be decoded"
                report["fallback"] = reason
    if style == "utility" and kind == "website":
        style = "website"
    report["image"] = _tile(key, image_stem, style)
    report["generated_style"] = style
    return report
