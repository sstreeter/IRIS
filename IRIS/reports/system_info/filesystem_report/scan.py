import os
from datetime import datetime
from typing import Any, Dict, List

DISK_IMAGE_EXTS = {
    ".iso", ".dmg", ".img", ".dd", ".cdr", ".vmdk", ".vmwarevm"
}

MEDIA_EXTS = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
    ".webp", ".heic", ".svg", ".ai", ".eps", ".psd", ".pdf"
}


def scan_user_directories(app_instance: Any) -> List[Dict[str, Any]]:
    found_files: List[Dict[str, Any]] = []

    scan_roots = [
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Public"),
        os.path.expanduser("~/Pictures"),
        "/Applications",
    ]

    tr = getattr(app_instance, "time_range", {})
    t_start = tr.get("start")
    t_end = tr.get("end")

    app_instance.log_output(
        "Scanning user directories for disk images and media..."
    )

    for root_dir in scan_roots:
        if not os.path.exists(root_dir):
            continue

        for root, dirs, files in os.walk(root_dir, topdown=True):
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in ("Library", "node_modules", ".git")
            ]

            for name in files:
                if name.startswith("."):
                    continue

                ext = os.path.splitext(name)[1].lower()
                category = None

                if ext in DISK_IMAGE_EXTS:
                    category = "disk_image"
                elif ext in MEDIA_EXTS:
                    category = "media_file"

                if not category:
                    continue

                full_path = os.path.join(root, name)

                try:
                    stats = os.stat(full_path)

                    if t_start or t_end:
                        mtime_dt = datetime.fromtimestamp(stats.st_mtime)
                        if t_start and mtime_dt < t_start:
                            continue
                        if t_end and mtime_dt > t_end:
                            continue

                    found_files.append(
                        {
                            "name": name,
                            "path": full_path,
                            "size": stats.st_size,
                            "mtime": stats.st_mtime,
                            "ext": ext,
                            "category": category,
                            "dup_group": None,
                        }
                    )

                except Exception:
                    pass

    return found_files
