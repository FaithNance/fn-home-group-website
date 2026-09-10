/* ==========================================================================
   FN Home Group — Global Site Script
   Handles: mobile nav, form validation/success states, active nav highlighting,
   FAQ helpers, and site-config data injection.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

  /* ---------------- Mobile nav toggle ---------------- */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.main-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      nav.classList.toggle('is-open');
      // Collapse any expanded nav dropdown group with the menu itself
      if (expanded && typeof closeDropdowns === 'function') closeDropdowns(null);
    });
    // Close menu when a link is clicked (mobile)
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
        if (typeof closeDropdowns === 'function') closeDropdowns(null);
      });
    });
  }

  /* ---------------- Resources nav dropdown ----------------
     The dropdown's parent item stays a real link (Resource Hub); the caret
     button next to it opens the grouped resource pages. CSS also opens the
     menu on hover/keyboard focus at desktop widths, so this handler only
     owns the click/touch state -- which is what mobile depends on, since
     the stacked menu has no hover.
  ------------------------------------------------------------- */
  var dropdowns = Array.prototype.slice.call(document.querySelectorAll('[data-nav-dropdown]'));
  function closeDropdowns(except, dismissed) {
    dropdowns.forEach(function (dd) {
      if (dd === except) return;
      dd.classList.remove('is-open');
      dd.classList.toggle('is-closed', !!dismissed);
      var btn = dd.querySelector('[data-nav-dropdown-toggle]');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  }
  dropdowns.forEach(function (dd) {
    var btn = dd.querySelector('[data-nav-dropdown-toggle]');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var open = dd.classList.contains('is-open');
      closeDropdowns(dd);
      dd.classList.toggle('is-open', !open);
      // Dismissing keeps the menu shut even though the caret still holds
      // focus (and the pointer); moving away clears that state below.
      dd.classList.toggle('is-closed', open);
      btn.setAttribute('aria-expanded', String(!open));
    });
    dd.addEventListener('mouseleave', function () { dd.classList.remove('is-closed'); });
    dd.addEventListener('focusout', function (e) {
      if (!dd.contains(e.relatedTarget)) dd.classList.remove('is-closed');
    });
  });
  if (dropdowns.length) {
    document.addEventListener('click', function (e) {
      var inside = dropdowns.some(function (dd) { return dd.contains(e.target); });
      if (!inside) closeDropdowns(null);
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      var openDd = dropdowns.filter(function (dd) { return dd.classList.contains('is-open'); })[0];
      if (!openDd) return;
      closeDropdowns(null, true);
      var btn = openDd.querySelector('[data-nav-dropdown-toggle]');
      if (btn) btn.focus();
    });
  }

  /* ---------------- Highlight current nav link ----------------
     Scoped to direct nav links only (.main-nav > a) so the "Schedule a
     Consultation" CTA button -- which lives in .nav-cta nested inside
     .main-nav and also points to /contact.html -- never gets treated as
     a "current page" nav link. (That previously made its text invisible
     on the Contact page, since the aria-current color rule matched the
     button's own background color.)
     The Resources item now lives in a dropdown wrapper, so its own link and
     the grouped resource links are matched explicitly as well.
  ------------------------------------------------------------- */
  var currentPath = window.location.pathname.replace(/\/index\.html$/, '/').replace(/index\.html$/, '');
  document.querySelectorAll('.main-nav > a, .nav-dropdown > a, .nav-dropdown-menu a, .footer-nav a').forEach(function (link) {
    var href = link.getAttribute('href');
    if (!href) return;
    var linkPath = href.replace(/\/index\.html$/, '/').replace(/index\.html$/, '');
    if (linkPath && (currentPath === linkPath || currentPath.endsWith(linkPath))) {
      link.setAttribute('aria-current', 'page');
    }
  });

  /* ---------------- Front-end form handling ----------------
     Forms are built to POST to Netlify Forms (data-netlify="true").
     This script adds lightweight required-field validation and a
     friendly inline success/error state for a smoother experience,
     while still allowing a normal Netlify form submission/redirect.
  ------------------------------------------------------------- */
  document.querySelectorAll('form[data-site-form]').forEach(function (form) {
    // The success/error message boxes are siblings of the form (inside the
    // same .form-card wrapper), not children of it, so look there instead.
    var container = form.closest('.form-card') || form.parentElement;
    var successBox = container ? container.querySelector('.form-success') : null;
    var errorBox = container ? container.querySelector('.form-error') : null;

    form.addEventListener('submit', function (e) {
      var valid = true;
      var firstInvalid = null;

      form.querySelectorAll('[required]').forEach(function (field) {
        var wrapper = field.closest('.field') || field.closest('.checkbox-field');
        var fieldOk = true;

        if (field.type === 'checkbox') {
          fieldOk = field.checked;
        } else {
          fieldOk = field.value && field.value.trim() !== '';
        }

        if (field.type === 'email' && field.value) {
          var emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!emailPattern.test(field.value)) fieldOk = false;
        }

        if (!fieldOk) {
          valid = false;
          if (wrapper) wrapper.classList.add('has-error');
          if (!firstInvalid) firstInvalid = field;
        } else if (wrapper) {
          wrapper.classList.remove('has-error');
        }
      });

      // Honeypot spam trap (Netlify-compatible bot-field)
      var honeypot = form.querySelector('input[name="bot-field"]');
      if (honeypot && honeypot.value) {
        valid = false;
      }

      if (!valid) {
        e.preventDefault();
        if (errorBox) errorBox.classList.add('is-visible');
        if (successBox) successBox.classList.remove('is-visible');
        if (firstInvalid) firstInvalid.focus();
        return;
      }

      if (errorBox) errorBox.classList.remove('is-visible');
      // Allow the natural Netlify form submission (redirect to /success.html)
      // to proceed. No preventDefault() here.
    });
  });

  /* ---------------- Set current year in footer ---------------- */
  document.querySelectorAll('[data-current-year]').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  /* ---------------- Community image carousel (Southern Middle Tennessee) ----------------
     Fade-transition carousel used in the "Proudly Serving Southern Middle
     Tennessee" section on the homepage. Autoplays, pauses on hover/focus,
     supports keyboard arrows, swipe on touch devices, and respects
     prefers-reduced-motion (autoplay and swipe still work when reduced
     motion is set -- only the CSS opacity transition duration changes,
     handled in styles.css).
  ------------------------------------------------------------- */
  document.querySelectorAll('[data-carousel]').forEach(function (root) {
    var slides = Array.prototype.slice.call(root.querySelectorAll('[data-slide]'));
    if (!slides.length) return;

    var track = root.querySelector('.community-carousel-track');
    var prevBtn = root.querySelector('[data-carousel-prev]');
    var nextBtn = root.querySelector('[data-carousel-next]');
    var dotsWrap = root.querySelector('[data-carousel-dots]');
    var current = 0;
    var autoplayMs = 4000;
    var timer = null;
    var reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Build pagination dots
    var dots = slides.map(function (slide, i) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'community-carousel-dot' + (i === 0 ? ' is-active' : '');
      var name = slide.querySelector('figcaption');
      btn.setAttribute('aria-label', 'Show ' + (name ? name.textContent : 'slide ' + (i + 1)));
      if (i === 0) btn.setAttribute('aria-current', 'true');
      btn.addEventListener('click', function () {
        goTo(i);
        restartAutoplay();
      });
      dotsWrap.appendChild(btn);
      return btn;
    });

    // Screen readers should only "see" the active slide's caption/alt text
    slides.forEach(function (slide, i) {
      slide.setAttribute('aria-hidden', i === 0 ? 'false' : 'true');
      var img = slide.querySelector('img');
      // Preload the second slide immediately (the first likely-next slide);
      // the rest stay lazy as authored.
      if (i === 1 && img) img.loading = 'eager';
    });

    function goTo(index) {
      var next = (index + slides.length) % slides.length;
      if (next === current) return;
      slides[current].setAttribute('aria-hidden', 'true');
      dots[current].classList.remove('is-active');
      dots[current].removeAttribute('aria-current');

      slides[next].setAttribute('aria-hidden', 'false');
      dots[next].classList.add('is-active');
      dots[next].setAttribute('aria-current', 'true');

      // Slide the track itself right-to-left (or back) so photos physically
      // move past each other rather than crossfading in place.
      track.style.transform = 'translateX(-' + (next * 100) + '%)';

      // Preload the slide after the upcoming one so it's ready before its turn
      var upcoming = slides[(next + 1) % slides.length].querySelector('img');
      if (upcoming) upcoming.loading = 'eager';

      current = next;
    }

    function nextSlide() { goTo(current + 1); }
    function prevSlide() { goTo(current - 1); }

    function startAutoplay() {
      if (reducedMotion) return; // respect reduced-motion: no forced motion
      stopAutoplay();
      timer = window.setInterval(nextSlide, autoplayMs);
    }
    function stopAutoplay() {
      if (timer) { window.clearInterval(timer); timer = null; }
    }
    function restartAutoplay() { startAutoplay(); }

    if (nextBtn) nextBtn.addEventListener('click', function () { nextSlide(); restartAutoplay(); });
    if (prevBtn) prevBtn.addEventListener('click', function () { prevSlide(); restartAutoplay(); });

    // Pause on hover and on keyboard focus within the carousel
    root.addEventListener('mouseenter', stopAutoplay);
    root.addEventListener('mouseleave', startAutoplay);
    root.addEventListener('focusin', stopAutoplay);
    root.addEventListener('focusout', startAutoplay);

    // Keyboard navigation (left/right arrows) when the carousel has focus
    root.setAttribute('tabindex', '0');
    root.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { nextSlide(); restartAutoplay(); e.preventDefault(); }
      else if (e.key === 'ArrowLeft') { prevSlide(); restartAutoplay(); e.preventDefault(); }
    });

    // Swipe support on touch devices
    var touchStartX = null;
    track.addEventListener('touchstart', function (e) {
      touchStartX = e.changedTouches[0].clientX;
      stopAutoplay();
    }, { passive: true });
    track.addEventListener('touchend', function (e) {
      if (touchStartX === null) return;
      var deltaX = e.changedTouches[0].clientX - touchStartX;
      if (Math.abs(deltaX) > 40) {
        if (deltaX < 0) nextSlide(); else prevSlide();
      }
      touchStartX = null;
      restartAutoplay();
    }, { passive: true });

    startAutoplay();
  });

});
