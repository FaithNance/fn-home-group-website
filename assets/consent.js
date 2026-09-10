/* ==========================================================================
   FN Home Group — Privacy notice and analytics consent
   Loaded on every page by build/templates/base.html.

   Google Consent Mode does the actual gating: base.html sets
   analytics_storage to denied before the Google tag runs, so Google Analytics
   reads and writes no cookie until a visitor accepts. This file owns the
   visible side of that: the notice, the two choices, remembering the choice in
   browser storage, and the Privacy Choices link in the footer that reopens the
   notice so a visitor can change their mind later.

   The choice is kept in localStorage (not a cookie), so nothing is stored for
   tracking purposes and the notice does not reappear on every page visit.
   ========================================================================== */

(function () {
  'use strict';

  var STORAGE_KEY = 'fnhgAnalyticsConsent';
  var GRANTED = 'granted';
  var DENIED = 'denied';

  function readChoice() {
    try {
      var value = window.localStorage.getItem(STORAGE_KEY);
      return value === GRANTED || value === DENIED ? value : null;
    } catch (e) {
      return null;
    }
  }

  function saveChoice(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch (e) { /* private mode: the choice applies to this page view only */ }
  }

  /* Tell Google Analytics about the choice. Denied is sent explicitly too, so
     the state is unambiguous rather than relying on the page default alone. */
  function applyChoice(value) {
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', { 'analytics_storage': value });
    }
  }

  /* Other scripts (assets/analytics.js) ask this before sending an event. */
  window.fnhgConsent = {
    state: function () { return readChoice(); },
    analyticsAllowed: function () { return readChoice() === GRANTED; },
    open: function () { showNotice(true); }
  };

  /* Reuse the footer's own Privacy Policy link rather than building a path.
     The site generator has already rewritten that href to the right depth for
     the page it sits on, so this works from any folder and also when a page is
     opened straight from disk. */
  function privacyPolicyHref() {
    var existing = document.querySelector(
      '.footer-legal-links a[href$="privacypolicy.html"], ' +
      '.footer-legal-links a[href$="privacy-policy.html"]');
    return existing ? existing.getAttribute('href') : '/legal/privacypolicy.html';
  }

  var notice = null;
  var lastFocus = null;

  function buildNotice() {
    var el = document.createElement('div');
    el.className = 'privacy-notice';
    el.id = 'privacynotice';
    el.setAttribute('role', 'region');
    el.setAttribute('aria-label', 'Privacy preference');

    var inner = document.createElement('div');
    inner.className = 'privacy-notice-inner';

    var text = document.createElement('p');
    text.className = 'privacy-notice-text';
    text.textContent = 'We use analytics to understand how visitors use this website and to improve the experience. We do not send your contact form answers to analytics.';

    var actions = document.createElement('div');
    actions.className = 'privacy-notice-actions';

    var accept = document.createElement('button');
    accept.type = 'button';
    accept.className = 'btn btn-primary privacy-notice-btn';
    accept.textContent = 'Accept Analytics';
    accept.addEventListener('click', function () { choose(GRANTED); });

    var decline = document.createElement('button');
    decline.type = 'button';
    decline.className = 'btn btn-secondary privacy-notice-btn';
    decline.textContent = 'Decline Analytics';
    decline.addEventListener('click', function () { choose(DENIED); });

    var policy = document.createElement('a');
    policy.className = 'privacy-notice-policy';
    policy.href = privacyPolicyHref();
    policy.textContent = 'Privacy Policy';

    actions.appendChild(accept);
    actions.appendChild(decline);
    actions.appendChild(policy);
    inner.appendChild(text);
    inner.appendChild(actions);
    el.appendChild(inner);
    document.body.appendChild(el);
    return el;
  }

  /* moveFocus is used when the visitor asked for the notice (Privacy Choices).
     The automatic first visit notice does not grab focus or move the page. */
  function showNotice(moveFocus) {
    if (!notice) notice = buildNotice();
    notice.classList.add('is-visible');
    var current = readChoice();
    var buttons = notice.querySelectorAll('.privacy-notice-btn');
    // Reflect the saved choice when the notice is reopened later
    buttons[0].setAttribute('aria-pressed', String(current === GRANTED));
    buttons[1].setAttribute('aria-pressed', String(current === DENIED));
    if (moveFocus) {
      lastFocus = document.activeElement;
      buttons[0].focus();
    }
  }

  function hideNotice() {
    if (!notice) return;
    notice.classList.remove('is-visible');
    if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus();
    lastFocus = null;
  }

  function choose(value) {
    saveChoice(value);
    applyChoice(value);
    hideNotice();
  }

  /* Footer Privacy Choices link: reopens the notice instead of navigating.
     Without JavaScript it still leads to the Cookie Notice, which explains
     the same choice in writing. */
  document.querySelectorAll('[data-privacy-choices]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      showNotice(true);
    });
  });

  /* First visit, or storage cleared: ask. A saved choice stays applied and
     the notice stays out of the way. */
  if (!readChoice()) showNotice(false);

})();
