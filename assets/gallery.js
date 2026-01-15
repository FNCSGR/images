const gallery = document.querySelector(".gallery");
const sentinel = document.createElement("div");
sentinel.id = "scroll-sentinel";
gallery.after(sentinel);

const platformIcons = {
  x: "../assets/x.png",
  bsky: "../assets/bsky.png",
  patreon: "../assets/patreon.png",
  substar: "../assets/substar.png"
};

let artistRegistry = {};
let jsonFiles = [];
let jsonNames = [];

const selectedTags = {
  artist: new Set(),
  character: new Set(),
  visual: new Set(),
  activity: new Set(),
};

let filterMode = "any";

const BATCH_SIZE = 10;

let imageQueue = [];
let filteredQueue = [];
let renderIndex = 0;

const artistSections = new Map();

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

  return Object.values(selectedTags).every(set =>
    [...set].every(tag => itemTags.includes(tag))
  );
}

async function applyFiltersAndReset() {
  filteredQueue = imageQueue.filter(imageMatches);
  renderIndex = 0;
  gallery.innerHTML = "";
  artistSections.clear();

  loadNextBatch();
  await fillViewport();

  observer.observe(sentinel);
}

async function fillViewport() {
  let safety = 0;

  while (
    sentinel.getBoundingClientRect().top < window.innerHeight + 200 &&
    renderIndex < filteredQueue.length &&
    safety < 10
  ) {
    loadNextBatch();
    safety++;
    await new Promise(r => requestAnimationFrame(r));
  }
}

/* ---------------- ARTIST SECTION MANAGEMENT ---------------- */

function getArtistSection(artist) {
  if (artistSections.has(artist)) return artistSections.get(artist);

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

  const grid = document.createElement("div");
  grid.className = "artist-gallery";

  section.appendChild(header);
  section.appendChild(grid);
  gallery.appendChild(section);

  artistSections.set(artist, grid);
  return grid;
}

/* ---------------- RENDERING ---------------- */

function loadNextBatch() {
  const next = filteredQueue.slice(renderIndex, renderIndex + BATCH_SIZE);
  if (!next.length) return;

  next.forEach(({ src, alt, tags, artist }) => {
    const grid = getArtistSection(artist);

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

  renderIndex += BATCH_SIZE;
}

/* ---------------- INTERSECTION OBSERVER ---------------- */

let isLoading = false;

const observer = new IntersectionObserver(entries => {
  if (!entries[0].isIntersecting) return;
  if (isLoading) return;

  isLoading = true;

  loadNextBatch();

  requestAnimationFrame(() => {
    isLoading = false;

    if (renderIndex < filteredQueue.length) {
      observer.observe(sentinel);
    }
  });
}, { rootMargin: "300px" });

/* ---------------- UI ---------------- */

document.getElementById("filter-mode-toggle").addEventListener("change", e => {
  filterMode = e.target.value;
  applyFiltersAndReset();
});

document.getElementById("toggle-filters").addEventListener("click", () => {
  const filterBar = document.getElementById("filters-bar");
  const expanded = filterBar.classList.toggle("expanded");
  filterBar.classList.toggle("collapsed", !expanded);
  document.getElementById("toggle-filters").textContent =
    expanded ? "Hide Filters" : "Show Filters";
});

/* ---------------- INIT ---------------- */

async function initializeGallery() {
  try {
    const manifest = await fetch("manifest.json").then(r => r.json());
    artistRegistry = await fetch("../artists.json").then(r => r.json());

    jsonFiles = manifest.map(e => e.file);
    jsonNames = manifest.map(e => e.name);

    const tagCategories = { artist: jsonNames };
    Object.assign(tagCategories, extraTagCategories);

    const responses = await Promise.all(
      jsonFiles.map((file, i) =>
        fetch(file).then(r => r.json()).then(images =>
          images.map(img => ({ ...img, artist: jsonNames[i] }))
        )
      )
    );

    imageQueue = responses.flat();

    for (const [category, values] of Object.entries(tagCategories)) {
      const container = document.getElementById(`${category}-filter`);
      values.forEach(v => v.trim() && createCheckbox(container, v, category));
    }

    applyFiltersAndReset();

  } catch (err) {
    console.error("Gallery load error:", err);
  }
}

initializeGallery();