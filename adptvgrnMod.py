from vapoursynth import core
import vapoursynth as vs
from vsutil import get_depth, get_y, split, plane, depth
import math
from functools import partial


def adptvgrnMod(clip_in: vs.VideoNode, strength=0.25, cstrength=None, size=1, sharp=50, static=False, luma_scaling=12,
                grain_chroma=True, grainer=None, fade_edges=True, tv_range=True, lo=None, hi=None, protect_neutral=True,
                seed=-1,
                show_mask=False) -> vs.VideoNode:
    """
    Original header:
    Generates grain based on frame and pixel brightness. Details can be found here:
    https://kageru.moe/blog/article/adaptivegrain
    Strength is the strength of the grain generated by AddGrain, static=True for static grain, luma_scaling
    manipulates the grain alpha curve. Higher values will generate less grain (especially in brighter scenes),
    while lower values will generate more grain, even in brighter scenes.
    ====================================================================================================================
    This mod simply adds the size and sharpness features from havsfunc's GrainFactory3.
    Additionally, the option to process only luma is added. Requires YUV input.
    New:
    - Option to add your own graining function (i.e. grainer=lambda x: core.f3kdb.Deband(x, y=0, cr=0, cb=0, grainy=64,
      dynamic_grain=True, keep_tv_range=True, output_depth=16)
    - Fixed grain_chroma and added cstrength. Mod 2 sources with size=1 now work, too.
    - Option to fade amount of grain added on edge values where grain raises/lowers average plane value.
      - Additional protect_neutral parameter to keep neutral chroma in blacks neutral.
    - Added seed option.
    - Change defaults: static=False, fade_edges=True
    - Added custom hi and lo params.
    """

    dpth = get_depth(clip_in)

    try:
        from kagefunc import adaptive_grain
        mask = adaptive_grain(clip_in, luma_scaling=luma_scaling, show_mask=True)
    except ModuleNotFoundError:
        mask = core.adg.Mask(clip.std.PlaneStats(), luma_scaling)

    if get_depth(mask) != dpth:
        mask = depth(mask, dpth)
    if show_mask:
        return mask

    grained = sizedgrn(clip_in, strength=strength, cstrength=cstrength, size=size, sharp=sharp, static=static,
                       grain_chroma=grain_chroma, grainer=grainer, fade_edges=fade_edges, tv_range=tv_range, lo=lo,
                       hi=hi, protect_neutral=protect_neutral, seed=seed)

    return core.std.MaskedMerge(clip_in, grained, mask)


def sizedgrn(clip, strength=0.25, cstrength=None, size=1, sharp=50, static=False, grain_chroma=True,
             grainer=None, fade_edges=True, tv_range=True, lo=None, hi=None, protect_neutral=True, seed=-1):
    dpth = get_depth(clip)
    neutral = 1 << (get_depth(clip) - 1)

    def m4(x):
        return 16 if x < 16 else math.floor(x / 4 + 0.5) * 4

    cw = clip.width  # ox
    ch = clip.height  # oy

    sx = m4(cw / size) if size != 1 else cw
    sy = m4(ch / size) if size != 1 else ch
    sxa = m4((cw + sx) / 2)
    sya = m4((ch + sy) / 2)
    b = sharp / -50 + 1
    c = (1 - b) / 2
    if cstrength is None and grain_chroma:
        cstrength = .5 * strength
    elif cstrength != 0 and cstrength is not None and not grain_chroma:
        raise ValueError("cstrength must be None or 0 if grain_chroma is False!")
    elif cstrength is None and not grain_chroma:
        cstrength = 0

    blank = core.std.BlankClip(clip, sx, sy, color=[neutral for i in split(clip)])
    if grainer is None:
        grained = core.grain.Add(blank, var=strength, uvar=cstrength, constant=static, seed=seed)
    else:
        grained = grainer(blank)
    if size != 1 and (sx != cw or sy != ch):
        if size > 1.5:
            grained = core.resize.Bicubic(grained, sxa, sya, filter_param_a=b, filter_param_b=c)
        grained = core.resize.Bicubic(grained, cw, ch, filter_param_a=b, filter_param_b=c)

    if fade_edges:
        if lo:
            lo = lo << (dpth - 8)
        if hi:
            hi = [_ << (dpth - 8) for _ in hi]
        if tv_range:
            if not lo:
                lo = 16 << (dpth - 8)
            if not hi:
                hi = [235 << (dpth - 8), 240 << (dpth - 8)]
        else:
            if not lo:
                lo = 0
            if not hi:
                hi = 2 * [(1 << dpth) - 1]
        limit_expr = "x y {0} - abs - {1} < x y {0} - abs + {2} > or x y {0} - x + ?"
        grained = core.std.Expr([clip, grained], [limit_expr.format(
            neutral, lo, hi[0]), limit_expr.format(neutral, lo, hi[1])])
        if protect_neutral and (grain_chroma or cstrength > 0):
            max_value = round(3 * cstrength) << (dpth - 8)
            neutral_mask = core.std.Expr(split(depth(clip.resize.Bilinear(format=vs.YUV444P16), dpth)),
                                         "x {0} <= x {1} >= or y {2} - abs {3} <= and z {2} - abs {3} <= and {4} {5} ?".format(
                                             lo + max_value,
                                             hi[1] - max_value, neutral,
                                             max_value, (1 << dpth) - 1, 0))
            grained = core.std.MaskedMerge(grained, clip, neutral_mask, planes=[1, 2])
    else:
        grained = core.std.MakeDiff(clip, grained)
    return grained


