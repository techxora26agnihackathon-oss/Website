import os

directory = r"c:\SAM\Projects\Hackathon 26"
replacements = [
    ("TECHXORA", "TECHXORA"),
    ("TECHXORA", "TECHXORA"),
    ("TECHXORA", "TECHXORA"),
    ("techxora", "techxora")
]

for root, dirs, files in os.walk(directory):
    if ".git" in root or "__pycache__" in root or "instance" in root or ".gemini" in root:
        continue
    for file in files:
        if file.endswith((".html", ".js", ".css", ".py")):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                original_content = content
                for old, new in replacements:
                    content = content.replace(old, new)
                
                if content != original_content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"Updated {filepath}")
            except Exception as e:
                print(f"Skipping {filepath}: {e}")
