<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Image Gallery</title>
  <style>
    body {
      background-color: #121212;
      color: #eee;
      font-family: sans-serif;
      margin: 0;
      padding: 0;
    }
    header {
      padding: 1rem;
      background: #1e1e1e;
      position: sticky;
      top: 0;
      z-index: 10;
    }
    .filters {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .filters button {
      background: #333;
      border: none;
      color: #fff;
      padding: 0.5rem 1rem;
      border-radius: 5px;
      cursor: pointer;
    }
    .filters button.active {
      background: #6200ee;
    }
    .gallery {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      padding: 1rem;
    }
    .gallery-item {
      background: #1e1e1e;
      border-radius: 10px;
      overflow: hidden;
    }
    .gallery-item img {
      width: 100%;
      display: block;
    }
  </style>
</head>
<body>
  <header>
    <div class="filters">
      <button class="active" data-filter="all">All</button>
      <button data-filter="sunset">Sunset</button>
      <button data-filter="ocean">Ocean</button>
      <button data-filter="mountains">Mountains</button>
    </div>
  </header>
  <main class="gallery">
    <div class="gallery-item" data-tags="sunset ocean">
      <img src="images/sunset1.jpg" alt="Sunset at the ocean" />
    </div>
    <div class="gallery-item" data-tags="mountains">
      <img src="images/mountains1.jpg" alt="Snowy mountain" />
    </div>
    <div class="gallery-item" data-tags="sunset">
      <img src="images/sunset2.jpg" alt="Sunset in the valley" />
    </div>
    <div class="gallery-item" data-tags="ocean">
      <img src="images/ocean1.jpg" alt="Waves on the beach" />
    </div>
  </main>
  <script>
    const buttons = document.querySelectorAll(".filters button");
    const items = document.querySelectorAll(".gallery-item");

    buttons.forEach(button => {
      button.addEventListener("click", () => {
        document.querySelector(".filters .active").classList.remove("active");
        button.classList.add("active");
        const filter = button.dataset.filter;

        items.forEach(item => {
          const tags = item.dataset.tags.split(" ");
          if (filter === "all" || tags.includes(filter)) {
            item.style.display = "block";
          } else {
            item.style.display = "none";
          }
        });
      });
    });
  </script>
</body>
</html>

