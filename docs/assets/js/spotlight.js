// ========== spotlight.js ==========
// Activates per-person spotlight if #members and #photo are present
(function () {
  const photo = document.getElementById('photo');
  const list  = document.getElementById('members');
  if (!photo || !list) return;

  function setSpotlight(li) {
    const x = li.getAttribute('data-x');
    const y = li.getAttribute('data-y');
    const r = li.getAttribute('data-r');
    if (x && y && r) {
      photo.style.setProperty('--x', x + '%');
      photo.style.setProperty('--y', y + '%');
      photo.style.setProperty('--r', r + 'px');
      photo.classList.add('on');
    }
  }
  function clearSpotlight(e){
    if (e && e.relatedTarget && list.contains(e.relatedTarget)) return;
    photo.classList.remove('on');
  }

  list.addEventListener('mouseover',  e => { if (e.target.tagName === 'LI') setSpotlight(e.target); });
  list.addEventListener('focusin',    e => { if (e.target.tagName === 'LI') setSpotlight(e.target); });
  list.addEventListener('mouseout',   clearSpotlight);
  list.addEventListener('focusout',   clearSpotlight);
})();