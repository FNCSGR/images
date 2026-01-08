const gallery = document.querySelector(".gallery"); // Calls in the filters as previously established, so the script can make the filtering happen.
const artistFilter = document.getElementById("artist-filter");
const characterFilter = document.getElementById("character-filter");
const visualFilter = document.getElementById("visual-filter");
const activityFilter = document.getElementById("activity-filter");

const platformIcons = { // Define all platforms that can be linked too here.
  x: "../assets/x.png",
  bsky: "../assets/bsky.png"
};


let jsonFiles = []; // Establishes these two variables for later assigment when the manifest json is loaded.
let jsonNames = [];
let artistRegistry = {};

const selectedTags = { // Get the tags established too.
  artist: new Set(),
  character: new Set(),
  visual: new Set(),
  activity: new Set(),
};
 
const allItems = []; // Currently redundant batch loading, needs rework.
let filterMode = "any";
let imageQueue = [];
const BATCH_SIZE = 500;
let batchIndex = 0;

function createCheckbox(container, value, category) { // This function creates the checkboxes so users can select the tags they wish to see.
  const label = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.value = value;

  checkbox.addEventListener("change", () => {
    if (checkbox.checked) {
      selectedTags[category].add(value);
    } else {
      selectedTags[category].delete(value);
    }
    filterGallery(); // Call filterGallery everytime the user updates their selection to filter the gallery based on the new selection.
  });

  label.appendChild(checkbox);
  label.appendChild(document.createTextNode(value.charAt(0).toUpperCase() + value.slice(1)));
  container.appendChild(label); 
}

function parseTags(text) { // Define the fuction for reading the tags from the json files.
  const regex = /"([^"]+)"|(\S+)/g;
  const tags = [];
  let match;

  while ((match = regex.exec(text)) !== null) {
    tags.push(match[1] || match[2]);
  }

  return tags;
}

function filterGallery() { // This function filters the gallery based on user selection. 
  const anyTagSelected = Object.values(selectedTags).some(tags => tags.size > 0); // Only filter if tags have been selected, and show all* images if not. (*Except sensitive ones)

  allItems.forEach(item => {
    const itemTags = parseTags(item.dataset.tags);

    const isSensitive = sensitiveTags.some(tag => itemTags.includes(tag));
    const sensitiveTagSelected = sensitiveTags.some(tag =>
      Object.values(selectedTags).some(set => set.has(tag))
    );
    if (isSensitive && !sensitiveTagSelected) { // Filter out sensitive tags unless they're selected.
      item.style.display = "none";
      return;
    }

    if (!anyTagSelected) {
      item.style.display = "block";
      return;
    }

    let matches = filterMode === "all";

    for (const [category, tags] of Object.entries(selectedTags)) {
      if (tags.size === 0) continue;

      const tagArray = Array.from(tags);
      const hasMatch = tagArray.some(tag => itemTags.includes(tag));
      const hasAll = tagArray.every(tag => itemTags.includes(tag));

      if (filterMode === "any" && hasMatch) {
        matches = true;
        break;
      }

      if (filterMode === "all" && !hasAll) {
        matches = false;
        break;
      }
    }

    if (filterMode === "all") {
      matches = Object.entries(selectedTags).every(([category, tags]) => {
        if (tags.size === 0) return true;
        const tagArray = Array.from(tags);
        return tagArray.every(tag => itemTags.includes(tag));
      });
    }

    item.style.display = matches ? "block" : "none";
  });
  
  document.querySelectorAll(".artist-section").forEach(section => { // This filters out empty artist category names
  const visibleItems = section.querySelectorAll(".gallery-item:not([style*='display: none'])");
  section.style.display = visibleItems.length ? "block" : "none";
});

}

