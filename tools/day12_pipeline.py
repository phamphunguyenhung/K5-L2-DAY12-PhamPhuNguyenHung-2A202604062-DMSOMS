#!/usr/bin/env python3
"""Local-only DMS & OMS autolabel + geometry QC + CVAT 1.1 XML exporter for Day 12 (G12).

Strictly local inference (YOLO26l + GroundingDINO-tiny + FAN2D/S3FD). No images leave the machine.
Reuses cvat_tools.pose.face50.FaceLandmarker and scripts/cabin_schema.py.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
CVAT_SRC = Path(r"D:\06-Learning\AIA-VINGROUP\learning\cvat\src")
if str(CVAT_SRC) not in sys.path:
    sys.path.insert(0, str(CVAT_SRC))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from cabin_schema import FACE13_POINTS, LABELS, MIN_FACE13_WIDTH_PX, cvat_labels_json  # noqa: E402

YOLO_WEIGHTS = Path(r"D:\06-Learning\AIA-VINGROUP\learning\cvat\models\checkpoints\yolo26l.pt")
GDINO_ID = "IDEA-Research/grounding-dino-tiny"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def iou_xyxy(a: list[float], b: list[float]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return inter / max(area_a + area_b - inter, 1e-6)


def containment(inner: list[float], outer: list[float]) -> float:
    x1, y1 = max(inner[0], outer[0]), max(inner[1], outer[1])
    x2, y2 = min(inner[2], outer[2]), min(inner[3], outer[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_i = max(0.0, inner[2] - inner[0]) * max(0.0, inner[3] - inner[1])
    return inter / max(area_i, 1e-6)


def clamp_box(box: list[float], w: int, h: int) -> list[float]:
    x1 = max(0.0, min(float(w), float(box[0])))
    y1 = max(0.0, min(float(h), float(box[1])))
    x2 = max(0.0, min(float(w), float(box[2])))
    y2 = max(0.0, min(float(h), float(box[3])))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]


def unrotate_box_rot90_k1(box: list[float], orig_w: int, orig_h: int) -> list[float]:
    """Map box from np.rot90(img, k=1) (shape orig_w x orig_h) back to orig (orig_h x orig_w)."""
    # For k=1 (90 deg CCW): rot(r, c) -> orig(c, orig_w - 1 - r) => orig_x = orig_w - 1 - rot_y, orig_y = rot_x
    rx1, ry1, rx2, ry2 = box
    ox1 = orig_w - 1 - ry2
    ox2 = orig_w - 1 - ry1
    oy1 = rx1
    oy2 = rx2
    return clamp_box([ox1, oy1, ox2, oy2], orig_w, orig_h)


def unrotate_pt_rot90_k1(x: float, y: float, orig_w: int) -> tuple[float, float]:
    return (float(orig_w - 1 - y), float(x))


def oms_seat_from_x(cx: float, w: int) -> str:
    """SVIRO camera faces rear: left of image = rear_right, right = rear_left."""
    frac = cx / max(w, 1)
    if frac < 0.36:
        return "rear_right"
    if frac <= 0.64:
        return "rear_middle"
    return "rear_left"


def map_ibug68_to_face13(p68: np.ndarray, sc68: np.ndarray, w: int, h: int) -> dict[str, dict[str, Any]]:
    """Map iBUG-68 landmarks to Guideline Cabin v1.0 face13 (person's own left/right)."""
    pts_map = {
        "left_eye_outer": (p68[45], float(sc68[45])),
        "left_eye_inner": (p68[42], float(sc68[42])),
        "left_eye_upper": (0.5 * (p68[43] + p68[44]), float(min(sc68[43], sc68[44]))),
        "left_eye_lower": (0.5 * (p68[46] + p68[47]), float(min(sc68[46], sc68[47]))),
        "right_eye_outer": (p68[36], float(sc68[36])),
        "right_eye_inner": (p68[39], float(sc68[39])),
        "right_eye_upper": (0.5 * (p68[37] + p68[38]), float(min(sc68[37], sc68[38]))),
        "right_eye_lower": (0.5 * (p68[40] + p68[41]), float(min(sc68[40], sc68[41]))),
        "nose_tip": (p68[30], float(sc68[30])),
        "mouth_left": (p68[54], float(sc68[54])),
        "mouth_right": (p68[48], float(sc68[48])),
        "lip_upper": (p68[51], float(sc68[51])),
        "lip_lower": (p68[57], float(sc68[57])),
    }
    out = {}
    for name in FACE13_POINTS:
        xy, sc = pts_map[name]
        x, y = float(xy[0]), float(xy[1])
        outside = "1" if (x < 0 or y < 0 or x > w or y > h) else "0"
        occluded = "1" if (outside == "1" or sc < 0.30) else "0"
        cx = max(0.0, min(float(w), x))
        cy = max(0.0, min(float(h), y))
        out[name] = {"x": round(cx, 2), "y": round(cy, 2), "occluded": occluded, "outside": outside, "score": round(sc, 3)}
    return out


def eye_state_from_ear(pts: dict[str, dict[str, Any]], side: str) -> str:
    outer = pts[f"{side}_eye_outer"]
    inner = pts[f"{side}_eye_inner"]
    upper = pts[f"{side}_eye_upper"]
    lower = pts[f"{side}_eye_lower"]
    if any(p["occluded"] == "1" or p["outside"] == "1" for p in (outer, inner, upper, lower)):
        return "unknown"
    horiz = np.hypot(outer["x"] - inner["x"], outer["y"] - inner["y"])
    vert = np.hypot(upper["x"] - lower["x"], upper["y"] - lower["y"])
    if horiz < 4.0:
        return "unknown"
    ear = vert / horiz
    return "closed" if ear < 0.17 else "open"


class ModelBundle:
    def __init__(self):
        self._yolo = None
        self._gdino_proc = None
        self._gdino = None
        self._fl = None

    def yolo(self):
        if self._yolo is None:
            from ultralytics import YOLO
            self._yolo = YOLO(str(YOLO_WEIGHTS))
        return self._yolo

    def gdino(self):
        if self._gdino is None:
            import torch  # noqa: F401
            from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
            self._gdino_proc = AutoProcessor.from_pretrained(GDINO_ID, local_files_only=True)
            self._gdino = AutoModelForZeroShotObjectDetection.from_pretrained(GDINO_ID, local_files_only=True)
            self._gdino.eval()
        return self._gdino_proc, self._gdino

    def fan2d(self):
        if self._fl is None:
            from cvat_tools.pose.face50 import FaceLandmarker
            self._fl = FaceLandmarker(min_face_score=0.5)
        return self._fl


def run_gdino(models: ModelBundle, pil_img: Image.Image, prompt: str, threshold: float = 0.30) -> list[tuple[str, float, list[float]]]:
    import torch
    proc, model = models.gdino()
    inputs = proc(images=pil_img, text=prompt, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    res = proc.post_process_grounded_object_detection(
        outputs, inputs.input_ids, threshold=threshold, text_threshold=threshold, target_sizes=[pil_img.size[::-1]]
    )[0]
    out = []
    lbls = res.get("text_labels", res["labels"])
    for sc, lbl, bx in zip(res["scores"], lbls, res["boxes"]):
        out.append((str(lbl).strip().lower(), float(sc), [float(x) for x in bx]))
    return out


def process_oms_image(img_path: Path, models: ModelBundle, run_id: str) -> dict[str, Any]:
    t0 = time.time()
    bgr = cv2.imread(str(img_path))
    h, w = bgr.shape[:2]
    modality = "rgb" if img_path.stem.endswith("_rgb") else "ir"
    pil_img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

    # 1. YOLO26l
    y_res = models.yolo().predict(str(img_path), conf=0.25, verbose=False)[0]
    persons: list[dict[str, Any]] = []
    yolo_objs: list[dict[str, Any]] = []
    for b in y_res.boxes:
        cls_name = y_res.names[int(b.cls)]
        conf = float(b.conf)
        xyxy = clamp_box([float(x) for x in b.xyxy[0]], w, h)
        if cls_name == "person":
            persons.append({"box": xyxy, "conf": conf, "model": "yolo26l"})
        elif cls_name in ("backpack", "handbag", "suitcase"):
            yolo_objs.append({"type": "bag", "box": xyxy, "conf": conf, "model": "yolo26l"})
        elif cls_name in ("cup", "bottle"):
            yolo_objs.append({"type": "cup", "box": xyxy, "conf": conf, "model": "yolo26l"})

    # 2. GroundingDINO for child_seat, infant_seat, box, face, bag, cup
    gd_dets = run_gdino(models, pil_img, "person. face. child seat. infant seat. bag. box. cup.", threshold=0.30)

    # Merge persons if YOLO missed
    for lbl, conf, bx in gd_dets:
        if lbl == "person":
            bx = clamp_box(bx, w, h)
            if not any(iou_xyxy(bx, p["box"]) > 0.4 for p in persons):
                persons.append({"box": bx, "conf": conf, "model": "grounding-dino-tiny"})

    boxes: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    # Add persons + faces
    for p in persons:
        bx = p["box"]
        cx = 0.5 * (bx[0] + bx[2])
        seat = oms_seat_from_x(cx, w)
        boxes.append({
            "label": "person",
            "xyxy": bx,
            "attrs": {"seat": seat, "seatbelt": "unknown"},
            "model_name": p["model"],
            "confidence": round(p["conf"], 3),
            "run_id": run_id,
            "created_at": now,
        })
        # Find face inside person
        face_candidates = [
            (conf, clamp_box(fb, w, h))
            for lbl, conf, fb in gd_dets
            if "face" in lbl and containment(clamp_box(fb, w, h), bx) > 0.6
        ]
        if face_candidates:
            fconf, fbox = max(face_candidates, key=lambda x: x[0])
            boxes.append({
                "label": "face",
                "xyxy": fbox,
                "attrs": {"eye_left": "unknown", "eye_right": "unknown", "glasses": "unknown", "gaze_zone": "other"},
                "model_name": "grounding-dino-tiny",
                "confidence": round(fconf, 3),
                "run_id": run_id,
                "created_at": now,
            })

    # Add child_seat / infant_seat / object (suppress heavy overlap with person)
    seats_boxes = []
    for lbl, conf, bx in gd_dets:
        bx = clamp_box(bx, w, h)
        if any(containment(bx, p["box"]) > 0.65 or iou_xyxy(bx, p["box"]) > 0.45 for p in persons):
            continue
        if "infant" in lbl:
            if not any(iou_xyxy(bx, sb) > 0.4 for sb in seats_boxes):
                seats_boxes.append(bx)
                boxes.append({
                    "label": "infant_seat",
                    "xyxy": bx,
                    "attrs": {"seat": oms_seat_from_x(0.5 * (bx[0] + bx[2]), w), "facing": "rear"},
                    "model_name": "grounding-dino-tiny",
                    "confidence": round(conf, 3),
                    "run_id": run_id,
                    "created_at": now,
                })
        elif "child" in lbl:
            if not any(iou_xyxy(bx, sb) > 0.4 for sb in seats_boxes):
                seats_boxes.append(bx)
                boxes.append({
                    "label": "child_seat",
                    "xyxy": bx,
                    "attrs": {"seat": oms_seat_from_x(0.5 * (bx[0] + bx[2]), w), "occupied": "no"},
                    "model_name": "grounding-dino-tiny",
                    "confidence": round(conf, 3),
                    "run_id": run_id,
                    "created_at": now,
                })
        elif lbl in ("bag", "box", "cup"):
            if not any(iou_xyxy(bx, yo["box"]) > 0.4 for yo in yolo_objs):
                yolo_objs.append({"type": lbl, "box": bx, "conf": conf, "model": "grounding-dino-tiny"})

    for yo in yolo_objs:
        bx = yo["box"]
        if any(containment(bx, p["box"]) > 0.7 for p in persons):
            continue
        boxes.append({
            "label": "object",
            "xyxy": bx,
            "attrs": {"seat": oms_seat_from_x(0.5 * (bx[0] + bx[2]), w), "type": yo["type"]},
            "model_name": yo["model"],
            "confidence": round(yo["conf"], 3),
            "run_id": run_id,
            "created_at": now,
        })

    return {
        "name": img_path.name,
        "rel_path": str(img_path.relative_to(REPO_ROOT / "G12")).replace("\\", "/"),
        "width": w,
        "height": h,
        "sha256": sha256_file(img_path),
        "inference_sec": round(time.time() - t0, 3),
        "tags": [{"label": "frame_meta", "attrs": {"modality": modality, "light": "unknown", "camera_blocked": "no"}}],
        "boxes": boxes,
        "skeletons": [],
    }


def process_dms_image(img_path: Path, models: ModelBundle, run_id: str) -> dict[str, Any]:
    t0 = time.time()
    bgr = cv2.imread(str(img_path))
    h, w = bgr.shape[:2]
    rot = np.ascontiguousarray(np.rot90(bgr, 1))
    pil_rot = Image.fromarray(cv2.cvtColor(rot, cv2.COLOR_BGR2RGB))
    now = datetime.now(timezone.utc).isoformat()

    boxes: list[dict[str, Any]] = []
    skeletons: list[dict[str, Any]] = []

    # 1. YOLO26l on upright rotated image
    y_res = models.yolo().predict(rot, conf=0.25, verbose=False)[0]
    person_box = None
    person_conf = 0.0
    for b in y_res.boxes:
        cls_name = y_res.names[int(b.cls)]
        conf = float(b.conf)
        bx = unrotate_box_rot90_k1([float(x) for x in b.xyxy[0]], w, h)
        if cls_name == "person" and conf > person_conf:
            person_box, person_conf = bx, conf
        elif cls_name == "cell phone":
            boxes.append({
                "label": "phone",
                "xyxy": bx,
                "attrs": {"state": "held"},
                "model_name": "yolo26l",
                "confidence": round(conf, 3),
                "run_id": run_id,
                "created_at": now,
            })

    if person_box:
        boxes.append({
            "label": "person",
            "xyxy": person_box,
            "attrs": {"seat": "driver", "seatbelt": "unknown"},
            "model_name": "yolo26l",
            "confidence": round(person_conf, 3),
            "run_id": run_id,
            "created_at": now,
        })

    # 2. FAN2D directly on rot=90 (fast, no rot=0 wasted)
    fl = models.fan2d()
    res = fl._run(np.ascontiguousarray(rot[:, :, ::-1]))
    face_box = None
    if res is not None:
        lm, sc, fs, rot_bbox = res
        pts68 = np.array([unrotate_pt_rot90_k1(x, y, w) for x, y in lm])
        face_box = unrotate_box_rot90_k1([float(x) for x in rot_bbox], w, h)
        f13 = map_ibug68_to_face13(pts68, sc, w, h)
        el_state = eye_state_from_ear(f13, "left")
        er_state = eye_state_from_ear(f13, "right")
        boxes.append({
            "label": "face",
            "xyxy": face_box,
            "attrs": {"eye_left": el_state, "eye_right": er_state, "glasses": "unknown", "gaze_zone": "other"},
            "model_name": "s3fd+fan2d",
            "confidence": round(float(fs), 3),
            "run_id": run_id,
            "created_at": now,
        })
        if (face_box[2] - face_box[0]) >= MIN_FACE13_WIDTH_PX:
            skeletons.append({
                "label": "face13",
                "points": f13,
                "model_name": "s3fd+fan2d",
                "confidence": round(float(np.mean(sc)), 3),
                "run_id": run_id,
                "created_at": now,
            })

    # 3. GroundingDINO for hands (and phone fallback if YOLO missed)
    gd_dets = run_gdino(models, pil_rot, "hand. cell phone.", threshold=0.32)
    hand_candidates = []
    for lbl, conf, bx in gd_dets:
        obx = unrotate_box_rot90_k1(bx, w, h)
        if "hand" in lbl:
            hand_candidates.append((conf, obx))
        elif "phone" in lbl and not any(b["label"] == "phone" and iou_xyxy(b["xyxy"], obx) > 0.3 for b in boxes):
            boxes.append({
                "label": "phone",
                "xyxy": obx,
                "attrs": {"state": "held"},
                "model_name": "grounding-dino-tiny",
                "confidence": round(conf, 3),
                "run_id": run_id,
                "created_at": now,
            })

    # Keep at most 2 hands (1 left, 1 right) by driver's y-axis (larger y = left side)
    hand_candidates.sort(key=lambda x: x[0], reverse=True)
    kept_hands = []
    for conf, hbx in hand_candidates:
        if any(iou_xyxy(hbx, kb[1]) > 0.35 for kb in kept_hands):
            continue
        kept_hands.append((conf, hbx))
        if len(kept_hands) == 2:
            break
    if len(kept_hands) == 2:
        # Larger center_y = driver's left hand
        c0 = 0.5 * (kept_hands[0][1][1] + kept_hands[0][1][3])
        c1 = 0.5 * (kept_hands[1][1][1] + kept_hands[1][1][3])
        sides = ["left", "right"] if c0 >= c1 else ["right", "left"]
    elif len(kept_hands) == 1:
        ref_y = 0.5 * (face_box[1] + face_box[3]) if face_box else h * 0.5
        cy = 0.5 * (kept_hands[0][1][1] + kept_hands[0][1][3])
        sides = ["left"] if cy >= ref_y else ["right"]
    else:
        sides = []

    for (conf, hbx), side in zip(kept_hands, sides):
        boxes.append({
            "label": "hand",
            "xyxy": hbx,
            "attrs": {"whose": "driver", "side": side, "on_wheel": "unknown"},
            "model_name": "grounding-dino-tiny",
            "confidence": round(conf, 3),
            "run_id": run_id,
            "created_at": now,
        })

    return {
        "name": img_path.name,
        "rel_path": str(img_path.relative_to(REPO_ROOT / "G12")).replace("\\", "/"),
        "width": w,
        "height": h,
        "sha256": sha256_file(img_path),
        "inference_sec": round(time.time() - t0, 3),
        "tags": [{"label": "frame_meta", "attrs": {"modality": "ir", "light": "unknown", "camera_blocked": "no"}}],
        "boxes": boxes,
        "skeletons": skeletons,
    }


def build_cvat_xml(records: list[dict[str, Any]], task_name: str = "Day12-G12") -> ET.Element:
    root = ET.Element("annotations")
    ET.SubElement(root, "version").text = "1.1"
    meta = ET.SubElement(root, "meta")
    task = ET.SubElement(meta, "task")
    ET.SubElement(task, "name").text = task_name
    ET.SubElement(task, "size").text = str(len(records))
    labels_el = ET.SubElement(task, "labels")
    for spec in cvat_labels_json():
        lel = ET.SubElement(labels_el, "label")
        ET.SubElement(lel, "name").text = spec["name"]
        ET.SubElement(lel, "type").text = spec["type"]
        attrs_el = ET.SubElement(lel, "attributes")
        for a in spec["attributes"]:
            ael = ET.SubElement(attrs_el, "attribute")
            ET.SubElement(ael, "name").text = a["name"]
            ET.SubElement(ael, "mutable").text = "False"
            ET.SubElement(ael, "input_type").text = a["input_type"]
            ET.SubElement(ael, "default_value").text = a["default_value"]
            ET.SubElement(ael, "values").text = "\n".join(a["values"])

    for idx, rec in enumerate(records):
        img_el = ET.SubElement(
            root, "image",
            id=str(idx), name=rec["name"], width=str(rec["width"]), height=str(rec["height"]),
        )
        for t in rec["tags"]:
            tel = ET.SubElement(img_el, "tag", label=t["label"], source="auto")
            for k, v in t["attrs"].items():
                ET.SubElement(tel, "attribute", name=k).text = str(v)
        for b in rec["boxes"]:
            x1, y1, x2, y2 = b["xyxy"]
            bel = ET.SubElement(
                img_el, "box",
                label=b["label"], source="auto", occluded="0",
                xtl=f"{x1:.2f}", ytl=f"{y1:.2f}", xbr=f"{x2:.2f}", ybr=f"{y2:.2f}", z_order="0",
            )
            for k, v in b["attrs"].items():
                ET.SubElement(bel, "attribute", name=k).text = str(v)
        for s in rec["skeletons"]:
            sel = ET.SubElement(img_el, "skeleton", label=s["label"], source="auto", z_order="0")
            for pname in FACE13_POINTS:
                p = s["points"][pname]
                ET.SubElement(
                    sel, "points",
                    label=pname, source="auto",
                    occluded=p["occluded"], outside=p["outside"],
                    points=f"{p['x']:.2f},{p['y']:.2f}",
                )
    return root


def write_cvat_zip(records: list[dict[str, Any]], zip_path: Path, task_name: str = "Day12-G12"):
    root = build_cvat_xml(records, task_name=task_name)
    ET.indent(root, space="  ")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("annotations.xml", xml_bytes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--g12-dir", default=str(REPO_ROOT / "G12"))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "artifacts" / "g12_run"))
    args = ap.parse_args()

    g12 = Path(args.g12_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")

    oms_files = sorted([g12 / "oms" / f"S{i:02d}_{m}.png" for i in range(1, 9) for m in ("rgb", "ir")])
    dms_files = sorted([g12 / "driver" / f"D{i:02d}.png" for i in range(1, 7)])

    models = ModelBundle()
    records = []
    for p in oms_files:
        print(f"[OMS] {p.name}...", flush=True)
        records.append(process_oms_image(p, models, run_id))
    for p in dms_files:
        print(f"[DMS] {p.name}...", flush=True)
        records.append(process_dms_image(p, models, run_id))

    draft_json = out / "draft_annotations.json"
    draft_json.write_text(json.dumps({"run_id": run_id, "images": records}, indent=2, ensure_ascii=False), encoding="utf-8")

    # Export part_A (S01, S02), part_B (D01, D02), and export_final.zip (all 22)
    part_a = [r for r in records if r["name"].startswith(("S01_", "S02_"))]
    part_b = [r for r in records if r["name"] in ("D01.png", "D02.png")]
    write_cvat_zip(part_a, REPO_ROOT / "part_A.zip")
    write_cvat_zip(part_b, REPO_ROOT / "part_B.zip")
    write_cvat_zip(records, REPO_ROOT / "export_final.zip")
    print(f"Done! Exported 22 images to {REPO_ROOT / 'export_final.zip'}")


if __name__ == "__main__":
    main()
