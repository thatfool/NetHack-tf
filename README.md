# NetHack-tilefont

This is an experimental fork of NetHack 5.0 that can use a custom font to display graphical tiles in a terminal.

It contains scripts that create a font and a symbol set:
- win/share/build\_tile\_font.py creates a ttf font with the NetHack tiles in the supplementary PUA that needs to be installed, or otherwise configured in your terminal of choice.
- win/share/build\_tile\_font\_symset.py creates a symbol set that needs to be added to dat/symbols or an installed symbols file.

Once the files are installed, the symbol set can be activated in your .nethackrc:

```
OPTIONS=symset:TileFont
```

However, by default, NetHack expects symbols to be exactly one character wide. This branch contains an additional patch that adds wide\_map\_cells option.
This option makes the curses interface use two terminal columns per map column:

```
OPTIONS=wide_map_cells
```

Currently, only the curses interface supports this option.

## Supported Terminals Status

Support by terminal emulators is a bit of a mixed bag:

### Linux

To install the font:

```sh
install -Dm644 win/share/nethack-tile-font.ttf "$HOME/.local/share/fonts/nethack-tile-font.ttf"
fc-cache -f "$HOME/.local/share/fonts"
```

**Alacritty:** Works without further configuration if the font is installed.

**Konsole:** Works on somewhat recent Qt versions with additional fontconfig setup after installing the font. Put this in `~/.config/fontconfig/conf.d/90-nethack-tiles.conf` (create directories if they don't exist) and run `fc-cache -f`.
```xml
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test name="prgname"><string>konsole</string></test>
    <edit name="family" mode="append_last" binding="strong">
      <string>NetHack Tiles</string>
    </edit>
  </match>
</fontconfig>
```

**Kitty:** Uses the font if it's installed, but doesn't render the color glyphs correctly because it only renders a pre-defined set of emoji as color glyphs.

**Ghostty:** Does not work on Linux even if the font is configured as a fallback font, because it doesn't handle color glyphs correctly with FreeType.

### macOS

To install the font, double-click it or copy it to ~/Library/Fonts.

**Terminal:** Works without further configuration if the font is installed.

**Ghostty:** Needs configuration, and the font needs to be built with the --svg option. For example, to configure the default JetBrains Mono font with the tile font as a fallback:
```
font-family="JetBrains Mono"
font-family="NetHack Tiles"
```

**iTerm 2:** Uses the font if it's installed, but the Metal renderer does not display colored glyphs correctly if they're not in a font called "Apple Color Emoji". If the GPU rendering is disabled in Settings/General/Magic, or at other times when the CoreText fallback is used (e.g. while actively resizing the window), it works.

