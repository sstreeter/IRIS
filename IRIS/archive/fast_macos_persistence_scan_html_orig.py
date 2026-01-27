import json
from fast_macos_persistence_scan import main

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>macOS Persistence Scan Report</title>
<style>
  body {{ font-family: Arial, sans-serif; background: #f8f8f8; color: #222; }}
  h1 {{ background: #003366; color: white; padding: 1em; }}
  .section {{ margin: 20px; padding: 10px; background: white; border-radius: 8px; box-shadow: 0 0 5px #ccc; }}
  .suspicious {{ color: red; font-weight: bold; }}
  pre {{ background: #eee; padding: 10px; border-radius: 4px; overflow-x: auto; }}
</style>
</head>
<body>
<h1>macOS Persistence Scan Report</h1>

{sections}

</body>
</html>
"""

def highlight_malware(text):
    """Highlight known malware indicators like curl payloads etc."""
    indicators = [
        r'(curl\s+http[^\s]+)',
        r'(wget\s+http[^\s]+)',
        r'(python3?\s+-c\s+.+)',
        r'(launchctl\s+load\s+.+)',
        r'(base64\s+-d\s+.+)',
        r'(osascript\s+-e\s+.+)',
    ]
    for pattern in indicators:
        text = re.sub(pattern, r'<span class="suspicious">\1</span>', text, flags=re.I)
    return text

def generate_section(title, items):
    if not items:
        content = "<p>No suspicious items found.</p>"
    else:
        content = "<ul>"
        for item in items:
            safe_item = item.replace("<", "&lt;").replace(">", "&gt;")
            highlighted = highlight_malware(safe_item)
            content += f"<li>{highlighted}</li>"
        content += "</ul>"
    return f'<div class="section"><h2>{title}</h2>{content}</div>'

def generate_html_report(results):
    sections_html = ""
    for section, items in results.items():
        sections_html += generate_section(section, items)
    return HTML_TEMPLATE.format(sections=sections_html)

if __name__ == "__main__":
    import re
    results = main()
    html_report = generate_html_report(results)
    output_file = "macos_persistence_scan_report.html"
    with open(output_file, "w") as f:
        f.write(html_report)
    print(f"HTML report generated: {output_file}")
