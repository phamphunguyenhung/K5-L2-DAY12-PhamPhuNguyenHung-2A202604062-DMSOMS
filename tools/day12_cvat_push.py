#!/usr/bin/env python3
"""Create Project Day12, Task Day12-G12 (22 core images), import export_final.zip, and verify read-back."""
from __future__ import annotations

import json
from pathlib import Path

from cvat_sdk import make_client
from cvat_sdk.core.proxies.tasks import ResourceType

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(r"C:\Users\ppnh1\.cvat.env")


def load_local_env() -> tuple[str, str]:
    env = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["CVAT_URL"], env["CVAT_TOKEN"]


def main():
    url, token = load_local_env()
    labels_spec = json.loads((REPO_ROOT / "labels_cabin_v1.json").read_text(encoding="utf-8"))

    g12 = REPO_ROOT / "G12"
    img_paths = sorted([g12 / "oms" / f"S{i:02d}_{m}.png" for i in range(1, 9) for m in ("rgb", "ir")])
    img_paths += sorted([g12 / "driver" / f"D{i:02d}.png" for i in range(1, 7)])
    assert len(img_paths) == 22, f"Expected 22 images, got {len(img_paths)}"

    with make_client(host=url) as client:
        client.api_client.set_default_header("Authorization", f"Token {token}")

        # 1. Find or create Project 'Day12'
        projs = [p for p in client.projects.list() if p.name == "Day12"]
        if projs:
            proj = projs[0]
            print(f"Using existing Project: id={proj.id}, name={proj.name}")
        else:
            proj = client.projects.create(spec={"name": "Day12", "labels": labels_spec})
            print(f"Created Project: id={proj.id}, name={proj.name}")

        # 2. Find or create Task 'Day12-G12'
        tasks = [t for t in client.tasks.list() if t.name == "Day12-G12" and t.project_id == proj.id]
        if tasks:
            task = tasks[0]
            print(f"Using existing Task: id={task.id}, name={task.name}")
        else:
            task = client.tasks.create_from_data(
                spec={"name": "Day12-G12", "project_id": proj.id},
                resource_type=ResourceType.LOCAL,
                resources=[str(p) for p in img_paths],
            )
            print(f"Created Task: id={task.id}, name={task.name}, size={task.size}")

        # 3. Backup existing annotations before import
        ann = task.get_annotations()
        backup_path = REPO_ROOT / "artifacts" / "g12_run" / f"cvat_backup_task_{task.id}.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps(ann.to_dict(), indent=2, default=str), encoding="utf-8")

        # 4. Import export_final.zip (CVAT 1.1)
        zip_path = REPO_ROOT / "export_final.zip"
        task.import_annotations("CVAT 1.1", str(zip_path))
        print(f"Imported {zip_path.name} into Task {task.id}")

        # 5. Read-back verification
        rb = task.get_annotations()
        jobs = task.get_jobs()
        job_id = jobs[0].id if jobs else "?"
        print(f"Read-back Task {task.id}: tags={len(rb.tags)}, shapes={len(rb.shapes)}, tracks={len(rb.tracks)}")
        print(f"CVAT URL: {url}/tasks/{task.id}/jobs/{job_id}")


if __name__ == "__main__":
    main()
