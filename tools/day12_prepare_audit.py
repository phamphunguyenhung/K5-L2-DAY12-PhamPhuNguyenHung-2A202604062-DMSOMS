#!/usr/bin/env python3
"""Backup CVAT Task 62, extract current attributes, and render upright DMS crops + OMS RGB/IR views."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from cvat_sdk import make_client

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(r"C:\Users\ppnh1\.cvat.env")
AUDIT_DIR = REPO_ROOT / "artifacts" / "g12_audit"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_local_env() -> tuple[str, str]:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["CVAT_URL"], env["CVAT_TOKEN"]


def main():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    views_dir = AUDIT_DIR / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # 1. Backup CVAT Task 62 & current export_final.zip
    url, token = load_local_env()
    with make_client(host=url) as client:
        client.api_client.set_default_header("Authorization", f"Token {token}")
        task = client.tasks.retrieve(62)
        ann = task.get_annotations()
        raw = ann.to_dict()
        bkp_json = AUDIT_DIR / f"cvat_task62_backup_{ts}.json"
        bkp_json.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")
        print(f"Backup JSON: {bkp_json} (sha256={sha256_file(bkp_json)[:12]}, version={raw.get('version')})")

    exp_zip = REPO_ROOT / "export_final.zip"
    if exp_zip.exists():
        print(f"Current export_final.zip sha256={sha256_file(exp_zip)}")

    # 2. Parse annotations.xml for exact current state
    with zipfile.ZipFile(exp_zip) as z:
        root = ET.fromstring(z.read("annotations.xml"))

    records = []
    for img_el in sorted(root.findall("image"), key=lambda x: x.get("name")):
        name = img_el.get("name")
        w, h = int(float(img_el.get("width"))), int(float(img_el.get("height")))
        rec = {"name": name, "width": w, "height": h, "tags": [], "boxes": [], "skeletons": []}
        for el in img_el:
            attrs = {a.get("name"): a.text for a in el.findall("attribute")}
            if el.tag == "tag":
                rec["tags"].append({"label": el.get("label"), "attrs": attrs})
            elif el.tag == "box":
                rec["boxes"].append({
                    "label": el.get("label"),
                    "xyxy": [float(el.get(k)) for k in ("xtl", "ytl", "xbr", "ybr")],
                    "attrs": attrs,
                })
            elif el.tag == "skeleton":
                pts = {}
                for p in el.findall("points"):
                    xy = [float(v) for v in p.get("points").split(",")]
                    pts[p.get("label")] = {"x": xy[0], "y": xy[1], "occluded": p.get("occluded"), "outside": p.get("outside")}
                rec["skeletons"].append({"label": el.get("label"), "points": pts})
        records.append(rec)

    (AUDIT_DIR / "current_attributes.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 3. Render upright DMS views (full upright + zoomed face crop)
    for rec in records:
        name = rec["name"]
        if name.startswith("D"):
            bgr = cv2.imread(str(REPO_ROOT / "G12" / "driver" / name))
            # Rotate 90 deg CCW so driver head is upright
            rot = np.ascontiguousarray(np.rot90(bgr, 1))
            rh, rw = rot.shape[:2]  # rw=1024, rh=1280
            vis = rot.copy()

            def rot_pt(x, y):
                return int(round(y)), int(round(bgr.shape[1] - 1 - x))

            face_crop = None
            for b in rec["boxes"]:
                x1, y1, x2, y2 = b["xyxy"]
                p1 = rot_pt(x1, y1)
                p2 = rot_pt(x2, y2)
                rx1, rx2 = min(p1[0], p2[0]), max(p1[0], p2[0])
                ry1, ry2 = min(p1[1], p2[1]) , max(p1[1], p2[1])
                col = (0, 255, 0) if b["label"] == "face" else ((255, 100, 0) if b["label"] == "person" else (0, 165, 255))
                cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), col, 2)
                cv2.putText(vis, b["label"], (rx1, max(20, ry1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
                if b["label"] == "face":
                    pad = 50
                    cx1, cy1 = max(0, rx1 - pad), max(0, ry1 - pad)
                    cx2, cy2 = min(rw, rx2 + pad), min(rh, ry2 + pad)
                    face_crop = rot[cy1:cy2, cx1:cx2]

            # Save upright annotated + zoomed face side-by-side
            vis_small = cv2.resize(vis, (640, 800))
            if face_crop is not None and face_crop.size > 0:
                fc_res = cv2.resize(face_crop, (640, 800))
                comb = np.hstack([vis_small, fc_res])
            else:
                comb = vis_small
            cv2.imwrite(str(views_dir / f"audit_{name}"), comb)

    # 4. Render OMS RGB | IR side-by-side views for S01..S08
    for i in range(1, 9):
        rgb_name, ir_name = f"S{i:02d}_rgb.png", f"S{i:02d}_ir.png"
        rgb_img = cv2.imread(str(REPO_ROOT / "G12" / "oms" / rgb_name))
        ir_img = cv2.imread(str(REPO_ROOT / "G12" / "oms" / ir_name))
        for im, rname in ((rgb_img, rgb_name), (ir_img, ir_name)):
            rec = next(r for r in records if r["name"] == rname)
            for b in rec["boxes"]:
                x1, y1, x2, y2 = [int(round(v)) for v in b["xyxy"]]
                cv2.rectangle(im, (x1, y1), (x2, y2), (0, 220, 0), 2)
                lbl = f"{b['label']}:{b['attrs'].get('seat','')}"
                cv2.putText(im, lbl, (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
            cv2.putText(im, rname, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        comb = np.hstack([rgb_img, ir_img])
        cv2.imwrite(str(views_dir / f"audit_S{i:02d}_pair.png"), comb)

    print(f"Rendered audit views to {views_dir}")


if __name__ == "__main__":
    main()
