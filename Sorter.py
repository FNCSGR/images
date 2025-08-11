import json

source = input("Where is the base JSON located? \n").strip()
character = input("Which character name do you wish to sort for? \n").strip()
artist = input("Which artist is being sorted? \n").strip()

# Read the JSON file
with open(f"{source}/defines/{artist}.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter only entries that have the character tag
filtered = [item for item in data if character in item.get("tags", [])]

# Write the filtered result to a new file (pretty-printed)
with open(f"{character}/defines/{artist}.json", "w", encoding="utf-8") as f:
    json.dump(filtered, f, indent=2, ensure_ascii=False)
