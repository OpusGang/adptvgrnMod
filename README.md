# adptvgrnMod

This combines kagefunc's `adaptive_grain` function with havsfunc's `GrainFactory3` port to introduce additional size and sharpness parameters, as well as the option to only add grain to the luma plane. YUV input is required.

## Usage

```python
adptvgrnMod(clip_in, strength=0.25, cstrength=None, size=1, sharp=50, static=False, luma_scaling=12, grain_chroma=True, grainer=None, fade_edges=True, tv_range=True, protect_neutral=True, seed=-1, show_mask=False)
```

**strength**
Strength of the grain generated by AddGrain for luma plane. Default is `0.25`.

**cstrength**
Strength of the grain generated by AddGrain for chroma planes. Default is `None`.

**size**
Size of grain. Bicubic resizing is used. Default of `1` does not resize.

**sharp**
Sharpness to use when upscaling the grain to size. This changes b and c:
```
b = sharp / -50 + 1
c = (1 - b) / 2
```
Default is `50`.

**static**
Whether to generate static or dynamic grain. Default is `False`.

**luma_scaling**
This values changes the general grain opacity curve. Lower values will generate more grain, even in brighter scenes, while higher values will generate less, even in dark scenes. Default is `12`.

**grain_chroma**
Whether grain should be added to chroma planes. If set and `cstrength=None`, `cstrength` becomes `strength / 2`. Default is `True`.

**grainer**
Option to allow use of alternative graining functions. Resizing will still be performed. Default is `core.grain.Add`.

**fade_edges**
Whether to fade out graining as it gets close to the edges of allowed values. For 8-bit TV range, this means that 16 will not be grained, if the grainer would adjust by 2, 17 won't be grained et cetera. Default is `True`.

**tv_range**
Whether `fade_edges` should use full or limited range. Default is `True`.

**protect_neutral**
Whether to try to keep grain away from chroma plane when luma reaches the edges. Only works when `fade_edges` is on. Default is `True`.

**seed**
Seed to use in AddGrain. Default of `-1` is random.

**show_mask**
Whether to show generated mask. Default is `False`.

## frmtpfnc

Function to apply different functions to B, P, and I frames.

## frmtpgrn

Wrapper around `adptvgrnMod` and `frmtpfnc`. Enter a list for each parameter with [B, P, I] frame type's values.
