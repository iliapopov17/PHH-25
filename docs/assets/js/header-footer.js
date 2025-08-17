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

  // Active link highlight (robust for GitHub Pages: user & project pages)
  const normalize = (url) =>
    new URL(url, location.href)
      .pathname
      .replace(/\/index\.html$/i, '')  // /repo/index.html -> /repo
      .replace(/\/+$/, '');            // /repo/ -> /repo

  const herePath = normalize(location.href);

  // Clear any previous state
  hdr.querySelectorAll('[data-nav].is-active').forEach(el => el.classList.remove('is-active'));

  // Mark only exact match as active
  hdr.querySelectorAll('[data-nav]').forEach(a => {
    const targetPath = normalize(a.getAttribute('href'));
    if (targetPath === herePath) {
      a.classList.add('is-active');
      a.setAttribute('aria-current', 'page');
    } else {
      a.removeAttribute('aria-current');
    }
  });
} // ←←← this brace was missing

(async () => {
  try {
    // avoid double injection
    if (!document.querySelector('[data-injected="header"]')) {
      const headerHTML = await fetchText(headerURL);
      const header = document.createElement('div');
      header.setAttribute('data-injected', 'header');
      header.innerHTML = headerHTML;
      document.body.prepend(header);
      setupHeaderBehavior(header); // wire behavior after insertion
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