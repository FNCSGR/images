const gallery = document.querySelector(".gallery");

const artistFilter = document.getElementById("artist-filter");
const characterFilter = document.getElementById("character-filter");
const visualFilter = document.getElementById("visual-filter");
const activityFilter = document.getElementById("activity-filter");

const platformIcons = { // Define the paths for the icons of all platforms that can be linked to here.
  x: "../assets/x.png",
  bsky: "../assets/bsky.png",
  patreon: "../assets/patreon.png",
  substar: "../assets/substar.png"
};

let jsonFiles = [];
let jsonNames = [];
let artistRegistry = {};

const selectedTags = {
  artist: new Set(),
  character: new Set(),
  visual: new Set(),
  activity: new Set(),
};

let filterMode = "any";

const BATCH_SIZE = 20;

let imageQueue = [];      // full dataset
let filteredQueue = [];   // filtered dataset
let renderIndex = 0;      // pagination index

/* ---------------- TAG HELPERS ---------------- */

function createCheckbox(container, value, category) {
  const label = document.createElement("label");
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.value = value;

  checkbox.addEventListener("change", () => {
    checkbox.checked
      ? selectedTags[category].add(value)
      : selectedTags[category].delete(value);

    applyFiltersAndReset();
  });

  label.appendChild(checkbox);
  label.appendChild(document.createTextNode(value.charAt(0).toUpperCase() + value.slice(1)));
  container.appendChild(label);
}

function parseTags(text) {
  const regex = /"([^"]+)"|(\S+)/g;
  const tags = [];
  let match;
  while ((match = regex.exec(text)) !== null) {
    tags.push(match[1] || match[2]);
  }
  return tags;
}

/* ---------------- FILTERING ---------------- */

function imageMatches(img) {
  const itemTags = img.tags;

  const anyTagSelected = Object.values(selectedTags).some(s => s.size);

  const isSensitive = sensitiveTags.some(t => itemTags.includes(t));
  const sensitiveSelected = sensitiveTags.some(t =>
    Object.values(selectedTags).some(s => s.has(t))
  );

  if (isSensitive && !sensitiveSelected) return false;
  if (!anyTagSelected) return true;

  if (filterMode === "any") {
    return Object.values(selectedTags).some(set =>
      [...set].some(tag => itemTags.includes(tag))
    );
  }

  // filterMode === "all"
  return Object.values(selectedTags).every(set =>
    [...set].every(tag => itemTags.includes(tag))
  );
}

function applyFiltersAndReset() {
  filteredQueue = imageQueue.filter(imageMatches);
  renderIndex = 0;
  gallery.innerHTML = "";
  loadNextBatch();
}

/* ---------------- RENDERING ---------------- */

function loadNextBatch() {
  const next = filteredQueue.slice(renderIndex, renderIndex + BATCH_SIZE);
  if (!next.length) return;

  const grouped = {};

  next.forEach(img => {
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
      item.dataset.tags = tags.map(t => t.includes(" ") ? `"${t}"` : t).join(" ");

      const img = document.createElement("img");
      img.src = src;
      img.alt = alt;
      img.style.cursor = "pointer";
      img.addEventListener("click", () => window.open(src, "_blank", "noopener"));

      item.appendChild(img);
      grid.appendChild(item);
    });

    section.appendChild(grid);
    gallery.appendChild(section);
  }

  renderIndex += BATCH_SIZE;
}

/* ---------------- SCROLL ---------------- */

window.addEventListener("scroll", () => {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
    if (renderIndex < filteredQueue.length) {
      loadNextBatch();
    }
  }
});

/* ---------------- UI ---------------- */

document.getElementById("toggle-filters").addEventListener("click", () => {
  const filterBar = document.getElementById("filters-bar");
  const expanded = filterBar.classList.toggle("expanded");
  filterBar.classList.toggle("collapsed", !expanded);
  document.getElementById("toggle-filters").textContent = expanded ? "Hide Filters" : "Show Filters";
});

document.getElementById("filter-mode-toggle").addEventListener("change", e => {
  filterMode = e.target.value;
  applyFiltersAndReset();
});

/* ---------------- INIT ---------------- */

async function initializeGallery() {
  try {
    const manifestResponse = await fetch("manifest.json");
    const manifestData = await manifestResponse.json();

    const artistResponse = await fetch("../artists.json");
    artistRegistry = await artistResponse.json();

    jsonFiles = manifestData.map(e => e.file);
    jsonNames = manifestData.map(e => e.name);

    const tagCategories = { artist: jsonNames };
    Object.assign(tagCategories, extraTagCategories);

    const fileResponses = await Promise.all(
      jsonFiles.map((file, index) =>
        fetch(file)
          .then(r => r.json())
          .then(images =>
            images.map(img => ({
              ...img,
              artist: jsonNames[index]
            }))
          )
      )
    );

    imageQueue = fileResponses.flat();

    for (const [category, values] of Object.entries(tagCategories)) {
      const container = document.getElementById(`${category}-filter`);
      values.forEach(v => v.trim() && createCheckbox(container, v, category));
    }

    applyFiltersAndReset();

  } catch (error) {
    console.error("Error loading gallery:", error);
  }
}

initializeGallery();