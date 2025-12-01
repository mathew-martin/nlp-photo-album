(() => {
  const searchForm = document.getElementById("search-form");
  const searchInput = document.getElementById("search-input");
  const resultsEl = document.getElementById("results");
  const searchStatus = document.getElementById("search-status");

  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-input");
  const customLabelsInput = document.getElementById("custom-labels");
  const uploadStatus = document.getElementById("upload-status");
  const addButton = document.getElementById("add-button");
  const uploadModal = document.getElementById("upload-modal");
  const closeModal = document.getElementById("close-modal");
  const lightbox = document.getElementById("lightbox");
  const lightboxImg = document.getElementById("lightbox-img");
  const lightboxPrev = document.getElementById("lightbox-prev");
  const lightboxNext = document.getElementById("lightbox-next");
  const lightboxClose = document.getElementById("lightbox-close");

  const apiBase = window.CONFIG?.API_BASE;
  const apiKey = window.CONFIG?.API_KEY;
  const bucketUrl = "https://cc-hw3-b2-photos.s3.amazonaws.com";
  const defaultQuery = "*";
  let currentResults = [];
  let currentIndex = 0;

  function setStatus(el, message, isError = false) {
    el.textContent = message || "";
    el.classList.toggle("error", Boolean(isError));
  }

  async function searchPhotos(query) {
    const effectiveQuery = query && query.trim().length ? query : defaultQuery;
    closeLightbox();
    setStatus(searchStatus, "Searching...");
    resultsEl.innerHTML = "";
    try {
      const url = new URL(`${apiBase}/search`);
      url.searchParams.set("q", effectiveQuery);
      const resp = await fetch(url.toString(), {
        headers: { "x-api-key": apiKey },
      });
      if (!resp.ok) throw new Error(`Search failed (${resp.status})`);
      const data = await resp.json();
      currentResults = data.results || [];
      renderResults(currentResults);
      setStatus(searchStatus, currentResults.length ? "" : "No results.");
    } catch (err) {
      console.error(err);
      setStatus(searchStatus, err.message, true);
    }
  }

  function renderResults(items) {
    resultsEl.innerHTML = "";
    items.forEach((item, index) => {
      const card = document.createElement("div");
      card.className = "result-card";
      const img = document.createElement("img");
      img.src = `${bucketUrl}/${encodeURIComponent(item.objectKey)}`;
      img.alt = item.objectKey;
      img.addEventListener("click", () => openLightbox(index));
      card.appendChild(img);
      resultsEl.appendChild(card);
    });
  }

  async function uploadPhoto(file, customLabels) {
    setStatus(uploadStatus, "Uploading...");
    const objectKey = `${Date.now()}-${file.name}`;
    const url = `${apiBase}/photos?objectKey=${encodeURIComponent(objectKey)}`;
    const headers = {
      "Content-Type": file.type || "application/octet-stream",
      "x-api-key": apiKey,
    };
    if (customLabels) {
      headers["x-amz-meta-customLabels"] = customLabels;
    }

    const resp = await fetch(url, {
      method: "PUT",
      headers,
      body: file,
    });

    if (!resp.ok) {
      throw new Error(`Upload failed (${resp.status})`);
    }
    setStatus(uploadStatus, "Upload complete. Rekognition is indexing now.");
  }

  // Lightbox controls
  function openLightbox(index) {
    if (!currentResults.length) return;
    currentIndex = index;
    lightboxImg.src = `${bucketUrl}/${encodeURIComponent(currentResults[currentIndex].objectKey)}`;
    lightbox.classList.add("show");
  }

  function closeLightbox() {
    lightbox.classList.remove("show");
    lightboxImg.src = "";
  }

  function showPrev() {
    if (!currentResults.length) return;
    currentIndex = (currentIndex - 1 + currentResults.length) % currentResults.length;
    lightboxImg.src = `${bucketUrl}/${encodeURIComponent(currentResults[currentIndex].objectKey)}`;
  }

  function showNext() {
    if (!currentResults.length) return;
    currentIndex = (currentIndex + 1) % currentResults.length;
    lightboxImg.src = `${bucketUrl}/${encodeURIComponent(currentResults[currentIndex].objectKey)}`;
  }

  searchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = searchInput.value.trim();
    if (!q) {
      searchPhotos(defaultQuery);
    } else {
      searchPhotos(q);
    }
  });

  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!fileInput.files || !fileInput.files[0]) {
      setStatus(uploadStatus, "Select an image first.", true);
      return;
    }
    try {
      await uploadPhoto(fileInput.files[0], customLabelsInput.value.trim());
      uploadForm.reset();
    } catch (err) {
      console.error(err);
      setStatus(uploadStatus, err.message, true);
    }
  });

  // Modal controls
  function openModal() {
    uploadModal.classList.remove("hidden");
  }
  function closeModalFn() {
    uploadModal.classList.add("hidden");
    uploadForm.reset();
    setStatus(uploadStatus, "");
  }

  addButton.addEventListener("click", openModal);
  closeModal.addEventListener("click", closeModalFn);
  uploadModal.addEventListener("click", (e) => {
    if (e.target === uploadModal) closeModalFn();
  });

  lightboxClose.addEventListener("click", closeLightbox);
  lightbox.addEventListener("click", (e) => {
    if (e.target === lightbox) closeLightbox();
  });
  lightboxPrev.addEventListener("click", showPrev);
  lightboxNext.addEventListener("click", showNext);

  // Initial load: show full gallery
  searchPhotos(defaultQuery);
})();
