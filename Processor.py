import requests
import json
import os
import re
import copy
import time
import threading
import shutil
from collections import defaultdict
from customtkinter import *
from tkinter import messagebox
from LocalVariables import Token, upload_root, archive_root

# =========================================================
# API
# =========================================================

def create_imgchest_post(title, images_with_meta, token):
    """
    Create a new ImgChest post. The API requires images to be attached
    to the creation request. Descriptions are NOT supported during
    creation and must be applied later via PATCH.

    images_with_meta: [{"path": filepath}]
    Only the first ≤20 images should be provided here.
    """

    url = "https://api.imgchest.com/v1/post"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Python/requests"
    }

    files = []
    data = {"title": title, "privacy": "hidden", "nsfw": "true"}

    for item in images_with_meta:
        path = item["path"]

        files.append(
            ("images[]", (os.path.basename(path), open(path, "rb")))
        )

    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        resp_json = response.json()
        data = resp_json.get("data", {})
        return data.get("id"), resp_json, response.headers
    finally:
        for _, (_, f) in files:
            f.close()


def upload_images_to_post(post_id, images_with_meta, token):
    """
    images_with_meta = [
        {
            "path": filepath,
            "description": "tag1 tag2 ..."  # optional
        }
    ]
    """

    url = f"https://api.imgchest.com/v1/post/{post_id}/add"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Python/requests"
    }

    files = []
    data = {}

    for i, item in enumerate(images_with_meta):
        path = item["path"]
        desc = item.get("description", "")

        files.append(
            ("images[]", (os.path.basename(path), open(path, "rb")))
        )

        if desc:
            data[f"descriptions[{i}]"] = desc

    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        return response.json(), response.headers
    finally:
        for _, (_, f) in files:
            f.close()


def fetch_imgchest_post_data(post_id, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Python/requests"
    }
    url = f"https://api.imgchest.com/v1/post/{post_id}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json(), response.headers.get("X-RateLimit-Remaining")


def get_wait_time(remaining):
    if remaining is None:
        return 0
    remaining = int(remaining)
    return 60 if remaining <= 0 else 0



def patch_image_descriptions(patch_items, token):
    """
    patch_items = [{"id": "image_id", "description": "tags"}]
    """

    if not patch_items:
        return None, {}

    url = "https://api.imgchest.com/v1/files"

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Python/requests",
        "Content-Type": "application/json"
    }

    body = {"data": patch_items}

    response = requests.patch(url, headers=headers, json=body)
    response.raise_for_status()

    return response.json(), response.headers

# =========================================================
# HELPERS
# =========================================================

def sanitize_title(title):
    return re.sub(r'[\\/*?:"<>|]', "_", title).strip()


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(data, path, log):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log(f"Saved {len(data)} entries → {path}")


def merge_images(existing, new):
    seen = {img["src"] for img in existing}
    merged = list(existing)
    for img in new:
        if img["src"] not in seen:
            merged.append(img)
    return merged