function loadNextBatch() {
  const nextBatch = imageQueue.slice(batchIndex, batchIndex + BATCH_SIZE);

  const grouped = {};

  nextBatch.forEach(img => {
    if (!grouped[img.artist]) grouped[img.artist] = [];
    grouped[img.artist].push(img);
  });

  for (const [artist, images] of Object.entries(grouped)) {

    const section = document.createElement("div");
    section.className = "artist-section";

    const header = document.createElement("div");
    header.className = "artist-header";

    const nameSpan = document.createElement("span");
    nameSpan.textContent = artist;

    header.appendChild(nameSpan);

    const socials = artistRegistry[artist];

    if (socials) {
      for (const [platform, url] of Object.entries(socials)) {
        if (!platformIcons[platform]) continue;

        const link = document.createElement("a");
        link.href = url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.className = "artist-social";

        const icon = document.createElement("img");
        icon.src = platformIcons[platform];
        icon.alt = platform;

        link.appendChild(icon);
        header.appendChild(link);
      }
    }

    section.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "artist-gallery";

    images.forEach(({ src, alt, tags }) => {
      const item = document.createElement("div");
      item.className = "gallery-item";
      item.dataset.tags = tags.map(tag =>
        tag.includes(" ") ? `"${tag}"` : tag
      ).join(" ");

      const img = document.createElement("img");
      img.src = src;
      img.alt = alt;

      img.style.cursor = "pointer";

      img.addEventListener("click", () => {
        window.open(src, "_blank", "noopener");
      })

      item.appendChild(img);
      grid.appendChild(item);
      allItems.push(item);
    });

    section.appendChild(grid);
    gallery.appendChild(section);
  }

  batchIndex += BATCH_SIZE;
  filterGallery();
}

window.addEventListener("scroll", () => {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
    if (batchIndex < imageQueue.length) {
      loadNextBatch();
    }
  }
});

document.getElementById("toggle-filters").addEventListener("click", () => {
  const filterBar = document.getElementById("filters-bar");
  const expanded = filterBar.classList.toggle("expanded");
  filterBar.classList.toggle("collapsed", !expanded);
  document.getElementById("toggle-filters").textContent = expanded ? "Hide Filters" : "Show Filters";
});

document.getElementById("filter-mode-toggle").addEventListener("change", e => {
  filterMode = e.target.value;
  filterGallery();
});

async function initializeGallery() { // Loads the gallery by opening the manifest and then parsing all images and tags.
  try {
    const manifestResponse = await fetch("manifest.json");
    const manifestData = await manifestResponse.json();

    const artistResponse = await fetch("../artists.json");
    artistRegistry = await artistResponse.json();

    jsonFiles = manifestData.map(entry => entry.file); // Get the file names out of the manifest for correct pathing to the image jsons.
    jsonNames = manifestData.map(entry => entry.name); // Get the artist names out of the manifest for the filters.

    const tagCategories = {
      artist: jsonNames, // Base the contents of the artist filter group on the names of the artists in the manifest, this means they update automatically and are user-error proof.
    };
    
    //if (typeof extraTagCategories !== "undefined") {} THIS LINE HAS BEEN COMMENTED OUT AS IT BROKE THE SCRIPT 
    Object.assign(tagCategories, extraTagCategories); // Merge the artist category with the other categories that are defined in tags.json, this is why this script needs to be ran after.

    const fileResponses = await Promise.all(
      jsonFiles.map((file, index) =>
        fetch(file).then(r => r.json()).then(images =>
          images.map(img => ({
            ...img,
            artist: jsonNames[index]
          }))
        )
      )
    );

imageQueue = fileResponses.flat();


    imageQueue = fileResponses.flat();

    for (const [category, values] of Object.entries(tagCategories)) {
      const container = document.getElementById(`${category}-filter`);
      values.forEach(value => {
        if (value.trim() !== "") createCheckbox(container, value, category);
      });
    }

    loadNextBatch();
  } catch (error) {
    console.error("Error loading gallery:", error);
  }
}

initializeGallery();
