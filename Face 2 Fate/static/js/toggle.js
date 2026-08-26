/* ============================================================
   toggle.js — Face 2 Fate Theme Toggle
   Include at the bottom of <body> on every page (or in base.html).
   ============================================================ */

(function () {
  var STORAGE_KEY = 'f2f-theme';

  function getPreferred() {
    var saved = localStorage.getItem(STORAGE_KEY);
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    var btn = document.getElementById('theme-toggle');
    if (btn) btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    updateIcon(theme);
  }

  function updateIcon(theme) {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.innerHTML = theme === 'dark' ? sunSVG() : moonSVG();
  }

  function sunSVG() {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>';
  }

  function moonSVG() {
    return '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
  }

  function injectButton() {
    if (document.getElementById('theme-toggle')) return;
    var btn = document.createElement('button');
    btn.id = 'theme-toggle';
    btn.setAttribute('aria-label', 'Toggle theme');
    btn.addEventListener('click', function () {
      var current = document.documentElement.getAttribute('data-theme') || 'dark';
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });
    document.body.appendChild(btn);
    updateIcon(document.documentElement.getAttribute('data-theme') || 'dark');
  }

  /* ── Use matchMedia — same breakpoint as CSS ── */
  var mobileQuery = window.matchMedia('(max-width: 768px)');

  function isMobile() {
    return mobileQuery.matches;
  }

  /* ── Show / Hide ── */
  var hideTimer = null;

  function showToggle() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.style.opacity = '1';
    btn.style.pointerEvents = 'auto';
  }

  function hideToggle() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.style.opacity = '0';
    btn.style.pointerEvents = 'none';
  }

  function onScroll() {
    showToggle();
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hideToggle, 2000);
  }

  function enableMobileHide() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;
    /* Hide immediately */
    hideToggle();
    /* Show briefly on load */
    showToggle();
    hideTimer = setTimeout(hideToggle, 2000);
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function disableMobileHide() {
    clearTimeout(hideTimer);
    window.removeEventListener('scroll', onScroll);
    showToggle();
  }

  function initScrollBehavior() {
    var btn = document.getElementById('theme-toggle');
    if (!btn) return;

    btn.style.transition = 'opacity 0.4s ease, transform 0.2s ease, background 0.3s, border-color 0.3s, color 0.3s';

    if (isMobile()) {
      enableMobileHide();
    } else {
      showToggle();
    }

    /* React to viewport changes (rotation, resize, devtools) */
    mobileQuery.addEventListener('change', function (e) {
      if (e.matches) {
        enableMobileHide();
      } else {
        disableMobileHide();
      }
    });
  }

  /* ── Init ── */
  applyTheme(getPreferred());

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      injectButton();
      initScrollBehavior();
    });
  } else {
    injectButton();
    initScrollBehavior();
  }
})();