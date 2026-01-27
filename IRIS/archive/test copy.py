import requests

url = "https://standards-oui.ieee.org/oui/oui.txt"
output_file = "oui.txt"

response = requests.get(url)
if response.status_code == 200:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Downloaded to {output_file}")
else:
    print(f"Failed to download. Status code: {response.status_code}")