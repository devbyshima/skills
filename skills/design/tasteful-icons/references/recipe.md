# The recipe

What `scripts/tasteful_icons.py` draws, layer by layer. Use it to reimplement the look natively
(Figma, CSS, SwiftUI) or to tune an icon by hand.

## Layers

1. **Tile**: superellipse |x|^2.5 + |y|^2.5 = 1, full bleed. Vertical gradient: top = base lightened 2.5%
   (HLS L), bottom = base darkened 3%.
2. **Glyph shadow**: glyph alpha, Gaussian blur 14, offset y 12, color = base mixed 40% toward black,
   opacity 0.35-0.5, knocked out under the glyph so it never darkens the glass.
3. **Glass**, all clipped to the glyph, back to front:
   - milky body: white, opacity 0.86 at the top to 0.5 at the bottom;
   - light pool: radial gradient at (50%, 75%) of the glyph box, radius 52%, color = base mixed 35% toward
     white, opacity 0.7 at the center to 0 at the edge;
   - sheen: radial white at (42%, 24%), radius 60%, opacity 0.5 to 0;
   - inner edge glow: white stroke 40 px (20 px inside), blur 7, opacity 0.8;
   - edge: crisp white stroke 2.6 px inside, opacity 0.75.
4. **Marks**: color = base darkened 6%, sitting on a white halo (mark plus 20 px, blur 6, opacity 0.7).

## Tuning (`glass` overrides)

| Key | Default | Effect |
|---|---|---|
| `milk` | `[0.86, 0.5]` | white opacity top, bottom; raise for whiter, more opaque glass |
| `pool_opacity` | `0.7` | strength of the colored light at the bottom |
| `pool_at`, `pool_r` | `[0.5, 0.75]`, `0.52` | position and radius of that light, in glyph-box units |
| `sheen` | `0.5` | top highlight |
| `inner`, `inner_w` | `0.8`, `20` | inner edge glow opacity and width |
| `edge`, `edge_w` | `0.75`, `2.6` | crisp edge opacity and width |

Neutral tiles (gray, white) need a darker `pool` override so the haze reads (the apple uses `#8C8C8C`).
