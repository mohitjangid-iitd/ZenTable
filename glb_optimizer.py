"""
glb_optimizer.py
================
FastAPI ke liye GLB optimization utility.

Usage (server-side):
    from glb_optimizer import optimize_glb, audit_glb

"""

import subprocess
import shutil
import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from pygltflib import GLTF2

# ─── CONFIG ───────────────────────────────────────────────
# gltf-transform ka path — server pe 'gltf-transform' hona chahiye PATH mein
# Agar npx use karna ho toh GLTF_TRANSFORM_CMD = ["npx", "@gltf-transform/cli"]
GLTF_TRANSFORM_CMD = ["gltf-transform"]

# Texture max size (pixels) — 1024 = 1K
TEXTURE_MAX_SIZE = 1024

# Texture format
TEXTURE_FORMAT = "webp"  # 'webp' | 'jpeg' | 'png' | 'ktx2'
# ──────────────────────────────────────────────────────────


@dataclass
class AuditReport:
    """GLB file ka audit report"""
    original_size_mb: float
    optimized_size_mb: float
    size_reduction_pct: float
    poly_count: int
    texture_count: int
    texture_size_warning: bool   # koi texture 1K se bada hai
    estimated_load_time_sec: float  # 4G pe estimate
    draco_applied: bool
    texture_optimized: bool
    benchmark_ok: bool           # < 3MB aur < 2 sec
    warnings: list
    recommendations: list


