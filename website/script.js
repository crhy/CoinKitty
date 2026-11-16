// CoinKitty.org — mobile navigation and external-link labelling only.
// The page, its documents and its images all work without this file.
(function () {
  'use strict';

  var toggle = document.getElementById('nav-toggle');
  var nav = document.getElementById('site-nav');
  if (!toggle || !nav) {
    return;
  }

  var isOpen = false;

  function setMenu(open) {
    isOpen = open;
    if (open) {
      nav.classList.add('open');
    } else {
      nav.classList.remove('open');
    }
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  toggle.addEventListener('click', function () {
    setMenu(!isOpen);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && isOpen) {
      setMenu(false);
      toggle.focus();
    }
  });

  // When the header switches back to the always-visible desktop row, drop the
  // mobile menu state so it cannot stay stuck open.
  var narrow = window.matchMedia('(max-width: 58rem)');
  var onNarrowChange = function (event) {
    if (!event.matches) {
      setMenu(false);
    }
  };
  if (typeof narrow.addEventListener === 'function') {
    narrow.addEventListener('change', onNarrowChange);
  } else if (typeof narrow.addListener === 'function') {
    narrow.addListener(onNarrowChange);
  }

  // Label links that leave CoinKitty.org, so nothing looks like a broken
  // internal link and no third party is loaded by accident.
  var origin = (location.host || '').toLowerCase();
  var links = document.querySelectorAll('a[href]');
  Array.prototype.forEach.call(links, function (link) {
    var href = link.getAttribute('href') || '';
    if (/^https:\/\//i.test(href)) {
      var host = link.hostname.toLowerCase();
      if (host && host !== origin && !/\.coinkitty\.org$/i.test(host)) {
        link.setAttribute('rel', 'noopener noreferrer');
        link.classList.add('external');
      }
    }
  });
})();
