#!/usr/bin/env python3
"""Visual Attribute Audit & Auto-Correction Engine for Day 12 (G12, CVAT Task 62)."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Any

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


# Vision-verified attribute rules from direct inspection of upright DMS crops & OMS RGB/IR pairs
VISION_DECISIONS: dict[str, list[dict[str, Any]]] = {
    "D01.png": [
        {"label": "face", "attr": "glasses", "proposed": "none", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Zoomed face crop shows bare eyes, nose bridge, and temples with no frame or lens.", "reason": "Clear visual evidence of no glasses."},
        {"label": "face", "attr": "gaze_zone", "proposed": "lap", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Head pitched down and eyes directed downward toward hands resting on lap.", "reason": "Gaze directed at lap."},
        {"label": "person", "attr": "seatbelt", "proposed": "worn_correct", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Diagonal dark seatbelt strap clearly crosses from left shoulder across chest to right hip.", "reason": "Seatbelt properly worn."},
        {"label": "hand", "attr": "on_wheel", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Both hands rest together on lap; steering wheel below is untouched.", "reason": "Hands clearly off steering wheel."},
    ],
    "D02.png": [
        {"label": "face", "attr": "glasses", "proposed": "clear", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Thin metallic rimmed frame visible across nose bridge and temples; eyes visible through clear lenses.", "reason": "Wearing clear glasses."},
        {"label": "face", "attr": "eye_left", "proposed": "open", "status": "NEEDS HUMAN REVIEW", "conf": "medium",
         "evidence": "Both eyes look downward at object in hands with similar narrow open fissures; currently eye_left=closed, eye_right=open.", "reason": "Likely both eyes open looking down; needs human confirmation."},
        {"label": "face", "attr": "gaze_zone", "proposed": "lap", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Head and eyes directed straight down toward hands/object over lap.", "reason": "Gaze directed at lap."},
        {"label": "person", "attr": "seatbelt", "proposed": "worn_correct", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Diagonal dark seatbelt strap clearly crosses from left shoulder across chest.", "reason": "Seatbelt properly worn."},
        {"label": "hand", "attr": "on_wheel", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Both hands hold a small shiny object in front of lap, off the steering wheel.", "reason": "Hands off steering wheel."},
        {"label": "object", "attr": "_box_check", "proposed": "REMOVE_PER_GUIDE_4_2", "status": "NEEDS HUMAN REVIEW", "conf": "high",
         "evidence": "Object box around handheld item in DMS image.", "reason": "GUIDE.md §4.2 forbids object boxes in DMS; requires human approval to delete."},
    ],
    "D03.png": [
        {"label": "face", "attr": "glasses", "proposed": "none", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Zoomed face crop shows no glasses frame on nose bridge or temples.", "reason": "No glasses worn."},
        {"label": "face", "attr": "gaze_zone", "proposed": "center", "status": "NEEDS HUMAN REVIEW", "conf": "medium",
         "evidence": "Head turned left toward phone held near center console.", "reason": "Looking at held phone near center; confirm center vs other."},
        {"label": "person", "attr": "seatbelt", "proposed": "worn_correct", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Diagonal seatbelt strap clearly visible from left shoulder across chest.", "reason": "Seatbelt properly worn."},
        {"label": "hand", "attr": "on_wheel", "side": "right", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Right hand holds phone in mid-air.", "reason": "Right hand holding phone, not on wheel."},
        {"label": "hand", "attr": "on_wheel", "side": "left", "proposed": "yes", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Left hand grasps lower rim of steering wheel.", "reason": "Left hand clearly touching steering wheel."},
    ],
    "D04.png": [
        {"label": "face", "attr": "glasses", "proposed": "clear", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Thin rimmed clear glasses frame visible across nose bridge and temples.", "reason": "Wearing clear glasses."},
        {"label": "face", "attr": "gaze_zone", "proposed": "center", "status": "NEEDS HUMAN REVIEW", "conf": "medium",
         "evidence": "Eyes looking down-left toward center console / lap.", "reason": "Confirm center vs lap."},
        {"label": "person", "attr": "seatbelt", "proposed": "worn_correct", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Diagonal seatbelt strap clearly visible from left shoulder across chest.", "reason": "Seatbelt properly worn."},
        {"label": "hand", "attr": "on_wheel", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Hand rests on lap/belt buckle, away from steering wheel.", "reason": "Hand not on wheel."},
    ],
    "D05.png": [
        {"label": "face", "attr": "glasses", "proposed": "clear", "status": "NEEDS HUMAN REVIEW", "conf": "medium",
         "evidence": "Dark temple arm visible in side profile; lens tint cannot be confirmed from profile.", "reason": "Glasses present, confirm clear vs sun vs unknown."},
        {"label": "face", "attr": "gaze_zone", "proposed": "lap", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Head pitched strongly downward toward lap/hands.", "reason": "Looking down at lap."},
        {"label": "person", "attr": "seatbelt", "proposed": "worn_correct", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Diagonal seatbelt strap clearly visible from left shoulder across chest.", "reason": "Seatbelt properly worn."},
        {"label": "hand", "attr": "on_wheel", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Both hands rest on lap above steering wheel hub.", "reason": "Hands off wheel."},
        {"label": "phone", "attr": "_box_check", "proposed": "FALSE_POSITIVE_STEERING_LOGO", "status": "NEEDS HUMAN REVIEW", "conf": "high",
         "evidence": "Phone box is drawn around the Audi 4-ring steering wheel hub logo.", "reason": "False positive phone box; requires human approval to delete."},
    ],
    "D06.png": [
        {"label": "face", "attr": "glasses", "proposed": "clear", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Thick dark-rimmed glasses with transparent lenses showing eye region and IR reflections.", "reason": "Wearing clear glasses."},
        {"label": "face", "attr": "eye_right", "proposed": "unknown", "status": "NEEDS HUMAN REVIEW", "conf": "high",
         "evidence": "Strong IR LED reflection on right lens and 13/13 face13 landmarks marked occluded.", "reason": "Resolves contradiction with face13 occlusion (cabin_check WARN)."},
        {"label": "face", "attr": "gaze_zone", "proposed": "road", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Head upright facing forward toward windshield while drinking.", "reason": "Gaze directed toward road."},
        {"label": "person", "attr": "seatbelt", "proposed": "worn_correct", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Diagonal dark seatbelt strap visible across left shoulder.", "reason": "Seatbelt properly worn."},
        {"label": "hand", "attr": "on_wheel", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "One hand holds bottle at mouth, other hand rests on lap.", "reason": "Both hands off steering wheel."},
        {"label": "object", "attr": "_box_check", "proposed": "REMOVE_PER_GUIDE_4_2", "status": "NEEDS HUMAN REVIEW", "conf": "high",
         "evidence": "Object box around drinking bottle in DMS image.", "reason": "GUIDE.md §4.2 forbids object boxes in DMS; requires human approval to delete."},
    ],
    "S01_rgb.png": [
        {"label": "person", "attr": "seatbelt", "seat": "rear_right", "proposed": "not_worn", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Adult torso clearly lit in blue shirt with no seatbelt strap.", "reason": "No seatbelt worn."},
    ],
    "S01_ir.png": [
        {"label": "person", "attr": "seatbelt", "seat": "rear_right", "proposed": "not_worn", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Adult torso clearly visible in IR with no seatbelt strap.", "reason": "No seatbelt worn."},
    ],
    "S02_ir.png": [
        {"label": "child_seat", "attr": "occupied", "seat": "rear_left", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Empty child seat clearly visible on rear_left in S02_ir.", "reason": "Child seat is unoccupied."},
    ],
    "S04_rgb.png": [
        {"label": "infant_seat", "attr": "_class_check", "seat": "rear_left", "proposed": "CHANGE_TO_child_seat", "status": "NEEDS HUMAN REVIEW", "conf": "high",
         "evidence": "Upright forward-facing booster/child seat on rear_left (same as S04_ir child_seat).", "reason": "Class mismatch between RGB (infant_seat) and IR (child_seat)."},
    ],
    "S05_ir.png": [
        {"label": "child_seat", "attr": "occupied", "seat": "rear_right", "proposed": "no", "status": "KEEP CURRENT", "conf": "high",
         "evidence": "Already occupied=no.", "reason": "Verified correct."},
        {"label": "object", "attr": "type", "seat": "rear_left", "proposed": "bag", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Black tote handbag with handles clearly visible on rear_left seat.", "reason": "Object is a bag."},
    ],
    "S06_rgb.png": [
        {"label": "infant_seat", "attr": "_class_check", "seat": "rear_right", "proposed": "CHANGE_TO_child_seat", "status": "NEEDS HUMAN REVIEW", "conf": "high",
         "evidence": "Upright forward-facing child seat on rear_right (same as S06_ir child_seat).", "reason": "Class mismatch between RGB (infant_seat) and IR (child_seat)."},
    ],
    "S06_ir.png": [
        {"label": "child_seat", "attr": "occupied", "seat": "rear_right", "proposed": "no", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Empty child seat clearly visible on rear_right.", "reason": "Child seat is unoccupied."},
    ],
    "S07_ir.png": [
        {"label": "person", "attr": "seatbelt", "seat": "rear_right", "proposed": "not_worn", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Adult torso clearly lit in S07_ir with no seatbelt strap.", "reason": "No seatbelt worn."},
    ],
    "S08_rgb.png": [
        {"label": "person", "attr": "seatbelt", "seat": "rear_right", "proposed": "not_worn", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Adult torso in grey sweater clearly lit with no seatbelt strap.", "reason": "No seatbelt worn."},
    ],
    "S08_ir.png": [
        {"label": "person", "attr": "seatbelt", "seat": "rear_right", "proposed": "not_worn", "status": "AUTO-APPLY CANDIDATE", "conf": "high",
         "evidence": "Adult torso clearly lit in IR with no seatbelt strap.", "reason": "No seatbelt worn."},
    ],
}


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


def build_needs_review_html(audit_rows: list[dict[str, Any]], out_path: Path):
    review_rows = [r for r in audit_rows if r["review_status"] == "NEEDS HUMAN REVIEW"]
    auto_rows = [r for r in audit_rows if r["review_status"] == "AUTO-APPLY CANDIDATE"]

    def render_rows(items):
        out = []
        for idx, r in enumerate(items):
            img_rel = f"artifacts/g12_audit/views/audit_{r['image_id']}" if r["image_id"].startswith("D") else f"artifacts/g12_audit/views/audit_{r['image_id'][:3]}_pair.png"
            out.append(f"""
            <tr>
              <td><strong>{html.escape(r['image_id'])}</strong><br/><a href="http://localhost:8080/tasks/62/jobs/61" target="_blank">Open CVAT</a></td>
              <td><code>{html.escape(r['label'])}</code><br/><small>#{html.escape(str(r['shape_id']))}</small></td>
              <td><code>{html.escape(r['attribute'])}</code></td>
              <td><span class="pill">{html.escape(str(r['old_value']))}</span> &rarr; <span class="pill prop">{html.escape(str(r['proposed_value']))}</span></td>
              <td>{html.escape(r['visible_evidence'])}<br/><small style="color:#475569">{html.escape(r['reason'])}</small></td>
              <td><img src="{html.escape(img_rel)}" style="max-width:260px;border:1px solid #cbd5e1;border-radius:4px;" /></td>
              <td>
                <select onchange="setDec({idx}, this.value)">
                  <option value="pending">Pending</option>
                  <option value="accept">Accept</option>
                  <option value="reject">Reject</option>
                  <option value="keep_unknown">Keep Unknown</option>
                </select>
              </td>
            </tr>""")
        return "".join(out)

    html_doc = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>Day 12 · G12 Visual Attribute Review</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; padding: 20px 28px; font-size: 14px; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
    .pill {{ padding: 2px 8px; border-radius: 999px; background: #e2e8f0; font-size: 12px; font-weight: 600; }}
    .pill.prop {{ background: #dbeafe; color: #1e40af; }}
  </style>
</head>
<body>
  <h1>Lab Day 12 · G12 Visual Attribute Review</h1>
  <p>Task 62 / Job 61 · <a href="http://localhost:8080/tasks/62/jobs/61" target="_blank">http://localhost:8080/tasks/62/jobs/61</a></p>
  <div class="card">
    <h2>Needs Human Review ({len(review_rows)} cases)</h2>
    <table>
      <thead><tr><th>Image</th><th>Label</th><th>Attribute</th><th>Current &rarr; Proposed</th><th>Visual Evidence &amp; Reason</th><th>Preview</th><th>Decision</th></tr></thead>
      <tbody>{render_rows(review_rows)}</tbody>
    </table>
  </div>
  <div class="card">
    <h2>Auto-Apply Candidates ({len(auto_rows)} cases)</h2>
    <table>
      <thead><tr><th>Image</th><th>Label</th><th>Attribute</th><th>Current &rarr; Proposed</th><th>Visual Evidence &amp; Reason</th><th>Preview</th><th>Status</th></tr></thead>
      <tbody>{render_rows(auto_rows)}</tbody>
    </table>
  </div>
  <script>
    const decs = JSON.parse(localStorage.getItem('day12_attr_decs') || '{{}}');
    function setDec(i, v) {{ decs[i] = v; localStorage.setItem('day12_attr_decs', JSON.stringify(decs)); }}
  </script>
</body>
</html>"""
    out_path.write_text(html_doc, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Apply AUTO-APPLY CANDIDATE enum changes to CVAT Task 62")
    args = ap.parse_args()

    url, token = load_local_env()
    audit_rows: list[dict[str, Any]] = []
    applied_count = 0

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

        for sh in raw.get("shapes", []):
            fname = frames.get(sh["frame"], "")
            lname = label_by_id[sh["label_id"]].name
            sid = sh.get("id")
            rules = VISION_DECISIONS.get(fname, [])
            for rule in rules:
                if rule["label"] != lname:
                    continue
                if "seat" in rule:
                    seat_val = get_attr(sh["attributes"], attr_id(lname, "seat"))
                    if seat_val != rule["seat"]:
                        continue
                if "side" in rule:
                    side_val = get_attr(sh["attributes"], attr_id(lname, "side"))
                    if side_val != rule["side"]:
                        continue

                aname = rule["attr"]
                if aname.startswith("_"):
                    audit_rows.append({
                        "image_id": fname, "shape_id": sid, "label": lname, "attribute": aname,
                        "old_value": lname, "proposed_value": rule["proposed"],
                        "confidence": rule["conf"], "visible_evidence": rule["evidence"],
                        "reason": rule["reason"], "review_status": rule["status"], "action": "flag_for_human",
                    })
                    continue

                aid = attr_id(lname, aname)
                old_val = get_attr(sh["attributes"], aid)
                prop_val = rule["proposed"]
                status = rule["status"]
                if old_val == prop_val:
                    status = "KEEP CURRENT"
                    action = "none"
                elif status == "AUTO-APPLY CANDIDATE":
                    action = "apply" if args.apply else "dry_run_apply"
                    if args.apply:
                        set_attr(sh["attributes"], aid, prop_val)
                        applied_count += 1
                else:
                    action = "human_review"

                audit_rows.append({
                    "image_id": fname, "shape_id": sid, "label": lname, "attribute": aname,
                    "old_value": old_val, "proposed_value": prop_val,
                    "confidence": rule["conf"], "visible_evidence": rule["evidence"],
                    "reason": rule["reason"], "review_status": status, "action": action,
                })

        if args.apply and applied_count > 0:
            # Strip IDs for PUT update
            for t in raw.get("tags", []):
                t.pop("id", None)
            for sh in raw.get("shapes", []):
                sh.pop("id", None)
                if sh.get("elements"):
                    for el in sh["elements"]:
                        el.pop("id", None)
            task.set_annotations(models.LabeledDataRequest(**raw))
            rb = task.get_annotations()
            print(f"Applied {applied_count} attribute updates to Task 62. Read-back: tags={len(rb.tags)}, shapes={len(rb.shapes)}")
            out_zip = REPO_ROOT / "export_final.zip"
            if out_zip.exists():
                out_zip.unlink()
            task.export_dataset("CVAT for images 1.1", str(out_zip), include_images=False)
            print(f"Re-exported export_final.zip (sha256={sha256_file(out_zip)})")
        else:
            print(f"Dry-run complete: {len(audit_rows)} audited items, {sum(1 for r in audit_rows if r['review_status']=='AUTO-APPLY CANDIDATE')} auto-apply candidates.")

    (REPO_ROOT / "attribute_audit.json").write_text(json.dumps(audit_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(REPO_ROOT / "attribute_changes.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["image_id", "shape_id", "label", "attribute", "old_value", "proposed_value", "confidence", "visible_evidence", "reason", "review_status", "action"])
        w.writeheader()
        w.writerows(audit_rows)
    build_needs_review_html(audit_rows, REPO_ROOT / "needs_review.html")


if __name__ == "__main__":
    main()
