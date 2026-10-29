"""Set Windows folder icons from Nerd Fonts glyphs.

    python nficons.py            # render icons and apply folders.txt
    python nficons.py --undo     # remove icons set by this tool
    python nficons.py --plain    # bare glyph instead of folder + glyph

folders.txt lines: <glyph-name> <#color> <folder path>
Glyph names are nerd-fonts glyphnames.json keys without the "nf-" prefix
(browse https://www.nerdfonts.com/cheat-sheet).
"""
import ctypes, io, json, os, subprocess, sys, urllib.request, zipfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ICONS = os.path.join(HERE, "icons")
CACHE = os.path.join(HERE, "cache")
FONT = os.path.join(CACHE, "SymbolsNerdFont-Regular.ttf")
NAMES = os.path.join(CACHE, "glyphnames.json")
FONT_URL = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip"
NAMES_URL = "https://raw.githubusercontent.com/ryanoasis/nerd-fonts/master/glyphnames.json"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

HIDDEN, SYSTEM, READONLY = 0x2, 0x4, 0x1
k32 = ctypes.windll.kernel32


def fetch():
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.exists(FONT):
        data = urllib.request.urlopen(FONT_URL).read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            open(FONT, "wb").write(z.read(os.path.basename(FONT)))
    if not os.path.exists(NAMES):
        urllib.request.urlretrieve(NAMES_URL, NAMES)
    names = json.load(open(NAMES, encoding="utf-8"))
    names.pop("METADATA", None)
    return names


def read_mapping(path):
    for n, line in enumerate(open(path, encoding="utf-8-sig"), 1):  # -sig: Notepad/PowerShell add a BOM
        line = line.strip()
        if line and not line.startswith("#"):
            glyph, color, folder = line.split(maxsplit=2)
            yield n, glyph, color, folder


def glyph_img(font, ch, color, box):
    """Glyph cropped to its ink and scaled to fit a box x box square."""
    im = Image.new("RGBA", (1200, 1200))
    ImageDraw.Draw(im).text((100, 100), ch, font=font, fill=color)
    im = im.crop(im.getbbox())
    im.thumbnail((box, box), Image.LANCZOS)
    return im


