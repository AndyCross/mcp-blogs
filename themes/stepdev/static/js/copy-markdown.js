(function () {
  var btn = document.getElementById('copy-md-btn');
  if (!btn) return;

  var mdUrl = window.location.pathname.replace(/\/?$/, '/') + 'index.md';
  var cachedMd = null;
  var defaultLabel = btn.textContent;

  function prefetch() {
    if (!cachedMd) {
      fetch(mdUrl)
        .then(function (r) { return r.text(); })
        .then(function (t) { cachedMd = t; });
    }
  }

  function showCopied() {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(function () {
      btn.textContent = defaultLabel;
      btn.classList.remove('copied');
    }, 2000);
  }

  function copyText(text) {
    navigator.clipboard.writeText(text).then(showCopied);
  }

  btn.addEventListener('mouseenter', prefetch);
  btn.addEventListener('focus', prefetch);
  btn.addEventListener('touchstart', prefetch, { passive: true });

  btn.addEventListener('click', function () {
    if (cachedMd) {
      copyText(cachedMd);
    } else {
      fetch(mdUrl)
        .then(function (r) { return r.text(); })
        .then(function (t) {
          cachedMd = t;
          copyText(t);
        });
    }
  });
})();
