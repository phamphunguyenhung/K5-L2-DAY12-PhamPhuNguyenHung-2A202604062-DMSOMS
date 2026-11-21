#!/usr/bin/env python3
"""Render local visual overlays + Light Mode Web Review UI for Day 12 (G12)."""
from __future__ import annotations

import hashlib
import html
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from cabin_schema import FACE13_EDGES  # noqa: E402

COLORS = {
    "person": (37, 99, 235),       # blue
    "face": (22, 163, 74),         # green
    "face13": (234, 88, 12),       # orange
    "hand": (147, 51, 234),        # purple
    "phone": (220, 38, 38),        # red
    "child_seat": (13, 148, 136),  # teal
    "infant_seat": (202, 138, 4),  # amber
    "object": (79, 70, 229),       # indigo
}


def sha256_file(path: Path) -> str:
    if not path.exists():
        return "missing"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def draw_overlay(img_path: Path, rec: dict[str, Any], out_path: Path) -> None:
    bgr = cv2.imread(str(img_path))
    if bgr is None:
        return
    vis = bgr.copy()
    for b in rec.get("boxes", []):
        lbl = b["label"]
        rgb = COLORS.get(lbl, (51, 65, 85))
        col = (rgb[2], rgb[1], rgb[0])  # BGR
        x1, y1, x2, y2 = [int(round(v)) for v in b["xyxy"]]
        cv2.rectangle(vis, (x1, y1), (x2, y2), col, 2)
        tag = lbl
        if "seat" in b.get("attrs", {}):
            tag += f"[{b['attrs']['seat']}]"
        elif "side" in b.get("attrs", {}):
            tag += f"[{b['attrs']['side']}]"
        elif "type" in b.get("attrs", {}):
            tag += f"[{b['attrs']['type']}]"
        tag += f" {b.get('confidence', 0):.2f}"
        cv2.putText(vis, tag, (x1, max(18, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, col, 2, cv2.LINE_AA)

    for s in rec.get("skeletons", []):
        pts = s["points"]
        for a, b in FACE13_EDGES:
            pa, pb = pts.get(a), pts.get(b)
            if pa and pb and pa["outside"] == "0" and pb["outside"] == "0":
                cv2.line(vis, (int(pa["x"]), int(pa["y"])), (int(pb["x"]), int(pb["y"])), (255, 165, 0), 1, cv2.LINE_AA)
        for pname, p in pts.items():
            if p["outside"] == "1":
                continue
            pt = (int(round(p["x"])), int(round(p["y"])))
            c = (0, 0, 255) if p["occluded"] == "1" else (0, 255, 255)
            cv2.circle(vis, pt, 3, c, -1, cv2.LINE_AA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis)


def build_review_ui(draft_json: Path, ui_dir: Path, check_txt: Path | None = None) -> Path:
    data = json.loads(draft_json.read_text(encoding="utf-8"))
    images = data["images"]
    ui_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir = ui_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    g12_dir = REPO_ROOT / "G12"
    rows = []
    error_queue = []
    total_boxes = 0
    total_skels = 0
    total_time = 0.0

    for rec in images:
        src = g12_dir / rec["rel_path"]
        ov = overlays_dir / rec["name"]
        draw_overlay(src, rec, ov)
        total_boxes += len(rec["boxes"])
        total_skels += len(rec["skeletons"])
        total_time += rec.get("inference_sec", 0.0)

        # Collect quality flags for Error Queue
        low_conf = [b for b in rec["boxes"] if b.get("confidence", 1.0) < 0.40]
        for b in low_conf:
            error_queue.append({
                "frame": rec["name"],
                "type": "low_confidence",
                "label": b["label"],
                "detail": f"{b['label']} conf={b['confidence']} ({b['model_name']})",
            })
        persons = [b for b in rec["boxes"] if b["label"] == "person"]
        faces = [b for b in rec["boxes"] if b["label"] == "face"]
        if persons and not faces:
            error_queue.append({
                "frame": rec["name"],
                "type": "missing_face",
                "label": "face",
                "detail": f"{len(persons)} person(s) detected without face box",
            })

        rows.append({
            "name": rec["name"],
            "rel_orig": f"../G12/{rec['rel_path']}",
            "rel_overlay": f"overlays/{rec['name']}",
            "width": rec["width"],
            "height": rec["height"],
            "inference_sec": rec.get("inference_sec", 0),
            "tags": rec["tags"],
            "boxes": rec["boxes"],
            "skeletons": rec["skeletons"],
        })

    check_summary = check_txt.read_text(encoding="utf-8") if (check_txt and check_txt.exists()) else "Not run yet"
    export_sha = sha256_file(REPO_ROOT / "export_final.zip")

    payload_json = json.dumps({
        "run_id": data["run_id"],
        "images": rows,
        "error_queue": error_queue,
        "export_sha256": export_sha,
        "check_summary": check_summary,
    }, ensure_ascii=False)

    html_doc = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Day 12 · G12 DMS/OMS Review UI</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f8fafc; color: #0f172a; font-size: 14px; }}
    header {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }}
    .nav {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .nav button {{ height: 38px; padding: 0 16px; border: 1px solid #cbd5e1; background: #ffffff; color: #0f172a; border-radius: 6px; cursor: pointer; font-weight: 600; }}
    .nav button.active {{ background: #1d4ed8; color: #ffffff; border-color: #1d4ed8; }}
    main {{ width: 100%; padding: 20px 24px; }}
    .tab-pane {{ display: none; }}
    .tab-pane.active {{ display: block; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }}
    .kpi {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }}
    .kpi .val {{ font-size: 28px; font-weight: 800; color: #0f172a; margin-top: 4px; }}
    .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    .review-layout {{ display: grid; grid-template-columns: 280px 1fr 340px; gap: 16px; align-items: start; }}
    @media (max-width: 1100px) {{ .review-layout {{ grid-template-columns: 1fr; }} }}
    .frame-list {{ max-height: 75vh; overflow-y: auto; }}
    .frame-item {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
    .frame-item:hover, .frame-item.active {{ background: #eff6ff; }}
    .pill {{ padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; background: #e2e8f0; color: #334155; }}
    .pill.approved {{ background: #dcfce7; color: #166534; }}
    .pill.rejected {{ background: #fee2e2; color: #991b1b; }}
    .pill.flagged {{ background: #fef3c7; color: #92400e; }}
    .btn {{ height: 38px; padding: 0 14px; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; font-weight: 600; background: #ffffff; }}
    .btn-approve {{ background: #16a34a; color: #ffffff; border-color: #16a34a; }}
    .btn-reject {{ background: #dc2626; color: #ffffff; border-color: #dc2626; }}
    .btn-flag {{ background: #d97706; color: #ffffff; border-color: #d97706; }}
    .viewer-img {{ width: 100%; height: auto; border: 1px solid #cbd5e1; border-radius: 6px; cursor: zoom-in; }}
    .viewer-img.zoomed {{ width: 160%; max-width: none; cursor: zoom-out; }}
    table {{ width: 100%; border-collapse: collapse; background: #ffffff; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
    th {{ background: #f1f5f9; font-weight: 700; }}
    pre {{ background: #f1f5f9; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: 13px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1 style="margin:0;font-size:20px;">Lab Day 12 · G12 DMS &amp; OMS Review Console</h1>
      <div style="color:#475569;font-size:13px;">Run: <code>{html.escape(data['run_id'])}</code> · 22 Core Frames (Local-Only)</div>
    </div>
    <div class="nav">
      <button class="active" onclick="showTab('dashboard', this)">1. Dashboard</button>
      <button onclick="showTab('review', this)">2. Image Review</button>
      <button onclick="showTab('errors', this)">3. Error Queue ({len(error_queue)})</button>
      <button onclick="showTab('sync', this)">4. CVAT Sync</button>
      <button onclick="showTab('export', this)">5. Export Center</button>
    </div>
  </header>
  <main>
    <section id="tab-dashboard" class="tab-pane active">
      <div class="kpi-grid">
        <div class="kpi"><div>Tổng ảnh cốt lõi</div><div class="val">{len(images)}</div></div>
        <div class="kpi"><div>Tổng Box Draft</div><div class="val">{total_boxes}</div></div>
        <div class="kpi"><div>Face13 Skeletons</div><div class="val">{total_skels}</div></div>
        <div class="kpi"><div>Đã duyệt (Local)</div><div class="val" id="kpi-approved">0</div></div>
        <div class="kpi"><div>Từ chối / Flag</div><div class="val" id="kpi-flagged">0</div></div>
        <div class="kpi"><div>Tổng thời gian Inference</div><div class="val">{total_time:.1f}s</div></div>
      </div>
      <div class="card">
        <h3>Tiến độ &amp; Trạng thái</h3>
        <p>Tất cả 22 ảnh (16 OMS + 6 DMS) đã được chạy inference cục bộ (YOLO26l + GroundingDINO-tiny + S3FD/FAN2D). Vui lòng kiểm tra từng ảnh ở tab <strong>Image Review</strong> trước khi nộp.</p>
      </div>
    </section>

    <section id="tab-review" class="tab-pane">
      <div class="review-layout">
        <div class="card frame-list" id="frame-list"></div>
        <div class="card" style="overflow:auto;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
            <strong id="cur-title">-</strong>
            <div style="display:flex;gap:8px;">
              <button class="btn" onclick="toggleMode()">Toggle Original / Overlay</button>
              <button class="btn btn-approve" onclick="setStatus('approved')">Approve</button>
              <button class="btn btn-flag" onclick="setStatus('flagged')">Flag</button>
              <button class="btn btn-reject" onclick="setStatus('rejected')">Reject</button>
            </div>
          </div>
          <img id="cur-img" class="viewer-img" onclick="this.classList.toggle('zoomed')" />
        </div>
        <div class="card">
          <h3 style="margin-top:0;">Annotations &amp; Provenance</h3>
          <div id="cur-meta"></div>
        </div>
      </div>
    </section>

    <section id="tab-errors" class="tab-pane">
      <div class="card">
        <h3>Error &amp; Uncertainty Queue ({len(error_queue)} items)</h3>
        <table>
          <thead><tr><th>Frame</th><th>Type</th><th>Label</th><th>Detail</th></tr></thead>
          <tbody id="err-tbody"></tbody>
        </table>
      </div>
    </section>

    <section id="tab-sync" class="tab-pane">
      <div class="card">
        <h3>CVAT Sync &amp; Read-Back</h3>
        <p><strong>Target CVAT:</strong> <code>http://localhost:8080</code> (Dry-run / Local XML Ready)</p>
        <p>Sử dụng <code>export_final.zip</code> (CVAT for images 1.1, không kèm ảnh) để import hoặc đồng bộ khi CVAT Docker Desktop hoạt động.</p>
        <button class="btn" onclick="exportDecisions()">Export Human Review Decisions JSON</button>
      </div>
    </section>

    <section id="tab-export" class="tab-pane">
      <div class="card">
        <h3>Export Center &amp; SHA-256 Verification</h3>
        <p><strong>export_final.zip SHA-256:</strong> <code>{export_sha}</code></p>
        <h4>cabin_check.py Output:</h4>
        <pre>{html.escape(check_summary)}</pre>
      </div>
    </section>
  </main>
  <script>
    const DATA = {payload_json};
    let curIdx = 0;
    let showOverlay = true;
    const decisions = JSON.parse(localStorage.getItem('day12_g12_decisions') || '{{}}');

    function showTab(id, btn) {{
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + id).classList.add('active');
      btn.classList.add('active');
    }}

    function updateKPIs() {{
      const vals = Object.values(decisions);
      document.getElementById('kpi-approved').textContent = vals.filter(v => v === 'approved').length;
      document.getElementById('kpi-flagged').textContent = vals.filter(v => v === 'flagged' || v === 'rejected').length;
    }}

    function renderList() {{
      const el = document.getElementById('frame-list');
      el.innerHTML = DATA.images.map((im, i) => {{
        const st = decisions[im.name] || 'pending';
        return `<div class="frame-item ${{i===curIdx?'active':''}}" onclick="selectFrame(${{i}})">
          <span>${{im.name}}</span><span class="pill ${{st}}">${{st}}</span>
        </div>`;
      }}).join('');
    }}

    function selectFrame(i) {{
      curIdx = i;
      const im = DATA.images[i];
      document.getElementById('cur-title').textContent = `${{im.name}} (${{im.width}}x${{im.height}}) · ${{im.inference_sec}}s`;
      document.getElementById('cur-img').src = showOverlay ? im.rel_overlay : im.rel_orig;
      const tagHtml = im.tags.map(t => `<div><strong>Tag:</strong> <code>${{t.label}}</code> ${{JSON.stringify(t.attrs)}}</div>`).join('');
      const boxHtml = im.boxes.map(b => `<div style="padding:6px 0;border-bottom:1px solid #f1f5f9;">
        <strong>${{b.label}}</strong> (conf: ${{b.confidence}}, <code>${{b.model_name}}</code>)<br/>
        <small>${{JSON.stringify(b.attrs)}}</small>
      </div>`).join('');
      const skelHtml = im.skeletons.map(s => `<div style="padding:6px 0;"><strong>${{s.label}}</strong> (13 pts, <code>${{s.model_name}}</code>)</div>`).join('');
      document.getElementById('cur-meta').innerHTML = tagHtml + boxHtml + skelHtml;
      renderList();
    }}

    function toggleMode() {{
      showOverlay = !showOverlay;
      selectFrame(curIdx);
    }}

    function setStatus(st) {{
      decisions[DATA.images[curIdx].name] = st;
      localStorage.setItem('day12_g12_decisions', JSON.stringify(decisions));
      updateKPIs();
      renderList();
    }}

    function exportDecisions() {{
      const blob = new Blob([JSON.stringify(decisions, null, 2)], {{type: 'application/json'}});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'g12_review_decisions.json';
      a.click();
    }}

    document.getElementById('err-tbody').innerHTML = DATA.error_queue.map(e =>
      `<tr><td>${{e.frame}}</td><td><code>${{e.type}}</code></td><td>${{e.label}}</td><td>${{e.detail}}</td></tr>`
    ).join('') || '<tr><td colspan="4">No errors queued.</td></tr>';

    updateKPIs();
    selectFrame(0);
  </script>
</body>
</html>"""
    out_html = ui_dir / "index.html"
    out_html.write_text(html_doc, encoding="utf-8")
    return out_html


if __name__ == "__main__":
    draft = REPO_ROOT / "artifacts" / "g12_run" / "draft_annotations.json"
    chk = REPO_ROOT / "check_final.txt"
    out = build_review_ui(draft, REPO_ROOT / "review_ui", chk)
    print("Review UI written to:", out)