def FrameType(n, clip, funcB=lambda x: x, funcP=lambda x: x, funcI=lambda x: x):
    if clip.get_frame(n).props._PictType.decode() == "B":
        return funcB(clip)
    elif clip.get_frame(n).props._PictType.decode() == "P":
        return funcP(clip)
    else:
        return funcI(clip)


def frmtpfnc(clip_in, funcB=lambda x: x, funcP=lambda x: x, funcI=lambda x: x):
    return core.std.FrameEval(clip_in, partial(FrameType, clip=clip_in, funcB=funcB, funcP=funcP, funcI=funcI))


def frmtpgrn(clip_in: vs.VideoNode, strength=[0.25, None, None], cstrength=[None, None, None], size=[1, None, None],
             sharp=[50, None, None], static=[True, None, None], luma_scaling=[12, None, None],
             grain_chroma=[True, None, None], grainer=[None, None, None], fade_edges=False, tv_range=True, lo=None,
             hi=None, protect_neutral=True, seed=-1, show_mask=False) -> vs.VideoNode:
    if isinstance(strength, int) or isinstance(strength, float):
        strength = 3 * [strength]
    if isinstance(cstrength, int) or isinstance(cstrength, float):
        cstrength = 3 * [cstrength]
    if isinstance(size, int) or isinstance(size, float):
        size = 3 * [size]
    if isinstance(sharp, int) or isinstance(sharp, float):
        sharp = 3 * [sharp]
    if isinstance(static, bool):
        static = 3 * [static]
    if isinstance(luma_scaling, int) or isinstance(luma_scaling, float):
        luma_scaling = 3 * [luma_scaling]
    if isinstance(grain_chroma, bool):
        grain_chroma = 3 * [grain_chroma]
    if callable(grainer):
        grainer = 3 * [grainer]

    return frmtpfnc(clip_in if not show_mask else get_y(clip_in),
                    funcB=lambda x: adptvgrnMod(x, strength[0], cstrength[0], size[0], sharp[0], static[0],
                                                luma_scaling[0], grain_chroma[0], grainer[0], fade_edges,
                                                tv_range, lo, hi, protect_neutral, seed, show_mask),
                    funcP=lambda x: adptvgrnMod(x, strength[1], cstrength[1], size[1], sharp[1], static[1],
                                                luma_scaling[1], grain_chroma[1], grainer[1], fade_edges, tv_range, lo,
                                                hi, protect_neutral, seed, show_mask),
                    funcI=lambda x: adptvgrnMod(x, strength[2], cstrength[2], size[2], sharp[2], static[2],
                                                luma_scaling[2], grain_chroma[2], grainer[2], fade_edges, tv_range, lo,
                                                hi, protect_neutral, seed, show_mask))
