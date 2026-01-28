import os
import json
import hashlib
import subprocess
from datetime import datetime
from typing import Dict, List, Any


def get_partial_hash(file_path: str, chunk_size: int = 4096) -> str:
    try:
        size = os.path.getsize(file_path)
        if size == 0:
            return "empty"

        with open(file_path, "rb") as f:
            start = f.read(chunk_size)
            if size > chunk_size:
                f.seek(-chunk_size, 2)
                end = f.read(chunk_size)
            else:
                end = b""

        return hashlib.md5(start + end).hexdigest()

    except Exception:
        return "error"


def format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0

    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.2f} {units[i]}"


def analyze_duplicates(files: List[Dict[str, Any]]) -> None:
    by_size: Dict[int, List[Dict[str, Any]]] = {}

    for f in files:
        if f["category"] != "disk_image":
            continue

        by_size.setdefault(f["size"], []).append(f)

    for sublist in by_size.values():
        if len(sublist) <= 1:
            continue

        by_hash: Dict[str, List[Dict[str, Any]]] = {}
        for f in sublist:
            ph = get_partial_hash(f["path"])
            by_hash.setdefault(ph, []).append(f)

        for ph, dupes in by_hash.items():
            if len(dupes) > 1:
                gid = ph[:8]
                for d in dupes:
                    d["dup_group"] = gid


def enrich_files(
    files: List[Dict[str, Any]],
    app_instance: Any,
    report_dir: str,
    thumb_limit: int = 300,
) -> None:
    analyze_duplicates(files)

    for f in files:
        f["formatted_size"] = format_size(f["size"])
        f["formatted_date"] = datetime.fromtimestamp(
            f["mtime"]
        ).strftime("%Y-%m-%d %H:%M")
        f["file_url"] = f"file://{f['path']}"

    thumbs_dir = os.path.join(report_dir, "thumbs")
    os.makedirs(thumbs_dir, exist_ok=True)

    app_instance.log_output(
        f"Generating thumbnails in {thumbs_dir} (Limit {thumb_limit})..."
    )

    try:
        subprocess.run(
            ["sips", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        has_sips = True
    except Exception:
        has_sips = False

    if not has_sips:
        return

    priority_exts = {".jpeg", ".jpg", ".png"}
    files.sort(
        key=lambda x: (
            x["ext"].lower() not in priority_exts,
            x["ext"].lower(),
        )
    )

    # Prepare list of files that need thumbnails
    files_to_process = []
    for f in files:
        if f["category"] == "media_file" and len(files_to_process) < thumb_limit:
            safe_name = hashlib.md5(f["path"].encode()).hexdigest() + ".jpg"
            thumb_path = os.path.join(thumbs_dir, safe_name)
            
            # Only process if thumbnail doesn't exist
            if not os.path.exists(thumb_path):
                files_to_process.append((f, thumb_path, safe_name))
            else:
                # Thumbnail already exists, just set the URL
                f["thumb_url"] = f"thumbs/{safe_name}"

    if not files_to_process:
        return

    app_instance.log_output(
        f"Generating {len(files_to_process)} new thumbnails using parallel processing..."
    )

    # Parallel thumbnail generation
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import multiprocessing
    
    # Optimal thread count: CPU cores * 2 (I/O bound task)
    # Cap at 25 as user suggested, min 4 for reasonable parallelism
    cpu_count = multiprocessing.cpu_count()
    max_workers = min(max(cpu_count * 2, 4), 25)
    
    def generate_thumbnail(file_info):
        f, thumb_path, safe_name = file_info
        try:
            subprocess.run(
                [
                    "sips",
                    "-Z",
                    "512",
                    "-s",
                    "format",
                    "jpeg",
                    "-s",
                    "formatOptions",
                    "high",
                    f["path"],
                    "--out",
                    thumb_path,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=4,
            )
            
            if os.path.exists(thumb_path):
                return (f, safe_name, True)
            return (f, safe_name, False)
        except Exception:
            return (f, safe_name, False)
    
    # Process thumbnails in parallel
    success_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(generate_thumbnail, info): info for info in files_to_process}
        
        for future in as_completed(futures):
            f, safe_name, success = future.result()
            if success:
                f["thumb_url"] = f"thumbs/{safe_name}"
                success_count += 1
    
    app_instance.log_output(
        f"Generated {success_count}/{len(files_to_process)} thumbnails using {max_workers} threads"
    )


def serialize_files(files: List[Dict[str, Any]]) -> str:
    return json.dumps(files, ensure_ascii=False)
