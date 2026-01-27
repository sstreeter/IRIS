import os
from pathlib import Path
import logging
import subprocess
import sys

# --- Configure logging to output to console ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Define the root directory where IRISX_app will be created
# Set this to your desired location, e.g., "/Users/spencer/Documents/Python/"
# IMPORTANT: On Windows, use forward slashes (/) or double backslashes (\\)
# Example for Windows: PROJECT_ROOT = "C:/Users/YourUsername/Documents/PythonProjects/"
# Example for macOS/Linux: PROJECT_ROOT = "/Users/spencer/Documents/Python/"
PROJECT_ROOT = "/Users/spencer/Documents/Python/"  # <<< PLEASE VERIFY/ADJUST THIS PATH FOR YOUR SYSTEM >>>
APP_DIR_NAME = "IRISX_app"

app_path = Path(PROJECT_ROOT) / APP_DIR_NAME
utils_path = app_path / "utils"
modules_path = app_path / "modules"
requirements_file_path = Path(PROJECT_ROOT) / "requirements.txt" # New: Path for requirements.txt

# --- Logging paths before action ---
logger.info(f"🚀 Starting project creation for '{APP_DIR_NAME}'.")
logger.info(f"Target project root directory: '{PROJECT_ROOT}'")
logger.info(f"Full application path will be: '{app_path}'")
logger.info(f"Utils module path will be: '{utils_path}'")
logger.info(f"Modules package path will be: '{modules_path}'")
logger.info(f"Requirements file will be: '{requirements_file_path}'") # New: Log requirements file path
logger.info("-" * 50)

# --- Content for each file (These are now placeholders, actual content comes from .txt files) ---
# The content variables are still defined for clarity in how they are referenced,
# but the script will *read* from the .txt files.
helpers_content = ""
system_diagnostics_content = ""
main_app_content = ""
requirements_content = "requests\n" # New: Content for requirements.txt

# --- Directory and file creation logic ---
try:
    logger.info(f"Creating application directory: '{app_path}'")
    app_path.mkdir(parents=True, exist_ok=True)
    if app_path.exists():
        logger.info(f"✅ Directory '{app_path}' created or already exists.")
    else:
        logger.error(
            f"❌ Failed to create directory '{app_path}'. Check permissions.")
        sys.exit(1)

    logger.info(f"Creating utils directory: '{utils_path}'")
    utils_path.mkdir(exist_ok=True)
    if utils_path.exists():
        logger.info(f"✅ Directory '{utils_path}' created or already exists.")
    else:
        logger.error(
            f"❌ Failed to create directory '{utils_path}'. Check permissions.")
        sys.exit(1)

    logger.info(f"Creating modules directory: '{modules_path}'")
    modules_path.mkdir(exist_ok=True)
    if modules_path.exists():
        logger.info(f"✅ Directory '{modules_path}' created or already exists.")
    else:
        logger.error(
            f"❌ Failed to create directory '{modules_path}'. Check permissions."
        )
        sys.exit(1)

    logger.info("-" * 50)
    logger.info("✍️ Writing Python files from external content files...")

    # Define paths to the content files (assuming they are in the same directory as this script)
    script_dir = Path(__file__).parent

    # Mapping source .txt files to their destination .py files
    files_to_read_and_create = {
        script_dir / "helpers_content.txt": utils_path / "helpers.py",
        script_dir / "system_diagnostics_content.txt":
        modules_path / "system_diagnostics.py",
        script_dir / "main_app_content.txt": app_path / "main_app.py"
    }

    # Add __init__.py files which are empty but necessary for Python packages
    empty_init_files = [
        app_path / "__init__.py", utils_path / "__init__.py",
        modules_path / "__init__.py"
    ]

    for source_file, destination_file in files_to_read_and_create.items():
        try:
            logger.info(
                f"  Reading content from '{source_file}' and writing to '{destination_file}'"
            )
            content = source_file.read_text(encoding='utf-8')
            with open(destination_file, "w", encoding='utf-8') as f:
                f.write(content)
            logger.info(f"  ✅ Successfully wrote '{destination_file}'.")
        except FileNotFoundError:
            logger.error(
                f"  ❌ Error: Source content file '{source_file}' not found. Please ensure it exists in the same directory as this script."
            )
            sys.exit(1)
        except Exception as e:
            logger.error(f"  ❌ Error writing file '{destination_file}': {e}")

    # Write empty __init__.py files
    for init_file_path in empty_init_files:
        try:
            logger.info(
                f"  Creating empty __init__.py file: '{init_file_path}'")
            with open(init_file_path, "w") as f:
                f.write("")  # Create an empty file
            logger.info(f"  ✅ Successfully created '{init_file_path}'.")
        except Exception as e:
            logger.error(
                f"  ❌ Error creating __init__.py file '{init_file_path}': {e}")

    # New: Write requirements.txt
    try:
        logger.info(f"  Creating requirements.txt file: '{requirements_file_path}'")
        with open(requirements_file_path, "w", encoding='utf-8') as f:
            f.write(requirements_content)
        logger.info(f"  ✅ Successfully created '{requirements_file_path}'.")
    except Exception as e:
        logger.error(f"  ❌ Error creating requirements.txt: {e}")

    logger.info("-" * 50)
    logger.info("🎉 Project creation script finished.")
    logger.info(
        f"You can now run the main application from: '{app_path / 'main_app.py'}'"
    )
    logger.info(
        f"Before running, please install the required dependencies using: 'pip install -r {requirements_file_path}'"
    )

except Exception as e:
    logger.critical(f"A critical error occurred during project setup: {e}")

if app_path.exists() and (app_path / "main_app.py").exists():
    logger.info("Attempting to launch the IRIS Rapid Response GUI now...")
    try:
        # Before launching, remind user to install dependencies
        logger.info("Please ensure you have installed dependencies: 'pip install -r requirements.txt'")
        subprocess.Popen([sys.executable, "-m", "IRISX_app.main_app"],
                         cwd=PROJECT_ROOT)
        logger.info(
            f"GUI launch command sent with cwd='{PROJECT_ROOT}'. Check for a new window."
        )
    except Exception as e:
        logger.error(f"Failed to launch main_app.py: {e}")
        logger.info(
            f"Please navigate to '{PROJECT_ROOT}' and run 'python3 -m IRISX_app.main_app' manually."
        )
else:
    logger.warning(
        "main_app.py was not found after creation. GUI will not be launched automatically."
    )
