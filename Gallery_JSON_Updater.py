import requests # Library for API calls
import json # Library for JSON structure
import os # Library for handling filepaths
import re # Library for handing file names
from API_Token import API_TOKEN

# Run API call
def fetch_imgchest_post_data(post_id, token):
    # Establish the headers, Image Chest uses bearer authentication tokens.
    headers = {
        "Authorization": "Bearer " + token,
        "User-Agent": "Python/requests"
    }
    # Establish the URL that needs to be called, this consists of the basic component for each post and then the dynamic post ID.
    # The post ID can be found after the /p/ in the normal URL. So in https://imgchest.com/p/vj4jg2pr248 the post ID is vj4jg2pr248
    url = "https://api.imgchest.com/v1/post/" + post_id
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Windows has restrictions on filenames that Image Chest doesn't have on their titles, if present these characters need to be removed.
def sanitize_title(title):
    # Remove characters unsafe for filenames
    return re.sub(r'[\\/*?:"<>|]', '_', title).strip()

# Build the JSON file out of the data received from the API call.
def build_image_list(images_data, title_tag):
    image_list = []
    for item in images_data:
        filename = item.get("original_name", "unknown.png")
        direct_url = item.get("link", "")
        if direct_url:
            image_list.append({
                "src": direct_url,
                "alt": filename,
                "tags": [title_tag]  # Just the post title
            })
    return image_list

# Update the existing JSON if one was found.
def merge_images(existing, new):
    existing_src_set = {img["src"] for img in existing}
    merged = list(existing)
    for img in new:
        if img["src"] not in existing_src_set:
            merged.append(img)
    return merged

# Load the existing JSON, if one exists, so it wont be overridden but updated instead.
def load_existing_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# Export the new JSON file to the defined filepath.
def save_json(images, output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(images, f, indent=2)
    print(f"✅ Saved {len(images)} entries to {output_file}")

project = input("Enter Character name: \n")

# Main
if __name__ == "__main__":
    post_id = input("Enter ImgChest post ID: \n").strip() # Request post ID from user.
    token = API_TOKEN # Statically defined API token, 
    # this value should remain as is unless the API tokens are changed on the site itself.
    if not token:
        token = input("Enter your ImgChest API token: ").strip()

    try:
        post_data = fetch_imgchest_post_data(post_id, token) # Run API call function.
        title_raw = post_data.get("data", {}).get("title", "untitled") # Grab the title from the data received.
        title_clean = sanitize_title(title_raw) # Run the santitization function to ensure title complies with Windows rules for filenames.

        output_file = f"{project}/Defines/{title_clean}.json" # Establish full export filepath.
        title_tag = title_clean # Set up the artist tag based on the post title.

        images_data = post_data.get("data", {}).get("images", []) # Grab the image data from the API call
        new_images = build_image_list(images_data, title_tag) # Build the JSON based on the title and image data.
        existing_images = load_existing_json(output_file) # Load existing JSON if it exists, using the same name. 
        merged_images = merge_images(existing_images, new_images) # Merge the new and old JSON's to ensure updating goes correctly.

        save_json(merged_images, output_file) # Export the new JSON by calling the function.
    except requests.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
