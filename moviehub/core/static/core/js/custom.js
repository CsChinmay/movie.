/* custom.js - main site JS for MovieHub
   Put in core/static/core/js/custom.js
   Author: ChatGPT (adapted)
*/

/* ===========================
   Utility / small helpers
   =========================== */
const MovieHub = (function () {
  // internal helpers
  function getCookie(name) {
    if (!document.cookie) return null;
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
      c = c.trim();
      if (c.startsWith(name + '=')) {
        return decodeURIComponent(c.substring(name.length + 1));
      }
    }
    return null;
  }

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }
  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function safeJSON(res) {
    return res.json().catch(() => ({}));
  }

  function showToast(message, level = 'info') {
    // minimal toast fallback using alert if no toast system exists
    // level: 'info'|'success'|'error'
    try {
      // prefer Bootstrap 5 toast if available on page
      const toastContainerId = '__moviehub_toast_container';
      let container = document.getElementById(toastContainerId);
      if (!container) {
        container = document.createElement('div');
        container.id = toastContainerId;
        container.style.position = 'fixed';
        container.style.right = '12px';
        container.style.bottom = '12px';
        container.style.zIndex = 20000;
        document.body.appendChild(container);
      }
      const toast = document.createElement('div');
      toast.className = 'toast align-items-center text-bg-dark border-secondary';
      toast.setAttribute('role', 'alert');
      toast.style.minWidth = '220px';
      toast.innerHTML = `
        <div class="d-flex">
          <div class="toast-body small">${message}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
      `;
      container.appendChild(toast);
      const bsToast = new bootstrap.Toast(toast, { delay: 3500 });
      bsToast.show();
      // remove after hidden
      toast.addEventListener('hidden.bs.toast', () => toast.remove());
    } catch (e) {
      // fallback
      alert(message);
    }
  }

  /* ===========================
     Theme toggle
     =========================== */
  function initThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    const icon = document.getElementById('themeIcon');
    if (!toggle || !icon) return;
    function applyTheme(t) {
      if (t === 'light') {
        document.documentElement.classList.add('light');
        icon.className = 'fa fa-sun';
      } else {
        document.documentElement.classList.remove('light');
        icon.className = 'fa fa-moon';
      }
      try { localStorage.setItem('moviehub_theme', t); } catch(e){/*ignore*/}
    }
    const saved = (localStorage.getItem('moviehub_theme')) || 'dark';
    applyTheme(saved);
    toggle.addEventListener('click', () => {
      const now = document.documentElement.classList.contains('light') ? 'light' : 'dark';
      applyTheme(now === 'dark' ? 'light' : 'dark');
    });
  }

  /* ===========================
     Lazy load images (basic)
     =========================== */
  function initLazyImages() {
    const imgs = qsa('img[data-lazy]');
    if (!imgs.length) return;
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(entries => {
        entries.forEach(en => {
          if (en.isIntersecting) {
            const img = en.target;
            img.src = img.dataset.lazy;
            img.removeAttribute('data-lazy');
            io.unobserve(img);
          }
        });
      }, {rootMargin: '200px'});
      imgs.forEach(i => io.observe(i));
    } else {
      // fallback: load all
      imgs.forEach(i => { i.src = i.dataset.lazy; i.removeAttribute('data-lazy'); });
    }
  }

  /* ===========================
     Bootstrap tooltips initializer
     =========================== */
  function initTooltips() {
    const tipEls = qsa('[data-bs-toggle="tooltip"]');
    tipEls.forEach(el => {
      try { new bootstrap.Tooltip(el); } catch (e) {}
    });
  }

  /* ===========================
     Movie modal (details + trailer + cast + reviews)
     ===========================
     - Exposes openMovieModal(id)
     - Expects API at window.urls.movie_detail_base or /api/movie/<id>/
  */
  async function openMovieModal(movieId) {
    if (!movieId) return;
    const modalEl = document.getElementById('movieModal');
    const modalContent = document.getElementById('modalContent');
    if (!modalEl || !modalContent) {
      console.error('Modal container missing (#movieModal/#modalContent).');
      return;
    }

    // loading UI
    modalContent.innerHTML = `
      <div class="p-5 text-center">
        <div class="spinner-border text-warning" role="status"></div>
        <p class="mt-2">Loading movie details...</p>
      </div>
    `;

    // show modal quickly (spinner)
    const bsModal = new bootstrap.Modal(modalEl);
    bsModal.show();

    // build fetch URL: try window.urls.movie_detail_api or fallback /api/movie/<id>/
    let apiUrl = `/api/movie/${movieId}/`;
    if (window.urls && window.urls.movie_detail_api) apiUrl = window.urls.movie_detail_api.replace('{id}', movieId);
    // attempt to fetch details
    try {
      const res = await fetch(apiUrl, { headers: {'X-Requested-With': 'XMLHttpRequest'} });
      if (!res.ok) {
        modalContent.innerHTML = `<div class="p-4 text-center text-danger">Failed to load movie data.</div>`;
        return;
      }
      const data = await res.json();

      // data expected: movie fields, videos, credits, similar
      const trailer = (data.videos && data.videos.results) ? data.videos.results.find(v => v.site === 'YouTube') : null;
      const cast = (data.credits && data.credits.cast) ? data.credits.cast.slice(0,12) : [];
      const poster = data.poster_path ? `https://image.tmdb.org/t/p/w500${data.poster_path}` : '/static/core/images/placeholder_movie.png';

      // cast HTML
      let castHtml = '';
      if (cast.length) {
        castHtml = `
          <h6 class="mt-3">Cast</h6>
          <div class="d-flex gap-2 overflow-auto py-2">
            ${cast.map(c => `
              <div class="text-center" style="width:120px;cursor:pointer;">
                <img src="${c.profile_path ? 'https://image.tmdb.org/t/p/w185' + c.profile_path : '/static/core/images/placeholder_person.png'}"
                     class="rounded mb-1" style="height:120px;width:100%;object-fit:cover;" onerror="this.src='/static/core/images/placeholder_person.png'">
                <div class="small text-truncate">${c.name}</div>
                <div class="small text-muted">${c.character || ''}</div>
              </div>
            `).join('')}
          </div>
        `;
      }

      // trailer embed
      const trailerHtml = trailer ? `
        <h6 class="mt-3">Trailer</h6>
        <div class="ratio ratio-16x9 mb-2">
          <iframe src="https://www.youtube.com/embed/${trailer.key}?rel=0&modestbranding=1" 
                  title="Trailer" allowfullscreen></iframe>
        </div>
        <a class="small text-muted" target="_blank" href="https://youtube.com/watch?v=${trailer.key}">Open on YouTube</a>
      ` : `<div class="small text-muted mt-3">No trailer available.</div>`;

      // modal content assembled
      modalContent.innerHTML = `
        <div class="modal-header border-secondary">
          <h5 class="modal-title">${escapeHtml(data.title || data.name || 'Movie')}</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-md-4">
              <img src="${poster}" class="img-fluid rounded" onerror="this.src='/static/core/images/placeholder_movie.png'">
            </div>
            <div class="col-md-8">
              <p class="text-secondary">${escapeHtml(data.overview || 'No overview available.')}</p>
              <div class="small text-muted">
                <strong>Release:</strong> ${data.release_date || 'N/A'} • 
                <strong>Runtime:</strong> ${data.runtime || 'N/A'} mins
              </div>
              ${trailerHtml}
              ${castHtml}
            </div>
          </div>

          <div class="mt-3" id="movieReviewsWrapper">
            <!-- reviews will be loaded here -->
            <div id="reviewsLoading" class="small text-muted">Loading reviews...</div>
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button class="btn btn-sm btn-outline-light" data-bs-dismiss="modal">Close</button>
        </div>
      `;

      // after rendering show reviews
      setTimeout(() => { try { refreshReviews(movieId); } catch(e){} }, 200);

    } catch (err) {
      console.error('openMovieModal error', err);
      modalContent.innerHTML = `<div class="p-4 text-center text-danger">Failed to load movie details.</div>`;
    }
  }

  /* ===========================
     Reviews: refresh, add, delete (AJAX)
     =========================== */
  async function refreshReviews(tmdbId) {
    if (!tmdbId) return;
    // expect window.urls.getReviewsFor(tmdbId) or window.urls.get_reviews + tmdbId
    let url = (window.urls && typeof window.urls.getReviewsFor === 'function') ?
      window.urls.getReviewsFor(tmdbId) : ( (window.urls && window.urls.get_reviews) ? (window.urls.get_reviews + String(tmdbId) + '/') : `/reviews/${tmdbId}/` );

    try {
      const res = await fetch(url, { headers: {'X-Requested-With': 'XMLHttpRequest'} });
      const data = await res.json();
      if (data && data.ok && data.html) {
        // place returned HTML into #movieReviewsWrapper or reviewsRoot location
        const wrapper = document.getElementById('movieReviewsWrapper');
        if (wrapper) {
          wrapper.innerHTML = data.html;
        } else {
          // fallback: replace reviewsRoot element
          const root = document.querySelector(`#reviewsRoot[data-tmdb-id="${tmdbId}"]`);
          if (root) root.outerHTML = data.html;
        }
      } else {
        const wrapper = document.getElementById('movieReviewsWrapper');
        if (wrapper) wrapper.innerHTML = `<div class="small text-muted">No reviews yet.</div>`;
      }
    } catch (err) {
      console.error('refreshReviews error', err);
    }
  }

  // Submit review (delegated submit handler)
  function initReviewFormHandler() {
    document.addEventListener('submit', async (ev) => {
      const form = ev.target.closest && ev.target.closest('#reviewForm');
      if (!form) return;
      ev.preventDefault();
      const tmdbId = form.dataset.tmdbId || form.querySelector('input[name="tmdb_id"]')?.value;
      if (!tmdbId) {
        showToast('Missing movie id for review', 'error');
        return;
      }
      const fd = new FormData(form);
      try {
        const res = await fetch(window.urls && window.urls.add_review ? window.urls.add_review : '/reviews/add/', {
          method: 'POST',
          headers: {'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest'},
          body: fd
        });
        const data = await res.json();
        if (data && data.ok && data.html) {
          // replace reviews block
          const parser = new DOMParser();
          const doc = parser.parseFromString(data.html, 'text/html');
          const newRoot = doc.querySelector('#reviewsRoot');
          if (newRoot) {
            const old = document.querySelector(`#reviewsRoot[data-tmdb-id="${tmdbId}"]`);
            if (old) old.outerHTML = newRoot.outerHTML;
            else {
              const wrapper = document.getElementById('movieReviewsWrapper');
              if (wrapper) wrapper.innerHTML = data.html;
            }
          } else {
            // fallback: just reload reviews area
            const wrapper = document.getElementById('movieReviewsWrapper');
            if (wrapper) wrapper.innerHTML = data.html;
          }
          showToast('Review saved', 'success');
        } else {
          const feedback = form.querySelector('#reviewFormFeedback');
          if (feedback) {
            feedback.classList.remove('d-none');
            feedback.textContent = data.error || 'Failed to save review.';
          } else showToast(data.error || 'Failed to save review', 'error');
        }
      } catch (err) {
        console.error('submit review error', err);
        showToast('Failed to submit review', 'error');
      }
    });

    // delete handler delegated
    document.addEventListener('click', async (ev) => {
      const btn = ev.target.closest && ev.target.closest('.btn-delete-review');
      if (!btn) return;
      const id = btn.dataset.id;
      if (!id) return;
      if (!confirm('Delete your review?')) return;
      const url = (window.urls && typeof window.urls.deleteReviewFor === 'function') ? window.urls.deleteReviewFor(id) : (window.urls && window.urls.delete_review ? window.urls.delete_review + String(id) + '/' : `/reviews/delete/${id}/`);
      try {
        const res = await fetch(url, { method: 'POST', headers: {'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest'} });
        const data = await res.json();
        if (data && data.ok && data.html) {
          // update reviews block
          const parser = new DOMParser();
          const doc = parser.parseFromString(data.html, 'text/html');
          const newRoot = doc.querySelector('#reviewsRoot');
          if (newRoot) {
            const tmdbId = newRoot.dataset.tmdbId;
            const old = document.querySelector(`#reviewsRoot[data-tmdb-id="${tmdbId}"]`);
            if (old) old.outerHTML = newRoot.outerHTML;
          }
        } else {
          showToast(data.error || 'Failed to delete review', 'error');
        }
      } catch (err) {
        console.error('delete review error', err);
        showToast('Failed to delete review', 'error');
      }
    });
  }

  /* ===========================
     Pagination / Load more
     =========================== */
  function initLoadMore() {
    // delegated click for loadMoreBtn
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest && ev.target.closest('#loadMoreBtn');
      if (!btn) return;
      const moviesGrid = document.getElementById('moviesGrid');
      if (!moviesGrid) return;
      const next = parseInt(btn.dataset.nextPage || (parseInt(moviesGrid.dataset.page || '1') + 1), 10);
      const total = parseInt(moviesGrid.dataset.totalPages || moviesGrid.dataset.total_pages || '1', 10);
      if (next > total) {
        btn.remove();
        return;
      }
      moviehub.loadPage(next);
    });
  }

  async function loadPage(page) {
    const moviesGrid = document.getElementById('moviesGrid');
    if (!moviesGrid) return;
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) spinner.classList.remove('d-none');

    try {
      const url = new URL(window.location.href);
      url.searchParams.set('page', page);
      url.searchParams.set('ajax', '1');
      const res = await fetch(url.toString(), { headers: {'X-Requested-With': 'XMLHttpRequest'} });
      const data = await res.json();
      if (!data || !data.ok) {
        console.error('loadPage failed', data);
        showToast('Failed to load more movies', 'error');
        return;
      }
      // data.html expected to be series of column cards (matching _movie_cards.html)
      const temp = document.createElement('div');
      temp.innerHTML = data.html;
      // append children
      while (temp.firstElementChild) moviesGrid.appendChild(temp.firstElementChild);
      // update page attributes
      moviesGrid.dataset.page = data.page || page;
      moviesGrid.dataset.totalPages = data.total_pages || data.totalPages || moviesGrid.dataset.totalPages || '1';
      // update loadMoreBtn
      const loadBtn = document.getElementById('loadMoreBtn');
      const totalPages = parseInt(moviesGrid.dataset.totalPages || '1', 10);
      if (page >= totalPages) {
        if (loadBtn) loadBtn.remove();
        const noMore = document.createElement('div');
        noMore.className = 'small text-muted text-center mt-3';
        noMore.textContent = 'No more results.';
        moviesGrid.parentElement.appendChild(noMore);
      } else if (loadBtn) {
        loadBtn.dataset.nextPage = String(page + 1);
      }
    } catch (err) {
      console.error('loadPage error', err);
      showToast('Failed to load more movies', 'error');
    } finally {
      if (spinner) spinner.classList.add('d-none');
    }
  }

  /* ===========================
     Watchlist toggle and quick handlers
     =========================== */
  async function toggleWatchlist(movieId, title=null, poster=null, btn=null) {
    if (!movieId) return;
    try {
      const body = new URLSearchParams();
      body.set('movie_id', String(movieId));
      if (title) body.set('title', title);
      if (poster) body.set('poster_path', poster);
      const res = await fetch(window.urls && window.urls.toggle_watchlist ? window.urls.toggle_watchlist : '/watchlist/toggle/', {
        method: 'POST',
        headers: {'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded'},
        body: body.toString()
      });
      const data = await res.json();
      if (data && data.status) {
        if (data.status === 'added') {
          if (btn) btn.classList.add('active-watch');
          showToast('Added to watchlist', 'success');
        } else if (data.status === 'removed') {
          if (btn) btn.classList.remove('active-watch');
          showToast('Removed from watchlist', 'info');
        }
      } else {
        showToast(data.error || 'Failed to update watchlist', 'error');
      }
    } catch (err) {
      console.error('toggleWatchlist error', err);
      showToast('Failed to update watchlist', 'error');
    }
  }

  function initQuickWatchlistButtons() {
    // delegate click for .quick-watchlist and .watchlist-btn existing classes
    document.addEventListener('click', (ev) => {
      const btn = ev.target.closest && ev.target.closest('.quick-watchlist, .watchlist-btn');
      if (!btn) return;
      const movieId = btn.dataset.id || btn.dataset.tmdbId;
      const title = btn.dataset.title;
      const poster = btn.dataset.poster;
      // If not logged in, server will return 403 or redirect — we simply call toggle
      toggleWatchlist(movieId, title, poster, btn);
    });
  }

  /* ===========================
     Watchlist page bulk remove handler
     =========================== */
  function initWatchlistBulk() {
    const bulkForm = qs('#bulkRemoveForm');
    if (!bulkForm) return;
    bulkForm.addEventListener('submit', async (ev) => {
      const idsField = qs('#bulk_ids');
      if (!idsField || !idsField.value.trim()) {
        ev.preventDefault();
        alert('Select at least one item to remove.');
        return;
      }
      // let normal submit happen or handle via fetch here
    });
  }

  /* ===========================
     Misc: cast carousel init & small helpers
     =========================== */
  function initCastCarousels() {
    // initialize any bootstrap carousels we inserted dynamically (no-op if none)
    const carousels = qsa('.carousel');
    carousels.forEach(c => {
      try { new bootstrap.Carousel(c); } catch (e) {}
    });
  }

  /* ===========================
     Escape helper (for safe text insertion)
     =========================== */
  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  }

  /* ===========================
     Initialization wiring
     =========================== */
  function initAll() {
    // helpers
    initThemeToggle();
    initTooltips();
    initLazyImages();

    // core features
    initReviewFormHandler();
    initLoadMore();
    initQuickWatchlistButtons();
    initWatchlistBulk();

    // Delegated click to open modal for any .movie-card quick-open
    document.addEventListener('click', (ev) => {
      const card = ev.target.closest && ev.target.closest('.movie-card');
      if (!card) return;
      // avoid when clicking quick-action buttons inside card
      const quick = ev.target.closest && ev.target.closest('.quick-watchlist, .quick-open, .remove-watch-btn');
      if (quick) return;
      // try to read data-id or inline onclick attribute fallback
      const id = card.dataset.id || card.dataset.tmdbId;
      if (id) openMovieModal(id);
    });

    // Expose some functions globally
    window.openMovieModal = openMovieModal;
    window.refreshReviews = refreshReviews;
    window.moviehub = window.moviehub || {};
    window.moviehub.loadPage = loadPage;
    window.moviehub.toggleWatchlist = toggleWatchlist;
  }

  // public API
  return {
    init: initAll,
    openMovieModal,
    refreshReviews,
    loadPage,
    toggleWatchlist,
    escapeHtml
  };
})();

/* Auto-init when DOM ready */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => MovieHub.init());
} else {
  MovieHub.init();
}