def _run(cmd: list, cwd=None) -> tuple[bool, str]:
    """Command run karo, (success, output) return karo"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=120  # 2 min max
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Timeout: optimization took too long"
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]} — install karo: npm install -g @gltf-transform/cli"
    except Exception as e:
        return False, str(e)


def _get_file_size_mb(path: str) -> float:
    """File size MB mein"""
    try:
        return round(os.path.getsize(path) / (1024 * 1024), 3)
    except:
        return 0.0


def _inspect_glb(path: str) -> dict:
    """gltf-transform inspect se metadata nikalo"""
    cmd = GLTF_TRANSFORM_CMD + ["inspect", path, "--format", "json"]
    success, output = _run(cmd)

    result = {
        "poly_count": 0,
        "texture_count": 0,
        "texture_size_warning": False,
        "raw_output": output
    }

    if not success:
        # fallback: basic JSON parse of GLB manually
        return _inspect_glb_manual(path, result)

    try:
        # gltf-transform inspect JSON output parse karo
        # Output format: JSON object with scenes, meshes, textures etc.
        data = json.loads(output)

        # Poly count
        meshes = data.get("meshes", {}).get("properties", [])
        for mesh in meshes:
            primitives = mesh.get("primitives", [])
            for prim in primitives:
                result["poly_count"] += prim.get("indices", 0) // 3

        # Texture info
        textures = data.get("textures", {}).get("properties", [])
        result["texture_count"] = len(textures)
        for tex in textures:
            w = tex.get("width", 0)
            h = tex.get("height", 0)
            if w > TEXTURE_MAX_SIZE or h > TEXTURE_MAX_SIZE:
                result["texture_size_warning"] = True

    except (json.JSONDecodeError, KeyError):
        # JSON parse fail — text output se extract karo
        result = _inspect_glb_manual(path, result)

    return result


def _inspect_glb_manual(path: str, base: dict) -> dict:
    """Fallback: pygltflib se basic info"""
    try:
        gltf = GLTF2().load(path)

        # Poly count
        poly = 0
        if gltf.accessors:
            for mesh in (gltf.meshes or []):
                for prim in mesh.primitives:
                    if prim.indices is not None:
                        acc = gltf.accessors[prim.indices]
                        poly += acc.count // 3
        base["poly_count"] = poly

        # Textures
        base["texture_count"] = len(gltf.textures or [])

    except Exception:
        pass  # pygltflib bhi fail ho — default values use karo

    return base


def optimize_glb(input_path: str, output_path: str) -> tuple[bool, str]:
    """
    GLB file optimize karo — Draco + texture compression.

    Args:
        input_path:  Source .glb file path
        output_path: Optimized output .glb path

    Returns:
        (success: bool, message: str)
    """
    if not os.path.exists(input_path):
        return False, f"Input file nahi mila: {input_path}"

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # gltf-transform optimize command
    # --compress draco         → Draco geometry compression
    # --texture-compress webp  → textures ko WebP mein convert
    # --texture-size 1024      → max 1K textures
    cmd = GLTF_TRANSFORM_CMD + [
        "optimize",
        input_path,
        output_path,
        "--compress", "draco",
        "--texture-compress", TEXTURE_FORMAT,
        "--texture-size", str(TEXTURE_MAX_SIZE),
    ]

    success, output = _run(cmd)

    if success and os.path.exists(output_path):
        orig_mb = _get_file_size_mb(input_path)
        opt_mb  = _get_file_size_mb(output_path)
        reduction = round((1 - opt_mb / orig_mb) * 100, 1) if orig_mb > 0 else 0
        return True, f"✅ Optimized: {orig_mb}MB → {opt_mb}MB ({reduction}% reduction)"
    else:
        # Fallback: sirf Draco apply karo (texture skip)
        cmd_fallback = GLTF_TRANSFORM_CMD + [
            "draco",
            input_path,
            output_path,
        ]
        success2, output2 = _run(cmd_fallback)
        if success2 and os.path.exists(output_path):
            return True, f"⚠️ Partial: Draco applied (texture optimization skipped)\n{output2[:200]}"
        return False, f"Optimization failed:\n{output[:300]}\n{output2[:200]}"


def audit_glb(
    original_path: str,
    optimized_path: Optional[str] = None
) -> AuditReport:
    """
    GLB file ka full audit report generate karo.

    Args:
        original_path:  Original .glb path
        optimized_path: Optimized .glb path (None = sirf original audit)

    Returns:
        AuditReport dataclass
    """
    orig_mb = _get_file_size_mb(original_path)
    opt_mb  = _get_file_size_mb(optimized_path) if optimized_path and os.path.exists(optimized_path) else orig_mb

    reduction_pct = round((1 - opt_mb / orig_mb) * 100, 1) if orig_mb > 0 else 0.0

    # Inspect optimized version (ya original agar optimized nahi)
    inspect_path = optimized_path if (optimized_path and os.path.exists(optimized_path)) else original_path
    info = _inspect_glb(inspect_path)

    # Load time estimate: 4G avg = ~15 Mbps download
    # + parsing overhead ~0.5 sec
    download_sec  = (opt_mb * 8) / 15
    parsing_sec   = 0.5
    estimated_sec = round(download_sec + parsing_sec, 1)

    # Warnings aur recommendations
    warnings = []
    recommendations = []

    if opt_mb > 3:
        warnings.append(f"File size {opt_mb}MB > 3MB target — AR pe slow load ho sakta hai")
        recommendations.append("Blender mein poly count aur reduce karo (target: 5k–20k)")

    poly = info["poly_count"]
    if poly > 20000:
        warnings.append(f"Poly count {poly:,} > 20k — mobile pe laggy ho sakta hai")
        recommendations.append("Blender Decimate modifier use karo ya retopology karo")
    elif poly == 0:
        warnings.append("Poly count detect nahi hua — manually check karo")

    if info["texture_size_warning"]:
        warnings.append(f"Koi texture > {TEXTURE_MAX_SIZE}px hai — optimize karo")
        recommendations.append("Textures 1024x1024 tak rakho (already WebP conversion apply hua hai)")

    if estimated_sec > 2:
        warnings.append(f"Estimated load time {estimated_sec}s > 2s target")
        recommendations.append("CDN use karo models serve karne ke liye (Cloudflare R2 perfect rahega)")

    benchmark_ok = opt_mb <= 3 and estimated_sec <= 2

    return AuditReport(
        original_size_mb=orig_mb,
        optimized_size_mb=opt_mb,
        size_reduction_pct=reduction_pct,
        poly_count=poly,
        texture_count=info["texture_count"],
        texture_size_warning=info["texture_size_warning"],
        estimated_load_time_sec=estimated_sec,
        draco_applied=optimized_path is not None,
        texture_optimized=optimized_path is not None,
        benchmark_ok=benchmark_ok,
        warnings=warnings,
        recommendations=recommendations,
    )


def optimize_and_audit(input_path: str, output_path: str) -> tuple[bool, dict]:
    """
    Convenience function: optimize + audit ek saath.

    Returns:
        (success: bool, result: dict with 'message' and 'audit')
    """
    success, message = optimize_glb(input_path, output_path)

    audit = audit_glb(
        original_path=input_path,
        optimized_path=output_path if success else None
    )

    return success, {
        "message": message,
        "audit": asdict(audit)
    }
