/* ==========================================================================
   FN Home Group — Google Analytics 4 event tracking
   Loaded on every page by build/templates/base.html, immediately after the
   base Google tag (gtag.js).

   PRIVACY RULES (deliberate, please keep):
   Only five things are ever sent with an event, and every one of them comes
   from the site's own markup or the browser address bar -- never from anything
   a visitor typed:
     - the event name
     - page_path    : location.pathname only (query string and hash dropped, so
                      nothing a visitor typed or was linked with can leak)
     - link_text    : the static button/link label authored in the HTML
     - link_url     : the destination the markup points to
     - resource_name: the name of the resource being opened, when relevant
   Phone and email clicks are a special case: the label and the destination are
   themselves the contact detail, so those two events send the page path only.
   Form fields are never read. Names, email addresses, phone numbers, message
   contents, and every other form response stay out of Google Analytics
   entirely -- form submissions send only the event name, the page path, and
   the submit button's own static label.

   Events are also held back until the visitor accepts analytics in the
   privacy notice (see assets/consent.js), on top of the Google Consent Mode
   default that keeps analytics storage denied until then.

   Nothing here reconfigures or suppresses the base tag, so GA4 enhanced
   measurement (page views, scrolls, outbound clicks, file downloads, form
   interactions) keeps working exactly as it does by default. These named
   events sit alongside it.
   ========================================================================== */

(function () {
  'use strict';

  var MAX_LEN = 100;

  /* Events that must never carry a label or destination, because on this site
     the label and the destination ARE the contact detail (a phone number or an
     email address). They report the page they happened on and nothing else. */
  var CONTACT_EVENTS = { phone_click: true, email_click: true };

  /* Last-resort guard: strip anything shaped like an email address or a phone
     number out of any value before it leaves the page, so no future edit to a
     button label can quietly start sending contact details to Analytics. */
  function scrub(text) {
    return text
      .replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, '')
      .replace(/\+?\d[\d().\s-]{6,}\d/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /* Static site copy, trimmed to a single tidy line. */
  function labelOf(el) {
    var text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!text) text = (el.getAttribute('aria-label') || '').trim();
    return text.slice(0, MAX_LEN);
  }

  /* The external scheduling host. Calendly accepts prefill parameters in the
     query string (for example a visitor's name or email address), so the query
     is always dropped from what gets reported for these links: only the static
     scheduling address authored in the HTML is ever sent, and no booking
     details of any kind are read. */
  var SCHEDULING_HOST = /(^|\.)calendly\.com$/;

  /* Internal destinations report path (+ in-page anchor); external ones report
     the full authored URL. Both come from the markup, not from the visitor. */
  function destinationOf(a) {
    if (a.hostname && a.hostname !== window.location.hostname) {
      var query = SCHEDULING_HOST.test((a.hostname || '').toLowerCase()) ? '' : a.search;
      return (a.protocol + '//' + a.hostname + a.pathname + query).slice(0, MAX_LEN);
    }
    return (a.pathname + a.hash).slice(0, MAX_LEN);
  }

  function send(name, params) {
    if (typeof window.gtag !== 'function') return false;
    /* Consent gate. Google Consent Mode already keeps analytics storage denied
       until the visitor accepts; holding events back as well means declining
       analytics stops these named events at the source, not just their
       storage. Until a choice is made, nothing is sent. */
    if (!window.fnhgConsent || !window.fnhgConsent.analyticsAllowed()) return false;
    var payload = { page_path: window.location.pathname };
    if (params) {
      Object.keys(params).forEach(function (key) {
        if (params[key]) payload[key] = params[key];
      });
    }
    window.gtag('event', name, payload);
    return true;
  }

  /* ---------------- Link / button click classification ----------------
     One click produces at most one event: the first rule that matches wins,
     so a CTA that is both a consultation button and a link to the Contact
     page is only ever counted once (as the consultation click it is).
  ------------------------------------------------------------- */
  function classify(a, label) {
    var href = a.getAttribute('href') || '';
    var host = (a.hostname || '').toLowerCase();
    var path = (a.pathname || '').toLowerCase();
    var hash = (a.hash || '').toLowerCase();
    /* An in-page jump (the skip link, "#listingconsultation", etc.) shares the
       current page's path, so destination-path rules must not treat it as a
       visit to that page -- only its own label and anchor describe it. */
    var goesElsewhere = path !== (window.location.pathname || '').toLowerCase();

    if (/^tel:/i.test(href)) return { name: 'phone_click' };
    if (/^mailto:/i.test(href)) return { name: 'email_click' };

    /* The Human Behind the House™ referral links (external, ?ref=faith) */
    if (/(^|\.)thehumanbehindthehouse\.com$/.test(host)) {
      return {
        name: 'thbth_referral_click',
        params: { resource_name: 'The Human Behind the House' }
      };
    }

    /* GM and Manufacturing Families resources: the partner financing resource
       and the GM Families resource page itself. */
    if (/(^|\.)my\.canva\.site$/.test(host) ||
        (goesElsewhere && /^\/gmfamilies(\.html)?$/.test(path))) {
      return {
        name: 'gm_resource_click',
        params: { resource_name: label || 'GM and Manufacturing Families' }
      };
    }

    if (/buyer\s*guide/i.test(label)) return { name: 'buyer_guide_request' };
    if (/seller\s*guide/i.test(label) ||
        (goesElsewhere && /seller-?\s*options-?\s*guide/i.test(path))) {
      return { name: 'seller_guide_request' };
    }

    /* Every scheduling button on the site points at Calendly, whichever event
       it books (general, buyer, listing, and so on). Matching the host as well
       as the label keeps a single consultation_click per click even if a
       button's label never says "consultation". Still one event: the first
       rule that matches wins, and there is only ever one click listener. */
    if (SCHEDULING_HOST.test(host) ||
        /consultation/i.test(label) || /consultation/i.test(hash)) {
      return { name: 'consultation_click' };
    }
    if (/search/i.test(label)) return { name: 'home_search_click' };
    if (/home\s*value|home\s*is\s*worth/i.test(label) ||
        (goesElsewhere && /^\/home-?value(\.html)?$/.test(path))) {
      return { name: 'home_value_click' };
    }
    if (/contact/i.test(label) ||
        (goesElsewhere && /^\/contact(\.html)?$/.test(path))) {
      return { name: 'contact_click' };
    }
    return null;
  }

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var label = labelOf(a);
    var match = classify(a, label);
    if (!match) return;
    var params = match.params || {};
    if (!CONTACT_EVENTS[match.name]) {
      params.link_text = scrub(label);
      params.link_url = scrub(destinationOf(a));
    }
    send(match.name, params);
  }, true);

  /* ---------------- Form submissions ----------------
     Runs on the bubbling phase, after the validation handler in script.js has
     had its say, and skips anything that handler blocked -- so an event is
     only recorded for a submission that actually goes through, once per form.
     No field values are read.
  ------------------------------------------------------------- */
  var FORM_EVENTS = {
    'contact': 'generate_lead',
    'buyer-guide-request': 'buyer_guide_request'
  };

  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (e.defaultPrevented || !form || form.tagName !== 'FORM') return;
    var eventName = FORM_EVENTS[form.getAttribute('name')];
    if (!eventName || form.hasAttribute('data-ga-sent')) return;
    var button = form.querySelector('button[type="submit"], input[type="submit"]');
    // Only mark the form as counted if the event actually went out
    if (send(eventName, { link_text: button ? scrub(labelOf(button)) : '' })) {
      form.setAttribute('data-ga-sent', 'true');
    }
  }, false);

})();
