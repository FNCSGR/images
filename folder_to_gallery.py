import os
import json

IMAGE_DIR = "new_images"
OUTPUT_FILE = "new_gallery.json"

def guess_tags(filename):
    # Example: "sunset_beach.jpg" → ["sunset", "beach"]
    name = os.path.splitext(filename)[0]
    tags = name.replace("-", "_").replace(".", "_").split("_")
    return [tag.lower() for tag in tags if tag.isalpha()]

def load_existing_entries():
    if not os.path.exists(OUTPUT_FILE):
        return {}
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return {entry["src"]: entry for entry in data}
        except json.JSONDecodeError:
            print("⚠️ Warning: existing JSON file is corrupted. Starting fresh.")
            return {}

def main():
    current_files = {
        f"{IMAGE_DIR}/{filename}"
        for filename in os.listdir(IMAGE_DIR)
        if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
    }

    existing = load_existing_entries()
    updated = {}

    for path in current_files:
        if path in existing:
            updated[path] = existing[path]
        else:
            filename = os.path.basename(path)
            updated[path] = {
                "src": path,
                "alt": filename,
                "tags": ["untagged"] # guess_tags(filename) 
            }

    # Optionally: warn about removed images
    removed = set(existing.keys()) - current_files
    if removed:
        print(f"🗑️ Removing {len(removed)} missing image(s):")
        for r in removed:
            print(f"  - {r}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(updated.values()), f, indent=2)

    print(f"✅ Synced {len(updated)} image(s) to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
