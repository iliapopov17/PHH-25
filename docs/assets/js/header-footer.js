// docs/assets/js/header-footer.js
// Inject header & footer and wire up mobile nav after insertion.

(() => {
  // Accent variable (optional)
  const accent = '#0b63f6';
  const s = document.createElement('style');
  s.textContent = `:root{ --accent:${accent}; }`;
  document.head.appendChild(s);
})();

const moduleBase = new URL('.', import.meta.url);
const headerURL = new URL('../../partials/header.html', moduleBase);
const footerURL = new URL('../../partials/footer.html', moduleBase);

async function fetchText(url) {
  const res = await fetch(url, { credentials: 'same-origin' });
  if (!res.ok) throw new Error(`Failed to load ${url}: ${res.status}`);
  return res.text();
}

function setupHeaderBehavior(root) {
  const hdr = root.querySelector('header.site-header');
  if (!hdr) return;

  const btn = hdr.querySelector('.nav-toggle');
  const nav = hdr.querySelector('.site-nav');
  if (!btn || !nav) return;

  const toggle = () => {
    const open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', String(open));
  };

  btn.addEventListener('click', toggle);

  // Close on link click (mobile UX)
  nav.addEventListener('click', (e) => {
    if (e.target.closest('a')) {
      nav.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    }
  });

  // Close on Esc
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && nav.classList.contains('open')) {
      nav.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
      btn.focus();
    }
  });

  // Active link highlight
  const here = location.pathname.replace(/\/+$/, '') || '/';
  hdr.querySelectorAll('[data-nav]').forEach(a => {
    const href = new URL(a.getAttribute('href'), location.href);
    const path = href.pathname.replace(/\/+$/, '') || '/';
    if (path === here) a.classList.add('is-active');
    else if (here.startsWith(path) && path !== '/') a.classList.add('is-active');
  });
}

(async () => {
  try {
    // avoid double injection
    if (!document.querySelector('[data-injected="header"]')) {
      const headerHTML = await fetchText(headerURL);
      const header = document.createElement('div');
      header.setAttribute('data-injected', 'header');
      header.innerHTML = headerHTML;
      document.body.prepend(header);
      setupHeaderBehavior(header); // <-- ВАЖНО: повесить поведение после вставки
    }

    if (!document.querySelector('[data-injected="footer"]')) {
      const footerHTML = await fetchText(footerURL);
      const footer = document.createElement('div');
      footer.setAttribute('data-injected', 'footer');
      footer.innerHTML = footerHTML;
      document.body.append(footer);
    }
  } catch (e) {
    console.error('[header-footer] injection failed:', e);
  }
})();