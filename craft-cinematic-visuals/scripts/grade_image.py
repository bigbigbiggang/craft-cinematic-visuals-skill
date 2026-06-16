#!/usr/bin/env python3
"""Apply restrained, geometry-preserving cinematic grades to raster images."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageFilter
except ModuleNotFoundError as exc:
    raise SystemExit(
        "grade_image.py requires Pillow and NumPy. "
        "In Codex, call load_workspace_dependencies and use its Python executable."
    ) from exc


@dataclass(frozen=True)
class Grade:
    exposure: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    temperature: float = 0.0
    tint: float = 0.0
    shoulder: float = 0.0
    black_density: float = 0.0
    soften: float = 0.0
    grain: float = 0.0
    vignette: float = 0.0
    shadow_tone: tuple[float, float, float] = (0.0, 0.0, 0.0)
    highlight_tone: tuple[float, float, float] = (0.0, 0.0, 0.0)


PRESETS = {
    "source-neutral": Grade(
        exposure=-0.03,
        contrast=1.035,
        saturation=0.96,
        shoulder=0.14,
        black_density=0.015,
        soften=0.16,
        grain=0.003,
    ),
    "cool-contained": Grade(
        exposure=-0.05,
        contrast=1.045,
        saturation=0.93,
        temperature=-0.07,
        tint=-0.01,
        shoulder=0.16,
        black_density=0.02,
        soften=0.18,
        grain=0.0035,
        shadow_tone=(-0.002, 0.001, 0.006),
    ),
    "warm-muted": Grade(
        exposure=-0.025,
        contrast=1.025,
        saturation=0.94,
        temperature=0.055,
        shoulder=0.16,
        black_density=0.012,
        soften=0.2,
        grain=0.0035,
        shadow_tone=(-0.001, 0.001, 0.003),
        highlight_tone=(0.005, 0.002, -0.002),
    ),
    "dense-neutral": Grade(
        exposure=-0.06,
        contrast=1.065,
        saturation=0.94,
        shoulder=0.18,
        black_density=0.035,
        soften=0.18,
        grain=0.0045,
        vignette=0.018,
    ),
}


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def parse_rect(value: str) -> tuple[int, int, int, int]:
    try:
        rect = tuple(int(part) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("rect must be x1,y1,x2,y2") from exc
    if len(rect) != 4:
        raise argparse.ArgumentTypeError("rect must be x1,y1,x2,y2")
    return rect


def apply_grade(rgb: np.ndarray, grade: Grade, strength: float, seed: int) -> np.ndarray:
    source = rgb.copy()
    work = np.clip(rgb * (2.0 ** (grade.exposure * strength)), 0.0, 1.0)

    temp = grade.temperature * strength
    tint = grade.tint * strength
    balance = np.array(
        [1.0 + 0.10 * temp + 0.035 * tint, 1.0 - 0.05 * tint, 1.0 - 0.10 * temp + 0.035 * tint],
        dtype=np.float32,
    )
    work = np.clip(work * balance, 0.0, 1.0)

    luma = np.sum(work * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), axis=2, keepdims=True)
    contrasted = 0.42 + (luma - 0.42) * (1.0 + (grade.contrast - 1.0) * strength)
    ratio = contrasted / np.maximum(luma, 1e-5)
    work = np.clip(work * ratio, 0.0, 1.0)

    luma = np.sum(work * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), axis=2, keepdims=True)
    shoulder_mask = smoothstep(0.58, 1.0, luma)
    work -= grade.shoulder * strength * shoulder_mask * np.square(np.maximum(work - 0.55, 0.0))
    work -= grade.black_density * strength * (1.0 - smoothstep(0.05, 0.42, luma))

    luma = np.sum(work * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), axis=2, keepdims=True)
    saturation = 1.0 + (grade.saturation - 1.0) * strength
    work = luma + (work - luma) * saturation

    shadow_mask = 1.0 - smoothstep(0.16, 0.58, luma)
    highlight_mask = smoothstep(0.52, 0.92, luma)
    work += shadow_mask * np.array(grade.shadow_tone, dtype=np.float32) * strength
    work += highlight_mask * np.array(grade.highlight_tone, dtype=np.float32) * strength

    if grade.soften > 0:
        softened = np.asarray(
            Image.fromarray(np.uint8(np.clip(work, 0.0, 1.0) * 255.0)).filter(
                ImageFilter.GaussianBlur(radius=0.55)
            ),
            dtype=np.float32,
        ) / 255.0
        work = work * (1.0 - grade.soften * strength) + softened * grade.soften * strength

    if grade.vignette > 0:
        height, width = work.shape[:2]
        yy, xx = np.mgrid[-1.0:1.0:complex(height), -1.0:1.0:complex(width)]
        radius = np.sqrt(xx * xx + yy * yy)
        vignette = smoothstep(0.42, 1.35, radius)[..., None]
        work *= 1.0 - grade.vignette * strength * vignette

    if grade.grain > 0:
        rng = np.random.default_rng(seed)
        luma = np.sum(work * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32), axis=2, keepdims=True)
        grain_weight = 0.45 + 0.55 * (1.0 - smoothstep(0.72, 1.0, luma))
        noise = rng.normal(0.0, grade.grain * strength, size=work.shape[:2] + (1,)).astype(np.float32)
        work += noise * grain_weight

    return np.clip(work, 0.0, 1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preset", choices=sorted(PRESETS), default="source-neutral")
    parser.add_argument("--strength", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=19)
    parser.add_argument("--protect-rect", action="append", type=parse_rect, default=[])
    args = parser.parse_args()

    if not 0.0 <= args.strength <= 1.0:
        parser.error("--strength must be between 0 and 1")

    image = Image.open(args.input)
    has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
    rgba = image.convert("RGBA")
    original = np.asarray(rgba, dtype=np.uint8)
    rgb = original[..., :3].astype(np.float32) / 255.0
    graded = np.uint8(np.clip(apply_grade(rgb, PRESETS[args.preset], args.strength, args.seed), 0.0, 1.0) * 255.0)

    height, width = graded.shape[:2]
    for x1, y1, x2, y2 in args.protect_rect:
        x1, x2 = sorted((max(0, x1), min(width, x2)))
        y1, y2 = sorted((max(0, y1), min(height, y2)))
        graded[y1:y2, x1:x2] = original[y1:y2, x1:x2, :3]

    if has_alpha:
        result = np.dstack([graded, original[..., 3]])
        output = Image.fromarray(result, mode="RGBA")
    else:
        output = Image.fromarray(graded, mode="RGB")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
