#!/usr/bin/env python3
"""Post-process draft_annotations.json: per-seat OMS deduplication, DMS y-axis check, re-export, QC."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))
from day12_pipeline import write_cvat_zip  # noqa: E402
from day12_review_ui import build_review_ui  # noqa: E402


def dedupe_oms_seats(rec: dict) -> dict:
    if not rec["name"].startswith("S"):
        return rec
    main_labels = {"person", "child_seat", "infant_seat"}
    by_seat = {}
    others = []
    for b in rec["boxes"]:
        if b["label"] in main_labels:
            seat = b["attrs"].get("seat")
            prev = by_seat.get(seat)
            # Prefer person over child_seat/infant_seat, or higher confidence
            score = (1.0 if b["label"] == "person" else 0.0) + b.get("confidence", 0.0)
            if prev is None or score > prev[0]:
                by_seat[seat] = (score, b)
        else:
            others.append(b)
    rec["boxes"] = [v[1] for v in by_seat.values()] + others
    return rec


def main():
    draft_path = REPO_ROOT / "artifacts" / "g12_run" / "draft_annotations.json"
    data = json.loads(draft_path.read_text(encoding="utf-8"))
    cleaned = [dedupe_oms_seats(r) for r in data["images"]]
    data["images"] = cleaned
    clean_path = REPO_ROOT / "artifacts" / "g12_run" / "clean_annotations.json"
    clean_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    part_a = [r for r in cleaned if r["name"].startswith(("S01_", "S02_"))]
    part_b = [r for r in cleaned if r["name"] in ("D01.png", "D02.png")]
    write_cvat_zip(part_a, REPO_ROOT / "part_A.zip")
    write_cvat_zip(part_b, REPO_ROOT / "part_B.zip")
    write_cvat_zip(cleaned, REPO_ROOT / "export_final.zip")
    print("Re-exported part_A.zip, part_B.zip, export_final.zip")

    # Verify DMS face13 y-axis orientation
    for r in cleaned:
        if r["name"].startswith("D") and r["skeletons"]:
            pts = r["skeletons"][0]["points"]
            ly = pts["left_eye_outer"]["y"]
            ry = pts["right_eye_outer"]["y"]
            print(f"  {r['name']} face13: left_eye_outer.y={ly:.1f}, right_eye_outer.y={ry:.1f}, y_ok={ly > ry}")

    build_review_ui(clean_path, REPO_ROOT / "review_ui", REPO_ROOT / "check_final.txt")


if __name__ == "__main__":
    main()
