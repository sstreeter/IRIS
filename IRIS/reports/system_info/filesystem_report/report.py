from typing import Any
from IRIS.helpers import Helpers

from .scan import scan_user_directories
from .enrich import enrich_files, serialize_files
from .render import render_report


def generate_images_report(
    app_instance: Any,
    helpers: Helpers,
    browser_preference: str = "System Default",
) -> None:
    app_instance.log_output(
        "\n--- Generating Advanced Filesystem Artifacts Report ---"
    )

    files = scan_user_directories(app_instance)

    report_dir = getattr(
        app_instance, "report_output_directory", "reports"
    )

    enrich_files(files, app_instance, report_dir)

    json_data = serialize_files(files)

    render_report(
        app_instance,
        helpers,
        json_data,
        browser_preference=browser_preference,
    )
