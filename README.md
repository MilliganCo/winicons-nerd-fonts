# WinIconsNerdFonts

Windows folder-icon utility using Nerd Fonts glyphs. Only code and a synthetic mapping example
are published; personal folder lists, downloaded fonts, generated icons and caches are excluded.

## Setup and usage

Python 3.10+ on Windows: `python -m pip install -r requirements.txt`.
Copy `folders.example.txt` to your own ignored `folders.txt`, then replace the example paths.

```sh
python nficons.py
python nficons.py --plain
python nficons.py --undo
```

Running the tool downloads the Nerd Fonts symbol font/name table when absent, generates icons and
edits desktop.ini in folders explicitly listed by the user. Check the mapping before running.
Font/glyph licenses remain with their upstream projects: https://github.com/ryanoasis/nerd-fonts/blob/master/LICENSE
No downloaded font or rendered glyph asset is redistributed in this repository.

Ownership checks parse quoted/indexed ICO descriptors and use canonical directory containment;
similar prefixes such as icons-other are not treated as this tool's files. Relative/environment
descriptors and another drive are left untouched. Symlinks resolving outside the managed directory
are rejected by the implementation; actual symlink tests depend on Windows privileges.


See [VALIDATION.md](VALIDATION.md) for actual publication checks.