def chunked(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def archive_images(image_paths):
    for src in image_paths:
        rel = os.path.relpath(src, upload_root)
        dest = os.path.join(archive_root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(src, dest)

def build_image_counts(upload_root):
    valid_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    counts = defaultdict(int)

    for category in os.listdir(upload_root):
        cat_path = os.path.join(upload_root, category)
        if not os.path.isdir(cat_path):
            continue

        for character in os.listdir(cat_path):
            char_path = os.path.join(cat_path, character)
            if not os.path.isdir(char_path):
                continue

            for artist in os.listdir(char_path):
                artist_path = os.path.join(char_path, artist)
                if not os.path.isdir(artist_path):
                    continue

                for file in os.listdir(artist_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in valid_ext:
                        counts[(character, artist)] += 1

    return counts 

# =========================================================
# PREFLIGHT / AUTO POST CREATION
# =========================================================

def plan_missing_posts(upload_root, selections, post_lookup, log):
    """
    Detect folders that contain images but have no matching post.
    Returns mapping:

    {
        (character, mode, artist, content): image_count
    }
    """

    valid_ext_I = {".png", ".jpg", ".jpeg"}
    valid_ext_A = {".webp", ".gif"}

    missing = defaultdict(int)

    for category in os.listdir(upload_root):
        cat_path = os.path.join(upload_root, category)
        if not os.path.isdir(cat_path):
            continue

        mode = "single" if category == "Characters" else "multi"

        for character in os.listdir(cat_path):
            char_path = os.path.join(cat_path, character)

            for artist in os.listdir(char_path):
                if (character, artist) not in selections:
                    continue

                artist_path = os.path.join(char_path, artist)
                if not os.path.isdir(artist_path):
                    continue

                for file in os.listdir(artist_path):
                    ext = os.path.splitext(file)[1].lower()

                    if ext in valid_ext_I:
                        content = "images"
                        key = (
                            character,
                            mode,
                            artist,
                            content
                        )

                        if key not in post_lookup:
                            missing[key] += 1

                    elif ext in valid_ext_A:
                        content = "animations"
                        key = (
                            character,
                            mode,
                            artist,
                            content
                        )

                        if key not in post_lookup:
                            missing[key] += 1
                    else:
                        log(f"Detected invalid file {file} in {artist_path}, skipping.")

    return missing


def create_missing_posts(missing_map, posts_path, all_posts, log, root):
    touched_posts = set()
    patch_items = []

    valid_ext_I = {".png", ".jpg", ".jpeg"}
    valid_ext_A = {".webp", ".gif"}

    group_defs = scan_group_definitions()

    for key in missing_map:
        character, mode, artist, content = key

        category = "Characters" if mode == "single" else "Groups"
        folder = os.path.join(upload_root, category, character, artist)

        if not os.path.isdir(folder):
            log(f"ERROR: expected folder missing → {folder}")
            continue

        files = []
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            ext = os.path.splitext(f)[1].lower()

            if os.path.isfile(path) and content == "images" and ext in valid_ext_I:
                files.append(path)
            elif os.path.isfile(path) and content == "animations" and ext in valid_ext_A:
                files.append(path)

        if not files:
            log(f"WARNING: no images found for {character}/{artist}")
            continue

        initial_batch = files[:20]

        # Tagging for multi posts so descriptions can be patched later
        tag_map = {}
        if mode == "multi":
            group_characters = group_defs.get(character, [])
            if group_characters:
                tag_map = prompt_group_tagging(root, character, initial_batch, group_characters)
                if tag_map is None:
                    raise RuntimeError("User aborted group tagging.")

        meta = [{"path": p} for p in initial_batch]

        log(f"Creating new post for {character}/{artist}/{content} with {len(meta)} initial images")

        post_id, resp_json, _ = create_imgchest_post(artist, meta, Token)

        touched_posts.add(post_id)

        # Extract IDs of created images so descriptions can be patched
        try:
            images_data = resp_json.get("data", {}).get("images", [])
            if len(images_data) >= len(initial_batch):
                created_ids = [img["id"] for img in images_data[-len(initial_batch):]]

                for path, img_id in zip(initial_batch, created_ids):
                    chars = tag_map.get(path, [])
                    desc = " ".join(chars).strip()

                    if desc:
                        patch_items.append({"id": img_id, "description": desc})
        except Exception as e:
            log(f"Failed preparing PATCH descriptions for new post images: {e}")

        try:
            archive_images(initial_batch)
        except Exception as e:
            log(f"WARNING: failed to archive initial images for {character}/{artist}: {e}")

        entry = {
            "post_id": post_id,
            "mode": mode,
            "character": character,
            "content": content,
            "D_artist": artist
        }

        all_posts.append(entry)

    with open(posts_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2)

    if patch_items:
        log(f"Patching descriptions for {len(patch_items)} newly created images")
        patch_image_descriptions(patch_items, Token)

    log("posts.json updated with newly created posts")
    return touched_posts


# =========================================================
# UPLOAD COLLECTION
# =========================================================

def build_post_lookup():
    posts = load_json("posts.json", [])
    lookup = {}
    for p in posts:
        key = (
            p.get("character", ""),
            p.get("mode", "").lower(),
            p.get("D_artist", ""),
            p.get("content", "").lower()
        )
        lookup[key] = p["post_id"]
    return lookup, posts


def collect_images_from_folder(upload_root, post_lookup, selections, log, root):
    """
    Returns:
        { post_id: [ {path, description?} ] }
    """

    valid_ext = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    uploads = defaultdict(list)

    group_defs = scan_group_definitions()

    for category in os.listdir(upload_root):
        cat_path = os.path.join(upload_root, category)
        if not os.path.isdir(cat_path):
            continue

        if category == "Characters":
            post_mode = "single"
        elif category == "Groups":
            post_mode = "multi"
        else:
            log(f"Invalid post mode for {category}")
            return

        for character in os.listdir(cat_path):
            char_path = os.path.join(cat_path, character)

            for artist in os.listdir(char_path):
                if (character, artist) not in selections:
                    continue

                folder = os.path.join(char_path, artist)
                if not os.path.isdir(folder):
                    continue

                images = []

                for image in os.listdir(folder):
                    path = os.path.join(folder, image)
                    if not os.path.isfile(path):
                        continue

                    ext = os.path.splitext(image)[1].lower()
                    if ext not in valid_ext:
                        continue

                    images.append(path)

                if not images:
                    continue

                # ---------- MULTI POST TAG PROMPT ----------
                tag_map = {}

                if post_mode == "multi":
                    group_characters = group_defs.get(character, [])

                    if group_characters:
                        tag_map = prompt_group_tagging(
                            root,
                            character,
                            images,
                            group_characters
                        )

                        if tag_map is None:
                            raise RuntimeError("User aborted group tagging.")

                # ---------- BUILD UPLOAD MAP ----------
                for path in images:
                    ext = os.path.splitext(path)[1].lower()
                    content = "animations" if ext in {".webp", ".gif"} else "images"

                    key = (
                        character,
                        post_mode.lower(),
                        artist,
                        content
                    )

                    post_id = post_lookup.get(key)
                    if not post_id:
                        raise RuntimeError(log(f"No post for {key}"))

                    meta = {"path": path}

                    if post_mode == "multi":
                        chars = tag_map.get(path)

                        # Safety check to ensure descriptions are actually attached
                        if not chars:
                            log(f"WARNING: No tags assigned for {os.path.basename(path)} — upload may fail GET validation")
                            chars = []

                        desc = " ".join(chars).strip()

                        if desc:
                            meta["description"] = desc
                            log(f"Tagging {os.path.basename(path)} → {desc}")
                        else:
                            log(f"WARNING: Empty description for {os.path.basename(path)}")

                    uploads[post_id].append(meta)

    return uploads


def upload_images_pipeline(touched_posts, upload_map, token, log, update_rate_limit, start_countdown):

    # Collect all PATCH operations globally so they can be sent in one request
    global_patch_items = []

    for post_id, images in upload_map.items():
        log(f"Uploading {len(images)} images → {post_id}")

        for batch in chunked(images, 20):
            response_json, headers = upload_images_to_post(post_id, batch, token)

            # Extract IDs of newly uploaded images
            new_ids = []
            try:
                images_data = response_json.get("data", {}).get("images", [])
                uploaded_count = len(batch)

                if uploaded_count <= len(images_data):
                    new_ids = [img["id"] for img in images_data[-uploaded_count:]]
            except Exception as e:
                log(f"Failed extracting uploaded image IDs: {e}")

            # Collect PATCH payload but do NOT send yet
            for meta, img_id in zip(batch, new_ids):
                desc = meta.get("description")
                if desc:
                    global_patch_items.append({"id": img_id, "description": desc})

            # Archive immediately after upload
            archive_images([i["path"] for i in batch])

            touched_posts.add(post_id)

            remaining = headers.get("X-RateLimit-Remaining")
            if remaining is not None:
                update_rate_limit(remaining)

            wait = get_wait_time(remaining)
            if wait:
                log("⏳ Rate limit reached (upload)")
                start_countdown(wait)
                time.sleep(wait)

    # Send ONE combined PATCH request for all uploaded images
    if global_patch_items:
        log(f"Patching descriptions for {len(global_patch_items)} images (single batch)")

        _, patch_headers = patch_image_descriptions(global_patch_items, token)

        remaining = patch_headers.get("X-RateLimit-Remaining")
        if remaining is not None:
            update_rate_limit(remaining)

        wait = get_wait_time(remaining)
        if wait:
            log("⏳ Rate limit reached (PATCH)")
            start_countdown(wait)
            time.sleep(wait)

    return touched_posts


# =========================================================
# NORMALIZATION / ROUTING
# =========================================================

def normalize_images(mode, images_data, artist_tag, post_id):
    normalized = []

    for item in images_data:
        src = item.get("link")
        if not src:
            continue

        filename = item.get("original_name", "unknown")

        if mode == "single":
            normalized.append({
                "src": src,
                "alt": filename,
                "tags": artist_tag
            })
        else:
            desc = item.get("description")
            if not desc:
                raise ValueError(f"Post {post_id}: missing description")
            characters = desc.strip().split()
            normalized.append({
                "src": src,
                "alt": filename,
                "tags": artist_tag + characters,
                "_characters": characters
            })

    return normalized


def route_images(images, mode, single_character=None):
    routes = defaultdict(list)

    for img in images:
        characters = [single_character] if mode == "single" else img["_characters"]

        for char in characters:
            copy_img = copy.deepcopy(img)
            copy_img.pop("_characters", None)
            copy_img["tags"] = [t for t in copy_img["tags"] if t != char]
            routes[char].append(copy_img)

    return routes


def output_path(character, content, artist):
    return f"{character}/Defines/{content.capitalize()}/{artist}.json"


# =========================================================
# MANIFEST
# =========================================================

def update_manifest(defines_dir, manifest_path, content, log):
    existing = load_json(manifest_path, [])
    registry = {e["name"]: e for e in existing}

    if os.path.isdir(defines_dir):
        for file in os.listdir(defines_dir):
            if file.endswith(".json"):
                name = os.path.splitext(file)[0]
                registry[name] = {
                    "name": name,
                    "file": f"Defines/{content.capitalize()}/{file}"
                }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(list(registry.values()), f, indent=2)

    log(f"Updated manifest → {manifest_path}")


# =========================================================
# GROUP CHARACTER POPUP SYSTEM
# =========================================================

def scan_group_definitions():
    """
    Reads upload_root/Groups/groups.json and builds:
    { group_name: [character1, character2, ...] }
    """

    groups_json = "groups.json"

    if not os.path.exists(groups_json):
        return {}

    try:
        with open(groups_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        mapping = {}

        for group_name, characters in data.items():
            if isinstance(characters, list):
                mapping[group_name] = sorted([str(c) for c in characters])

        return mapping

    except Exception:
        return {}

def prompt_group_tagging(root, group_name, image_paths, characters):
    """
    Image-by-image tagging popup.
    Returns:
        { image_path: [selected_characters] }
        or None if aborted
    """

    from PIL import Image, ImageTk

    result = {}

    win = CTkToplevel(root)
    win.title(f"Tag Group → {group_name}")

    # Start maximized but still allow proper layout
    try:
        win.state("zoomed")
    except Exception:
        win.attributes("-zoomed", True)

    win.grab_set()

    # ----- Layout frames -----
    top_frame = CTkFrame(win)
    top_frame.pack(fill="both", expand=True, padx=10, pady=10)

    bottom_frame = CTkFrame(win)
    bottom_frame.pack(fill="x", padx=10, pady=10)

    # Image display
    img_label = CTkLabel(top_frame, text="")
    img_label.pack(fill="both", expand=True)

    # Character selection area
    scroll = CTkScrollableFrame(bottom_frame, height=160)
    scroll.pack(fill="x", padx=5, pady=5)

    char_vars = {c: BooleanVar(value=False) for c in characters}

    for c in characters:
        CTkCheckBox(scroll, text=c, variable=char_vars[c]).pack(anchor="w", padx=6, pady=2)

    status_var = StringVar(value="")
    status_label = CTkLabel(bottom_frame, textvariable=status_var)
    status_label.pack(pady=(5, 2))

    nav_frame = CTkFrame(bottom_frame)
    nav_frame.pack(fill="x", pady=5)

    index = {"i": 0}
    aborted = {"flag": False}
    last_selection = {"tags": []}

    def load_image():
        path = image_paths[index["i"]]

        try:
            img = Image.open(path)

            # Ensure layout sizes are calculated
            win.update_idletasks()

            # Constrain image to the available space of the top frame
            max_w = max(300, top_frame.winfo_width() - 20)
            max_h = max(300, top_frame.winfo_height() - 20)

            img.thumbnail((max_w, max_h))

            tk_img = ImageTk.PhotoImage(img)
            img_label.configure(image=tk_img, text="")
            img_label.image = tk_img

        except Exception as e:
            img_label.configure(image=None, text=f"Failed to load image: {path}{e}")

        status_var.set(f"Image {index['i'] + 1} / {len(image_paths)}")

        # restore last selection
        for c, v in char_vars.items():
            v.set(c in last_selection["tags"])

    def save_current():
        selected = [c for c, v in char_vars.items() if v.get()]

        if not selected:
            messagebox.showwarning("No tags", "Select at least one character.")
            return False

        result[image_paths[index["i"]]] = selected
        last_selection["tags"] = selected
        return True

    def next_image():
        if not save_current():
            return

        if index["i"] < len(image_paths) - 1:
            index["i"] += 1
            load_image()
        else:
            win.destroy()

    def prev_image():
        if index["i"] > 0:
            index["i"] -= 1
            load_image()

    def on_close():
        aborted["flag"] = True
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)

    CTkButton(nav_frame, text="Previous", command=prev_image).pack(side="left", padx=5)
    CTkButton(nav_frame, text="Confirm / Next", command=next_image).pack(side="right", padx=5)

    load_image()

    root.wait_window(win)

    if aborted["flag"]:
        return None

    return result


# =========================================================
# MAIN PIPELINE
# =========================================================

def main_processing_with_upload(selections, log, update_rate_limit, start_countdown, root):
    post_lookup, all_posts = build_post_lookup()

    # -------------------------------------------------
    # PREFLIGHT: detect missing posts
    # -------------------------------------------------

    missing_map = plan_missing_posts(upload_root, selections, post_lookup, log)

    if missing_map:
        log(f"Detected {len(missing_map)} missing post targets")
        touched_posts = create_missing_posts(missing_map, "posts.json", all_posts, log, root)

        # Reload lookup after creating posts
        post_lookup, all_posts = build_post_lookup()

    else:
        touched_posts = set()

    # -------------------------------------------------
    # BUILD UPLOAD MAP
    # -------------------------------------------------

    upload_map = collect_images_from_folder(
        upload_root,
        post_lookup,
        selections,
        log,
        root
    )

    if not upload_map:
        log("No new images to upload detected, skipping upload step")

    # Determine which posts correspond to the current selection
    selected_posts = {
        p["post_id"]
        for p in all_posts
        if (p.get("character"), p.get("D_artist")) in selections
    }

    # Run uploads if there are images; otherwise start with empty touched set
    if upload_map:
        touched_posts = upload_images_pipeline(
            touched_posts,
            upload_map,
            Token,
            log,
            update_rate_limit,
            start_countdown
        )

    # Ensure selected posts are still refreshed via GET even if nothing uploaded
    touched_posts |= selected_posts

    # Cooldown before GET if needed
    if touched_posts:
        log("Refreshing touched posts…")

    touched_entries = [p for p in all_posts if p["post_id"] in touched_posts]
    main_processing(touched_entries, log, update_rate_limit, start_countdown)


def main_processing(posts, log, update_rate_limit, start_countdown):
    touched_manifests = set()

    for index, entry in enumerate(posts):
        post_id = entry["post_id"]
        mode = entry["mode"]
        content = entry["content"]

        log(f"Processing {post_id}")

        post_data, remaining = fetch_imgchest_post_data(post_id, Token)
        data = post_data["data"]

        artist = sanitize_title(data.get("title", "untitled"))
        artist_tag = [artist]

        images = normalize_images(
            mode,
            data.get("images", []),
            artist_tag,
            post_id
        )

        routed = route_images(images, mode, entry.get("character"))

        for character, imgs in routed.items():
            path = output_path(character, content, artist)
            existing = load_json(path, [])
            merged = merge_images(existing, imgs)
            save_json(merged, path, log)
            touched_manifests.add((character, content))

        if remaining is not None:
            update_rate_limit(remaining)

        wait = get_wait_time(remaining)
        if index < len(posts) - 1 and wait:
            log("⏳ Rate limit reached (GET)")
            start_countdown(wait)
            time.sleep(wait)

    for character, content in touched_manifests:
        update_manifest(
            f"{character}/Defines/{content.capitalize()}",
            f"{character}/{content.strip('s')}_manifest.json",
            content,
            log
        )

    log("All processing complete.")


# =========================================================
# GUI
# =========================================================

def main_GUI():
    set_appearance_mode("dark")
    root = CTk()
    root.geometry("900x600")
    root.title("ImgChest Upload Manager")
    root.after(0, lambda: root.state('zoomed'))
    image_counts = build_image_counts(upload_root)

    # ---------- FILTER STATE ----------
    char_filter = StringVar(value="All")
    artist_filter = StringVar(value="")

    def shutdown():
        root.destroy
        exit()
    
    root.protocol("WM_DELETE_WINDOW", shutdown)

    # ---------- LOG ----------
    log_box = CTkTextbox(root, height=120, state="disabled")
    log_box.pack(fill="x", padx=8, pady=(4, 2))

    def log(msg):
        root.after(0, lambda: (
            log_box.configure(state="normal"),
            log_box.insert("end", msg + "\n"),
            log_box.see("end"),
            log_box.configure(state="disabled")
        ))

    rate_var = StringVar(value="Rate limit: -")
    countdown_var = StringVar(value="")
    CTkLabel(root, textvariable=rate_var).pack(anchor="w", padx=8)
    CTkLabel(root, textvariable=countdown_var).pack(anchor="w", padx=8)

    def update_rate(val):
        root.after(0, lambda: rate_var.set(f"Rate limit remaining: {val}"))

    def countdown(sec):
        def tick(s):
            if s <= 0:
                countdown_var.set("")
                return
            countdown_var.set(f"Reset in {s}s")
            root.after(1000, tick, s - 1)
        tick(sec)

    # ---------- DATA BUILD ----------
    tree = defaultdict(list)
    for category in os.listdir(upload_root):
        for character in os.listdir(os.path.join(upload_root, category)):
            for artist in os.listdir(os.path.join(upload_root, category, character)):
                tree[character].append(artist)

    selections = {}

    # ---------- FILTER UI ----------
    filter_frame = CTkFrame(root)
    filter_frame.pack(fill="x", padx=8, pady=4)

    CTkLabel(filter_frame, text="Character").pack(side="left", padx=4)
    CTkOptionMenu(
        filter_frame,
        variable=char_filter,
        values=["All"] + sorted(tree.keys()),
        command=lambda _: rebuild()
    ).pack(side="left")

    CTkLabel(filter_frame, text="Artist filter").pack(side="left", padx=8)
    CTkEntry(filter_frame, textvariable=artist_filter, width=200).pack(side="left")
    artist_filter.trace_add("write", lambda *_: rebuild())

    # ---------- TREE ----------
    scroll = CTkScrollableFrame(root)
    scroll.pack(fill="both", expand=True, padx=8, pady=4)
    COLUMNS = 9
    ARTIST_COLUMNS_SINGLE = 4  # adjust based on density preference


    def rebuild():
        parent = getattr(scroll, "frame", scroll)

        for w in parent.winfo_children():
            w.destroy()

        visible_chars = [
            (char, sorted(set(artists)))
            for char, artists in sorted(tree.items())
            if char_filter.get() == "All" or char == char_filter.get()
        ]

        single_character = len(visible_chars) == 1

        if single_character:
            character, artists = visible_chars[0]

            char_frame = CTkFrame(parent)
            char_frame.pack(fill="both", expand=True, padx=8, pady=6)

            CTkLabel(
                char_frame,
                text=character,
                font=("Arial", 16, "bold")
            ).pack(anchor="w", padx=6, pady=(4, 6))

            grid = CTkFrame(char_frame)
            grid.pack(fill="both", expand=True)

            col = 0
            row = 0
            artists_sorted = sorted(
            set(artists),
            key=lambda a: image_counts.get((character, a), 0),
            reverse=True
            )


            for artist in artists_sorted:
                if artist_filter.get().lower() not in artist.lower():
                    continue

                key = (character, artist)
                var = selections.setdefault(key, BooleanVar(value=False))
                count = image_counts.get((character, artist), 0)
                label = f"{artist} ({count})" if count else f"{artist} (0)"

                CTkCheckBox(
                    grid,
                    text=label,
                    variable=var
                ).grid(row=row, column=col, sticky="w", padx=12, pady=2)

                col += 1
                if col >= ARTIST_COLUMNS_SINGLE:
                    col = 0
                    row += 1

        else:
            row_frame = None
            col = 0

            for idx, (character, artists) in enumerate(visible_chars):
                if idx % COLUMNS == 0:
                    row_frame = CTkFrame(parent)
                    row_frame.pack(fill="x", pady=6)

                char_frame = CTkFrame(row_frame)
                char_frame.pack(side="left", fill="y", expand=True, padx=6)

                CTkLabel(
                    char_frame,
                    text=character,
                    font=("Arial", 14, "bold")
                ).pack(anchor="w", padx=6, pady=(4, 2))

                artists_sorted = sorted(
                    set(artists),
                    key=lambda a: image_counts.get((character, a), 0),
                    reverse=True
                )

                for artist in artists_sorted:
                    if artist_filter.get().lower() not in artist.lower():
                        continue

                    key = (character, artist)
                    var = selections.setdefault(key, BooleanVar(value=False))
                    count = image_counts.get((character, artist), 0)
                    label = f"{artist} ({count})" if count else f"{artist} (0)"

                    CTkCheckBox(
                        char_frame,
                        text=label,
                        variable=var
                    ).pack(anchor="w", padx=14)

    rebuild()


    # ---------- BUTTONS ----------
    btns = CTkFrame(root)
    btns.pack(fill="x", padx=8, pady=6)

    def select_visible(val):
        for (char, artist), var in selections.items():
            if char_filter.get() != "All" and char != char_filter.get():
                continue
            if artist_filter.get().lower() not in artist.lower():
                continue
            var.set(val)

    CTkButton(btns, text="Select All Visible", command=lambda: select_visible(True)).pack(side="left")
    CTkButton(btns, text="Select None", command=lambda: select_visible(False)).pack(side="left", padx=6)

    def process():
        chosen = {k for k, v in selections.items() if v.get()}
        if not chosen:
            messagebox.showwarning("No selection", "Nothing selected.")
            return

        threading.Thread(
            target=lambda: main_processing_with_upload(chosen, log, update_rate, countdown, root),
            daemon=True
        ).start()

    CTkButton(btns, text="Process Selection", command=process).pack(side="right")

    root.mainloop()

if __name__ == "__main__":
    main_GUI()