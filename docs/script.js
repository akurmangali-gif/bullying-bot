/* =====================================================
   БУЛЛИНГ СТОП КЗ — script.js
   ===================================================== */

'use strict';

// ---- FAQ Accordion ----
function initFaq() {
  const items = document.querySelectorAll('.faq-item');
  if (!items.length) return;

  items.forEach(item => {
    const btn = item.querySelector('.faq-item__q');
    const answer = item.querySelector('.faq-item__a');
    if (!btn || !answer) return;

    btn.setAttribute('aria-expanded', 'false');

    btn.addEventListener('click', () => {
      const isOpen = item.classList.contains('is-open');

      // Close all
      items.forEach(i => {
        i.classList.remove('is-open');
        const a = i.querySelector('.faq-item__a');
        const b = i.querySelector('.faq-item__q');
        if (a) a.style.maxHeight = null;
        if (b) b.setAttribute('aria-expanded', 'false');
      });

      // Open clicked (if was closed)
      if (!isOpen) {
        item.classList.add('is-open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
        btn.setAttribute('aria-expanded', 'true');

        // analytics
        const q = btn.textContent.trim().substring(0, 60);
        trackEvent('faq-open', { question: q });
      }
    });
  });
}

// ---- Sticky Mobile CTA ----
function initStickyCta() {
  const sticky = document.querySelector('.sticky-cta');
  if (!sticky) return;

  const heroCta = document.querySelector('.hero__actions');
  const finalCta = document.querySelector('.final-cta');

  function check() {
    if (window.innerWidth > 640) {
      sticky.style.display = 'none';
      return;
    }
    const heroRect = heroCta ? heroCta.getBoundingClientRect() : null;
    const finalRect = finalCta ? finalCta.getBoundingClientRect() : null;
    const heroVisible = heroRect && heroRect.bottom > 0;
    const finalVisible = finalRect && finalRect.top < window.innerHeight;

    if (!heroVisible && !finalVisible) {
      sticky.style.display = 'block';
    } else {
      sticky.style.display = 'none';
    }
  }

  window.addEventListener('scroll', check, { passive: true });
  window.addEventListener('resize', check, { passive: true });
  check();
}

// ---- Smooth Scroll for anchor links ----
function initSmoothScroll() {
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) return;

  document.addEventListener('click', e => {
    const anchor = e.target.closest('a[href^="#"]');
    if (!anchor) return;
    const id = anchor.getAttribute('href').slice(1);
    const target = id ? document.getElementById(id) : null;
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

// ---- Nav scroll shadow ----
function initNavShadow() {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 10
      ? '0 1px 12px rgba(0,0,0,.1)'
      : 'none';
  }, { passive: true });
}

// ---- Analytics stub (replace with real analytics later) ----
function trackEvent(event, data) {
  // Replace with: gtag('event', event, data) or similar
  if (typeof window.analytics === 'undefined') return;
  try { window.analytics.track(event, data); } catch(_) {}
}

// ---- data-analytics click tracking ----
function initAnalytics() {
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-analytics]');
    if (!el) return;
    const name = el.dataset.analytics;
    trackEvent('click', { element: name });
  });
}

// ---- Init all ----
document.addEventListener('DOMContentLoaded', () => {
  initFaq();
  initStickyCta();
  initSmoothScroll();
  initNavShadow();
  initAnalytics();
});