def render(font, names, glyph, color, plain):
    out = os.path.join(ICONS, f"{glyph}_{color.lstrip('#')}{'_plain' if plain else ''}.ico")
    if os.path.exists(out):
        return out
    ch = chr(int(names[glyph]["code"], 16))
    canvas = Image.new("RGBA", (256, 256))
    if plain:
        g = glyph_img(font, ch, color, 240)
        canvas.alpha_composite(g, ((256 - g.width) // 2, (256 - g.height) // 2))
    else:
        f = glyph_img(font, chr(int(names["md-folder"]["code"], 16)), color, 248)
        top = (256 - f.height) // 2
        canvas.alpha_composite(f, ((256 - f.width) // 2, top))
        g = glyph_img(font, ch, "white", 112)
        # centre of the folder body, below the tab
        cy = top + int(f.height * 0.57)
        canvas.alpha_composite(g, ((256 - g.width) // 2, cy - g.height // 2))
    os.makedirs(ICONS, exist_ok=True)
    canvas.save(out, sizes=SIZES)
    return out


def read_ini(ini):
    if not os.path.exists(ini):
        return []
    raw = open(ini, "rb").read()
    txt = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("mbcs", "replace")
    return txt.splitlines()


def icon_line(lines):
    """Index and value of IconResource/IconFile, or (None, None)."""
    for i, l in enumerate(lines):
        key, _, val = l.partition("=")
        if key.strip().lower() in ("iconresource", "iconfile"):
            return i, val.strip()
    return None, None


def ours(val):
    """Only absolute ICO resources canonically within the managed directory."""
    import re

    if not isinstance(val, str) or not val.strip():
        return False
    spec = val.strip()
    if spec.startswith('"'):
        match = re.fullmatch(r'"([^\"]+)"\s*(?:,\s*[+-]?\d+)?', spec)
        if match is None:
            return False
        candidate = match.group(1)
    else:
        if '"' in spec:
            return False
        candidate = re.sub(r',\s*[+-]?\d+\s*$', '', spec).rstrip()
    if os.path.splitext(candidate)[1].casefold() != '.ico':
        return False
    drive, tail = os.path.splitdrive(candidate)
    root_drive = os.path.splitdrive(os.path.abspath(ICONS))[0]
    if (not drive or not tail.startswith(('\\', '/'))
            or os.path.normcase(drive) != os.path.normcase(root_drive)):
        return False
    try:
        root = os.path.normcase(os.path.realpath(ICONS))
        resolved = os.path.normcase(os.path.realpath(candidate))
        return resolved != root and os.path.commonpath([root, resolved]) == root
    except (OSError, ValueError):
        return False


def write_ini(ini, lines):
    if os.path.exists(ini):
        k32.SetFileAttributesW(ini, 0x80)  # NORMAL, else open() fails on hidden+system
    if lines:
        open(ini, "w", encoding="utf-16", newline="\r\n").write("\n".join(lines) + "\n")
        k32.SetFileAttributesW(ini, HIDDEN | SYSTEM)
    elif os.path.exists(ini):
        os.remove(ini)


def set_icon(folder, ico):
    ini = os.path.join(folder, "desktop.ini")
    lines = read_ini(ini)
    i, val = icon_line(lines)
    if val is not None and not ours(val):
        return "skip: own icon " + val
    entry = f"IconResource={ico},0"
    if i is not None:
        lines[i] = entry
    else:
        s = next((n for n, l in enumerate(lines) if l.strip().lower() == "[.shellclassinfo]"), None)
        if s is None:
            lines = ["[.ShellClassInfo]", entry] + lines
        else:
            lines.insert(s + 1, entry)
    write_ini(ini, lines)
    attrs = k32.GetFileAttributesW(folder)
    k32.SetFileAttributesW(folder, attrs | READONLY)
    git_exclude(folder)
    return "ok"


def unset_icon(folder):
    ini = os.path.join(folder, "desktop.ini")
    lines = read_ini(ini)
    i, val = icon_line(lines)
    if not ours(val):
        return "skip: not ours"
    del lines[i]
    if all(l.strip().lower() in ("", "[.shellclassinfo]") for l in lines):
        lines = []
    write_ini(ini, lines)
    return "removed"


def git_exclude(folder):
    """Keep desktop.ini out of `git status` in repos and worktrees."""
    if not os.path.exists(os.path.join(folder, ".git")):
        return
    r = subprocess.run(["git", "-C", folder, "rev-parse", "--git-path", "info/exclude"],
                       capture_output=True, text=True)
    if r.returncode:
        return
    path = os.path.join(folder, r.stdout.strip())
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if "desktop.ini" not in text.split():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "a", encoding="utf-8").write(("" if text.endswith("\n") or not text else "\n") + "desktop.ini\n")


def refresh(folder):
    shell = ctypes.windll.shell32
    shell.SHChangeNotify(0x00001000, 0x0005, folder, None)  # SHCNE_UPDATEDIR, SHCNF_PATHW


def main():
    args = sys.argv[1:]
    undo, plain = "--undo" in args, "--plain" in args
    files = [a for a in args if not a.startswith("--")]
    mapping = files[0] if files else os.path.join(HERE, "folders.txt")
    names = fetch()
    font = ImageFont.truetype(FONT, 1000)
    bad = [(n, g) for n, g, _, _ in read_mapping(mapping) if g not in names]
    if bad:
        sys.exit("unknown glyphs: " + ", ".join(f"line {n}: {g}" for n, g in bad))
    for _, glyph, color, folder in read_mapping(mapping):
        try:
            if not os.path.isdir(folder):
                status = "skip: missing"
            elif undo:
                status = unset_icon(folder)
            else:
                status = set_icon(folder, render(font, names, glyph, color, plain))
        except OSError as e:
            status = f"FAIL: {e.strerror} (run as admin)"
        refresh(folder)
        print(f"{status:<10} {glyph:<28} {folder}")
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED


if __name__ == "__main__":
    main()
