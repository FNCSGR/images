const gallery = document.querySelector(".gallery");
const artistFilter = document.getElementById("artist-filter");
const characterFilter = document.getElementById("character-filter");
const visualFilter = document.getElementById("visual-filter");
const activityFilter = document.getElementById("activity-filter");

let jsonFiles = [];
let jsonNames = [];

const selectedTags = {
  artist: new Set(),
  character: new Set(),
  visual: new Set(),
  activity: new Set(),
};

const allItems = [];
let filterMode = "any";
let imageQueue = [];
const BATCH_SIZE = 500;
let batchIndex = 0;

function createCheckbox(container, value, category) {
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
    filterGallery();
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

function filterGallery() {
  const anyTagSelected = Object.values(selectedTags).some(tags => tags.size > 0);

  allItems.forEach(item => {
    const itemTags = parseTags(item.dataset.tags);

    const isSensitive = sensitiveTags.some(tag => itemTags.includes(tag));
    const sensitiveTagSelected = sensitiveTags.some(tag =>
      Object.values(selectedTags).some(set => set.has(tag))
    );
    if (isSensitive && !sensitiveTagSelected) {
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
}

function loadNextBatch() {
  const nextBatch = imageQueue.slice(batchIndex, batchIndex + BATCH_SIZE);

  nextBatch.forEach(({ src, alt, tags }) => {
    const item = document.createElement("div");
    item.className = "gallery-item";
    item.dataset.tags = tags.join(" ");

    const img = document.createElement("img");
    img.src = src;
    img.alt = alt;

    item.appendChild(img);
    gallery.appendChild(item);
    allItems.push(item);
  });

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

async function initializeGallery() {
  try {
    const manifestResponse = await fetch("manifest.json");
    const manifestData = await manifestResponse.json();

    jsonFiles = manifestData.map(entry => entry.file);
    jsonNames = manifestData.map(entry => entry.name);

    const tagCategories = {
      artist: ["Rude Frog", "GRVTY"],
    };
    
    //if (typeof extraTagCategories !== "undefined") {}
    Object.assign(tagCategories, extraTagCategories);

    const fileResponses = await Promise.all(
      jsonFiles.map(file => fetch(file).then(r => r.json()))
    );

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
