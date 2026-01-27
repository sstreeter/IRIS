# IRIS (Incident Response & Investigation System)

**IRIS** is your personal security assistant. It scans your Mac to help you find viruses, hackers, or just see what is running on your computer. It creates easy-to-read reports so you can understand what is happening under the hood.

---

## 🚀 How to Run IRIS (Step-by-Step)

Follow these steps exactly. You only need to do the "Setup" once.

### Part 1: First-Time Setup
*(Do this only the first time you download the app)*

1.  **Open the Terminal**
    *   Press `Command` + `Space` on your keyboard.
    *   Type `Terminal` and hit Enter.

2.  **Go to the App Folder**
    *   Copy this command, paste it into the Terminal, and hit Enter:
        ```bash
        cd ~/Projects/python/IRISX
        ```

3.  **Create the Safety Box (Virtual Environment)**
    *   This keeps the app separate from your other files. Copy and paste:
        ```bash
        python3 -m venv venv
        ```

4.  **Turn on the Safety Box**
    *   Copy and paste:
        ```bash
        source venv/bin/activate
        ```
    *   *You should see `(venv)` appear at the start of the line.*

5.  **Install the Tools**
    *   Copy and paste this to get everything IRIS needs to run:
        ```bash
        pip install -r requirements.txt
        ```

---

### Part 2: Starting the App
*(Do this whenever you want to use IRIS)*

1.  **Open Terminal** (if not open).
2.  **Go to the Folder**:
    ```bash
    cd ~/Projects/python/IRISX
    ```
3.  **Activate the Box**:
    ```bash
    source venv/bin/activate
    ```
4.  **Run IRIS**:
    ```bash
    python3 iris_gui.py
    ```

---

## 🛠️ What Can IRIS Do?

Once the window opens, you can click buttons to generate reports. Here are the most useful ones:

*   **🔍 System Info**: Shows your serial number, disk space, and hardware details.
*   **🦠 Antivirus Status**: Checks if your specialized security software (XProtect/MRT) is running.
*   **🌐 Network Config**: Shows your IP address and Wi-Fi connections.
*   **💾 Images Report**: Scans your Downloads and Desktop for Disk Image files (`.iso`, `.dmg`) and Pictures. Great for finding downloaded installers.
*   **⚡ Running Processes**: Shows every program running right now. Red items might be suspicious!

---

## ❓ Troubleshooting (Help!)

**"Command not found"**
> Make sure you typed `source venv/bin/activate` before trying to run the app.

**"Module not found"**
> You might have forgotten to run `pip install -r requirements.txt`. Do that inside the virtual environment.

**It asks for a Password**
> Some checks (like seeing all running processes) need "Administrator" permission. It is safe to type your Mac login password if prompted.

**The screen froze!**
> Scanning thousands of files takes time. Give it 5-10 seconds to finish. It will say "Success" in the log box when done.
