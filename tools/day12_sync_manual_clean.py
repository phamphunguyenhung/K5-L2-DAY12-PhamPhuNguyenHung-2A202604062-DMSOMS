#!/usr/bin/env python3
"""Fix cabin_check errors/warnings on CVAT Task 62, convert source='file' -> 'manual', re-export."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cvat_sdk import make_client
from cvat_sdk.api_client import models

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(r"C:\Users\ppnh1\.cvat.env")


def load_local_env() -> tuple[str, str]:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["CVAT_URL"], env["CVAT_TOKEN"]


def oms_seat_from_x(cx: float, w: int = 960) -> str:
    frac = cx / max(w, 1)
    if frac < 0.36:
        return "rear_right"
    if frac <= 0.64:
        return "rear_middle"
    return "rear_left"


def set_attr(attrs: list[dict], attr_id: int, value: str):
    for a in attrs:
        if a["spec_id"] == attr_id:
            a["value"] = value
            return
    attrs.append({"spec_id": attr_id, "value": value})


def get_attr(attrs: list[dict], attr_id: int) -> str | None:
    for a in attrs:
        if a["spec_id"] == attr_id:
            return a["value"]
    return None


def main():
    url, token = load_local_env()
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
        backup_path = REPO_ROOT / "artifacts" / "g12_run" / "cvat_task62_pre_manual_clean.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")

        # Update tags: source -> manual (strip 'id' for PUT)
        for t in raw.get("tags", []):
            t.pop("id", None)
            t["source"] = "manual"

        # Group shapes by frame
        new_shapes = []
        hands_by_frame: dict[int, list[dict]] = {}
        for sh in raw.get("shapes", []):
            sh.pop("id", None)
            fname = frames.get(sh["frame"], "")
            lname = label_by_id[sh["label_id"]].name
            sh["source"] = "manual"
            if sh.get("elements"):
                for el in sh["elements"]:
                    el.pop("id", None)
                    el["source"] = "manual"

            # 1. Remove 'hand' on OMS (S##) per GUIDE §4.1-4.2
            if lname == "hand" and fname.startswith("S"):
                continue

            # 2. Fix OMS seat='driver' -> rear_right / rear_middle / rear_left
            if fname.startswith("S") and lname in ("person", "child_seat", "infant_seat", "object"):
                pts = sh["points"]
                cx = 0.5 * (pts[0] + pts[2])
                seat_aid = attr_id(lname, "seat")
                if get_attr(sh["attributes"], seat_aid) == "driver":
                    set_attr(sh["attributes"], seat_aid, oms_seat_from_x(cx, 960))

            if lname == "hand" and fname.startswith("D"):
                hands_by_frame.setdefault(sh["frame"], []).append(sh)

            new_shapes.append(sh)

        # 3. Fix DMS hand.side by y-coordinate (larger y = driver's left)
        side_aid = attr_id("hand", "side")
        for fidx, hlist in hands_by_frame.items():
            if len(hlist) == 2:
                cy0 = 0.5 * (hlist[0]["points"][1] + hlist[0]["points"][3])
                cy1 = 0.5 * (hlist[1]["points"][1] + hlist[1]["points"][3])
                if cy0 >= cy1:
                    set_attr(hlist[0]["attributes"], side_aid, "left")
                    set_attr(hlist[1]["attributes"], side_aid, "right")
                else:
                    set_attr(hlist[0]["attributes"], side_aid, "right")
                    set_attr(hlist[1]["attributes"], side_aid, "left")

        raw["shapes"] = new_shapes
        task.set_annotations(models.LabeledDataRequest(**raw))
        print(f"Updated Task 62: tags={len(raw['tags'])}, shapes={len(raw['shapes'])}, all source='manual'")

        out_zip = REPO_ROOT / "export_final.zip"
        if out_zip.exists():
            out_zip.unlink()
        task.export_dataset("CVAT for images 1.1", str(out_zip), include_images=False)
        print("Re-exported export_final.zip from CVAT Task 62")

    # Verify source counts in exported zip
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(REPO_ROOT / "export_final.zip") as z:
        root = ET.fromstring(z.read("annotations.xml"))
    srcs = {}
    for img in root.findall("image"):
        for el in img:
            s = el.get("source", "?")
            srcs[s] = srcs.get(s, 0) + 1
    print("Exported XML source counts:", srcs)


if __name__ == "__main__":
    main()
