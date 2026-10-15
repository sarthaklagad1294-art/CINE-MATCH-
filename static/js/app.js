(() => {
  const state = { mode: "title", recommendations: [], filtered: [], searchLabel: "", movies: [] };
  const $ = (selector) => document.querySelector(selector);
  const input = $("#searchInput");
  const form = $("#searchForm");
  const suggestions = $("#suggestions");
  const resultsGrid = $("#resultsGrid");
  const emptyState = $("#emptyState");
  const loadingState = $("#loadingState");
  const filterBar = $("#filterBar");
  const modal = $("#movieModal");
  let suggestTimer;

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  const truncate = (value, length = 150) => value && value.length > length ? `${value.slice(0, length).trim()}…` : (value || "No overview available.");
  const showLoading = (show) => { loadingState.hidden = !show; if (show) { resultsGrid.innerHTML = ""; emptyState.hidden = true; } };

  function movieCard(movie) {
    const genres = (movie.genres || []).slice(0, 2).join(" · ") || "Catalog pick";
    const match = typeof movie.similarity_percent === "number" ? `<span class="match-badge">${movie.similarity_percent.toFixed(1)}% match</span>` : "";
    return `<article class="movie-card" data-movie-id="${movie.id}" tabindex="0" role="button" aria-label="Open ${escapeHtml(movie.title)}">
      <div class="movie-poster"><img src="${escapeHtml(movie.poster_url)}" alt="${escapeHtml(movie.title)} poster" loading="lazy">${match}</div>
      <div class="card-body"><div class="card-meta"><span>${escapeHtml(movie.year)}</span><span class="rating">★ ${Number(movie.rating || 0).toFixed(1)}</span></div><h3>${escapeHtml(movie.title)}</h3><p class="genre-line">${escapeHtml(genres)}</p><p class="overview">${escapeHtml(truncate(movie.overview))}</p></div>
    </article>`;
  }

  function renderResults() {
    const genre = $("#genreFilter").value;
    const minimum = Number($("#ratingFilter").value);
    const sort = $("#sortFilter").value;
    let movies = state.recommendations.filter((movie) => (genre === "all" || (movie.genres || []).includes(genre)) && Number(movie.rating || 0) >= minimum);
    movies.sort((a, b) => sort === "rating" ? b.rating - a.rating : sort === "year" ? String(b.year).localeCompare(String(a.year)) : (b.similarity || 0) - (a.similarity || 0));
    state.filtered = movies;
    resultsGrid.innerHTML = movies.map(movieCard).join("");
    emptyState.hidden = movies.length > 0;
    $("#resultCount").textContent = movies.length ? `· ${movies.length}` : "";
    filterBar.hidden = state.recommendations.length === 0;
    resultsGrid.querySelectorAll(".movie-card").forEach((card) => { card.addEventListener("click", () => openMovie(card.dataset.movieId)); card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") openMovie(card.dataset.movieId); }); });
  }

  function populateGenres() {
    const current = $("#genreFilter").value;
    const genres = [...new Set(state.recommendations.flatMap((movie) => movie.genres || []))].sort();
    $("#genreFilter").innerHTML = `<option value="all">All genres</option>${genres.map((genre) => `<option value="${escapeHtml(genre)}">${escapeHtml(genre)}</option>`).join("")}`;
    $("#genreFilter").value = genres.includes(current) ? current : "all";
  }

  async function runSearch(event) {
    if (event) event.preventDefault();
    const query = input.value.trim();
    if (!query) { input.focus(); return; }
    closeSuggestions(); showLoading(true);
    try {
      const response = state.mode === "title" ? await fetch(`/api/recommend?title=${encodeURIComponent(query)}&n=12`) : await fetch("/api/recommend-text", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, n: 12 }) });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not prepare recommendations.");
      state.recommendations = payload.recommendations || [];
      state.searchLabel = payload.mode === "title" && state.recommendations[0]?.matched_title ? `Similar to “${state.recommendations[0].matched_title}”` : `For “${query}”`;
      $("#resultsContext").textContent = state.searchLabel;
      populateGenres(); renderResults();
      $("#resultsSection").scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      state.recommendations = []; filterBar.hidden = true; resultsGrid.innerHTML = ""; emptyState.hidden = false; $("#resultsContext").textContent = error.message; $("#resultCount").textContent = "";
    } finally { showLoading(false); }
  }

  async function loadSuggestions() {
    if (state.mode !== "title" || input.value.trim().length < 2) { closeSuggestions(); return; }
    try {
      const response = await fetch(`/api/movies?q=${encodeURIComponent(input.value.trim())}&limit=6`);
      const payload = await response.json();
      const movies = payload.movies || [];
      if (!movies.length) { closeSuggestions(); return; }
      suggestions.innerHTML = movies.map((movie) => `<button class="suggestion" type="button" data-title="${escapeHtml(movie.title)}"><span>${escapeHtml(movie.title)}</span><small>${escapeHtml(movie.year)}</small></button>`).join("");
      suggestions.classList.add("visible"); input.setAttribute("aria-expanded", "true");
      suggestions.querySelectorAll(".suggestion").forEach((button) => button.addEventListener("click", () => { input.value = button.dataset.title; closeSuggestions(); runSearch(); }));
    } catch (_) { closeSuggestions(); }
  }

  function closeSuggestions() { suggestions.classList.remove("visible"); input.setAttribute("aria-expanded", "false"); }

  function switchMode(mode) {
    state.mode = mode;
    document.querySelectorAll(".mode-btn").forEach((button) => { const active = button.dataset.mode === mode; button.classList.toggle("active", active); button.setAttribute("aria-selected", String(active)); });
    input.placeholder = mode === "title" ? "Try “Interstellar” or another film you love" : "Try “a hopeful space adventure with robots”";
    $("#modeHint").textContent = mode === "title" ? "We’ll find movies similar to a title you know." : "We’ll match your words to the catalog’s story signals.";
    closeSuggestions();
  }

  async function openMovie(id) {
    modal.hidden = false; document.body.classList.add("modal-open"); $("#modalContent").innerHTML = `<div class="loading-state"><span class="spinner"></span><span>Opening the reel…</span></div>`;
    try {
      const response = await fetch(`/api/movie/${id}`); const movie = await response.json();
      if (!response.ok) throw new Error(movie.error || "Movie not found.");
      const tags = (movie.genres || []).map((genre) => `<span class="tag">${escapeHtml(genre)}</span>`).join("");
      const more = (movie.more_like_this || []).map((item) => `<button class="more-item" type="button" data-more-id="${item.id}"><img src="${escapeHtml(item.poster_url)}" alt=""><span>${escapeHtml(item.title)}</span></button>`).join("");
      $("#modalContent").innerHTML = `<div class="modal-layout"><img src="${escapeHtml(movie.poster_url)}" alt="${escapeHtml(movie.title)} poster"><div class="modal-copy"><p class="eyebrow">Movie detail</p><h2 id="modalTitle">${escapeHtml(movie.title)}</h2><div class="modal-subline">${escapeHtml(movie.year)} · ★ ${Number(movie.rating || 0).toFixed(1)} · Directed by ${escapeHtml(movie.director)}</div><p>${escapeHtml(movie.overview)}</p><div class="tag-list">${tags}</div><p><strong>Cast:</strong> ${escapeHtml((movie.cast || []).join(", ") || "Not listed")}</p><div class="more-title">More like this</div><div class="more-list">${more || "<span class='modal-subline'>No nearby titles yet.</span>"}</div></div></div>`;
      $("#modalContent").querySelectorAll("[data-more-id]").forEach((item) => item.addEventListener("click", () => openMovie(item.dataset.moreId)));
    } catch (error) { $("#modalContent").innerHTML = `<div class="empty-state"><h3>Couldn’t open that title</h3><p>${escapeHtml(error.message)}</p></div>`; }
  }

  function closeModal() { modal.hidden = true; document.body.classList.remove("modal-open"); }

  document.querySelectorAll(".mode-btn").forEach((button) => button.addEventListener("click", () => switchMode(button.dataset.mode)));
  form.addEventListener("submit", runSearch);
  input.addEventListener("input", () => { clearTimeout(suggestTimer); suggestTimer = setTimeout(loadSuggestions, 180); });
  input.addEventListener("keydown", (event) => { if (event.key === "Escape") closeSuggestions(); });
  document.addEventListener("click", (event) => { if (!event.target.closest("#searchPanel")) closeSuggestions(); });
  $("#ratingFilter").addEventListener("input", (event) => { $("#ratingValue").textContent = Number(event.target.value).toFixed(1); renderResults(); });
  $("#genreFilter").addEventListener("change", renderResults); $("#sortFilter").addEventListener("change", renderResults);
  $("#modalClose").addEventListener("click", closeModal); modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); }); document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !modal.hidden) closeModal(); });
  document.querySelectorAll(".trend-card").forEach((card) => { card.addEventListener("click", () => openMovie(card.dataset.movieId)); card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") openMovie(card.dataset.movieId); }); });
  $("#browseAllBtn").addEventListener("click", () => { input.value = ""; $("#resultsContext").textContent = "Browse the complete catalog via autocomplete."; input.focus(); });
})();
