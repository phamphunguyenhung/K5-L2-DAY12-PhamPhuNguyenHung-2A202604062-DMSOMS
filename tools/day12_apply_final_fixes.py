#!/usr/bin/env python3
"""Apply final human-approved cleanups to CVAT Task 62, verify read-back, and export."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from cvat_sdk import make_client
from cvat_sdk.api_client import models

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


def get_attr(attrs: list[dict], attr_id: int) -> str | None:
    for a in attrs:
        if a["spec_id"] == attr_id:
            return a["value"]
    return None


def set_attr(attrs: list[dict], attr_id: int, value: str):
    for a in attrs:
        if a["spec_id"] == attr_id:
            a["value"] = value
            return
    attrs.append({"spec_id": attr_id, "value": value})


def center_x(pts: list[float]) -> float:
    return 0.5 * (pts[0] + pts[2])


def main():
    url, token = load_local_env()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    with make_client(host=url) as client:
        client.api_client.set_default_header("Authorization", f"Token {token}")
        task = client.tasks.retrieve(62)
        frames = {i: f.name for i, f in enumerate(task.get_meta().frames)}
        labels = {lb.name: lb for lb in task.get_labels()}
        label_by_id = {lb.id: lb for lb in labels.values()}

        def attr_id(lname: str, aname: str) -> int:
            for a in labels[lname].attributes:
                if a.name == aname:
                    return a.id
            raise KeyError((lname, aname))

        ann = task.get_annotations()
        raw = ann.to_dict()
        bkp = AUDIT_DIR / f"cvat_task62_pre_final_cleanup_{ts}.json"
        bkp.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")

        new_shapes = []
        removed = []
        updated = []

        for sh in raw.get("shapes", []):
            fname = frames.get(sh["frame"], "")
            lname = label_by_id[sh["label_id"]].name

            # 1. DMS: remove 'object' on D02, D06 (GUIDE §4.2) and false-positive 'phone' on D05 (Audi logo)
            if fname in ("D02.png", "D06.png") and lname == "object":
                removed.append((fname, lname, "GUIDE §4.2 forbids object in DMS"))
                continue
            if fname == "D05.png" and lname == "phone":
                removed.append((fname, lname, "False positive on Audi steering wheel logo"))
                continue

            # 2. DMS face attribute fixes
            if fname == "D02.png" and lname == "face":
                set_attr(sh["attributes"], attr_id("face", "eye_left"), "open")
                updated.append((fname, "face.eye_left", "open"))
            if fname == "D03.png" and lname == "face":
                set_attr(sh["attributes"], attr_id("face", "gaze_zone"), "center")
                updated.append((fname, "face.gaze_zone", "center"))
            if fname == "D04.png" and lname == "face":
                set_attr(sh["attributes"], attr_id("face", "gaze_zone"), "center")
                updated.append((fname, "face.gaze_zone", "center"))
            if fname == "D06.png" and lname == "face":
                set_attr(sh["attributes"], attr_id("face", "eye_right"), "unknown")
                updated.append((fname, "face.eye_right", "unknown"))

            # 3. OMS: S04_rgb rear_left & S06_rgb rear_right infant_seat -> child_seat (occupied=no)
            if fname == "S04_rgb.png" and lname == "infant_seat":
                if get_attr(sh["attributes"], attr_id("infant_seat", "seat")) == "rear_left":
                    sh["label_id"] = labels["child_seat"].id
                    sh["attributes"] = [
                        {"spec_id": attr_id("child_seat", "seat"), "value": "rear_left"},
                        {"spec_id": attr_id("child_seat", "occupied"), "value": "no"},
                    ]
                    updated.append((fname, "infant_seat->child_seat", "rear_left, occupied=no"))
            if fname == "S06_rgb.png" and lname == "infant_seat":
                if get_attr(sh["attributes"], attr_id("infant_seat", "seat")) == "rear_right":
                    sh["label_id"] = labels["child_seat"].id
                    sh["attributes"] = [
                        {"spec_id": attr_id("child_seat", "seat"), "value": "rear_right"},
                        {"spec_id": attr_id("child_seat", "occupied"), "value": "no"},
                    ]
                    updated.append((fname, "infant_seat->child_seat", "rear_right, occupied=no"))

            # 4. OMS: Remove child mannequin 'person' & 'face' inside child_seat/infant_seat
            # S01_rgb (rear_left), S03_rgb/S03_ir (rear_right & rear_left), S07_ir (rear_left)
            if fname == "S01_rgb.png" and lname in ("person", "face") and center_x(sh["points"]) > 500:
                removed.append((fname, lname, "Child mannequin in child_seat (use occupied=yes)"))
                continue
            if fname in ("S03_rgb.png", "S03_ir.png") and lname in ("person", "face"):
                removed.append((fname, lname, "Child/infant mannequin in seat (GUIDE §3)"))
                continue
            if fname == "S07_ir.png" and lname in ("person", "face") and center_x(sh["points"]) > 500:
                removed.append((fname, lname, "Child mannequin in child_seat (use occupied=yes)"))
                continue

            new_shapes.append(sh)

        raw["shapes"] = new_shapes
        for t in raw.get("tags", []):
            t.pop("id", None)
        for sh in raw.get("shapes", []):
            sh.pop("id", None)
            if sh.get("elements"):
                for el in sh["elements"]:
                    el.pop("id", None)

        task.set_annotations(models.LabeledDataRequest(**raw))
        rb = task.get_annotations()
        print(f"Removed {len(removed)} shapes: {removed}")
        print(f"Updated {len(updated)} items: {updated}")
        print(f"Read-back Task 62: tags={len(rb.tags)}, shapes={len(rb.shapes)}")

        out_zip = REPO_ROOT / "export_final.zip"
        if out_zip.exists():
            out_zip.unlink()
        task.export_dataset("CVAT for images 1.1", str(out_zip), include_images=False)
        print(f"Exported export_final.zip (sha256={sha256_file(out_zip)})")


if __name__ == "__main__":
    main()
