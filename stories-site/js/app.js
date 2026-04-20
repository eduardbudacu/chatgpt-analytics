/**
 * Stories Site — Application Logic
 * Handles data loading, filtering, rendering, and navigation.
 * All content comes from data/stories.json — zero content in HTML/CSS.
 */

(function () {
  'use strict';

  // --- State ---
  let allStories = [];
  let filteredStories = [];
  let currentIndex = -1;
  let activeFilters = { categories: new Set(), levels: new Set() };
  let searchQuery = '';
  let currentView = 'grid'; // 'grid' | 'timeline'

  // --- DOM refs ---
  const grid = document.getElementById('stories-grid');
  const timelineContainer = document.getElementById('timeline-container');
  const modal = document.getElementById('modal-overlay');
  const modalTitle = document.getElementById('modal-title');
  const modalBody = document.getElementById('modal-body');
  const modalMeta = document.getElementById('modal-meta');
  const storyCount = document.getElementById('story-count');
  const searchInput = document.getElementById('search-box');
  const statTotal = document.getElementById('stat-total');
  const statMonths = document.getElementById('stat-months');
  const statCategories = document.getElementById('stat-categories');

  // --- Load data ---
  async function loadData() {
    try {
      const resp = await fetch('data/stories.json');
      const data = await resp.json();
      allStories = data.stories;
      filteredStories = [...allStories];
      updateStats();
      render();
    } catch (e) {
      grid.innerHTML = '<div class="no-results">Failed to load stories.</div>';
      console.error(e);
    }
  }

  // --- Stats ---
  function updateStats() {
    statTotal.textContent = allStories.length;
    const months = new Set(allStories.map(s => s.date.slice(0, 7)));
    statMonths.textContent = months.size;
    const cats = new Set(allStories.map(s => s.category));
    statCategories.textContent = cats.size;
  }

  // --- Filtering ---
  function applyFilters() {
    filteredStories = allStories.filter(s => {
      if (activeFilters.categories.size > 0 && !activeFilters.categories.has(s.category)) return false;
      if (activeFilters.levels.size > 0 && !activeFilters.levels.has(s.level)) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (s.title.toLowerCase().includes(q) ||
                s.summary.toLowerCase().includes(q) ||
                s.content.toLowerCase().includes(q));
      }
      return true;
    });
    render();
  }

  function toggleFilter(type, value, btn) {
    const set = activeFilters[type];
    if (set.has(value)) {
      set.delete(value);
      btn.classList.remove('active');
    } else {
      set.add(value);
      btn.classList.add('active');
    }
    applyFilters();
  }

  // --- Rendering ---
  function render() {
    storyCount.textContent = `${filteredStories.length} din ${allStories.length} povești`;

    if (currentView === 'grid') {
      grid.style.display = '';
      timelineContainer.style.display = 'none';
      renderGrid();
    } else {
      grid.style.display = 'none';
      timelineContainer.style.display = 'block';
      renderTimeline();
    }
  }

  function renderGrid() {
    if (filteredStories.length === 0) {
      grid.innerHTML = '<div class="no-results">Nicio poveste nu se potrivește filtrelor.</div>';
      return;
    }

    grid.innerHTML = filteredStories.map((s, idx) => `
      <article class="story-card" data-idx="${idx}" role="button" tabindex="0">
        <div class="card-meta">
          <span class="card-badge badge-${s.category}">${s.category_label}</span>
          <span class="level-dot l${s.level}" title="Nivel ${s.level}: ${s.level_label}"></span>
          <span class="card-date">${formatDate(s.date)}</span>
          ${s.model !== 'gpt-4o' ? `<span class="card-model">${s.model}</span>` : ''}
        </div>
        <h2 class="card-title">${escapeHtml(s.title)}</h2>
        <p class="card-summary">${escapeHtml(s.summary)}</p>
      </article>
    `).join('');

    grid.querySelectorAll('.story-card').forEach(card => {
      card.addEventListener('click', () => openStory(parseInt(card.dataset.idx)));
      card.addEventListener('keydown', e => { if (e.key === 'Enter') openStory(parseInt(card.dataset.idx)); });
    });
  }

  function renderTimeline() {
    const byMonth = {};
    filteredStories.forEach((s, idx) => {
      const m = s.date.slice(0, 7);
      if (!byMonth[m]) byMonth[m] = [];
      byMonth[m].push({ ...s, filteredIdx: idx });
    });

    const months = Object.keys(byMonth).sort();

    if (months.length === 0) {
      timelineContainer.innerHTML = '<div class="no-results">Nicio poveste nu se potrivește filtrelor.</div>';
      return;
    }

    timelineContainer.innerHTML = months.map(m => `
      <div class="timeline-month">
        <div class="timeline-month-label">${formatMonth(m)}</div>
        ${byMonth[m].map(s => `
          <div class="timeline-item" data-idx="${s.filteredIdx}">
            <div class="timeline-item-title">${escapeHtml(s.title)}</div>
            <div class="timeline-item-meta">
              <span class="card-badge badge-${s.category}" style="font-size:0.65rem;padding:0.1rem 0.4rem;">${s.category_label}</span>
              · Nivel ${s.level} · ${s.date}
            </div>
          </div>
        `).join('')}
      </div>
    `).join('');

    timelineContainer.querySelectorAll('.timeline-item').forEach(item => {
      item.addEventListener('click', () => openStory(parseInt(item.dataset.idx)));
    });
  }

  // --- Modal ---
  function openStory(idx) {
    currentIndex = idx;
    const s = filteredStories[idx];
    if (!s) return;

    modalTitle.textContent = s.title;
    modalMeta.innerHTML = `
      <span class="card-badge badge-${s.category}">${s.category_label}</span>
      <span class="level-dot l${s.level}" title="Nivel ${s.level}"></span>
      <span style="font-family:var(--font-ui);font-size:0.78rem;color:var(--text-dim);">
        Nivel ${s.level}: ${s.level_label}
      </span>
      <span style="font-family:var(--font-ui);font-size:0.78rem;color:var(--text-dim);">
        · ${formatDate(s.date)} · ${s.model}
      </span>
    `;
    modalBody.innerHTML = s.content_html;

    // Nav buttons
    const prevBtn = document.getElementById('nav-prev');
    const nextBtn = document.getElementById('nav-next');
    prevBtn.disabled = idx <= 0;
    nextBtn.disabled = idx >= filteredStories.length - 1;

    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
    modal.scrollTop = 0;
  }

  function closeModal() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
    currentIndex = -1;
  }

  // --- Utilities ---
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const [y, m, d] = dateStr.split('-');
    const months = ['Ian', 'Feb', 'Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${parseInt(d)} ${months[parseInt(m) - 1]} ${y}`;
  }

  function formatMonth(ym) {
    const [y, m] = ym.split('-');
    const months = ['Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
                     'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie'];
    return `${months[parseInt(m) - 1]} ${y}`;
  }

  // --- Event listeners ---
  function init() {
    // Category filters
    document.querySelectorAll('.filter-btn[data-category]').forEach(btn => {
      btn.addEventListener('click', () => toggleFilter('categories', btn.dataset.category, btn));
    });

    // Level filters
    document.querySelectorAll('.filter-btn[data-level]').forEach(btn => {
      btn.addEventListener('click', () => toggleFilter('levels', parseInt(btn.dataset.level), btn));
    });

    // Search
    searchInput.addEventListener('input', e => {
      searchQuery = e.target.value;
      applyFilters();
    });

    // Modal close
    document.getElementById('modal-close').addEventListener('click', closeModal);
    modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });

    // Nav
    document.getElementById('nav-prev').addEventListener('click', () => {
      if (currentIndex > 0) openStory(currentIndex - 1);
    });
    document.getElementById('nav-next').addEventListener('click', () => {
      if (currentIndex < filteredStories.length - 1) openStory(currentIndex + 1);
    });

    // Keyboard
    document.addEventListener('keydown', e => {
      if (!modal.classList.contains('open')) return;
      if (e.key === 'Escape') closeModal();
      if (e.key === 'ArrowLeft' && currentIndex > 0) openStory(currentIndex - 1);
      if (e.key === 'ArrowRight' && currentIndex < filteredStories.length - 1) openStory(currentIndex + 1);
    });

    // View toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        currentView = btn.dataset.view;
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        render();
      });
    });

    loadData();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
