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

// ---- Route Calculator ----
function initCalc() {
  const widget = document.getElementById('calcWidget');
  if (!widget) return;

  const RESULTS = {
    // [type][school][danger]
    physical: {
      first: {
        danger:  { icon:'🔴', title:'Экстренный уровень', sub:'Немедленно вызовите полицию (102) и скорую (103). После — подайте документы в школу.', docs:['📝 Документ 1: Заявление директору','🚔 Заявление в полицию','📋 Чек-лист доказательств'] },
        safe:    { icon:'🟡', title:'Серьёзный уровень',  sub:'Параллельный трек: школа + полиция. Возраст обидчика важен для выбора правового пути.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа','🚔 Заявление в полицию'] },
      },
      verbal: {
        danger:  { icon:'🔴', title:'Экстренный уровень', sub:'Если ситуация повторяется и есть угрозы — срочно в полицию. Школа уже предупреждена устно.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа','🚔 Заявление в полицию'] },
        safe:    { icon:'🟡', title:'Серьёзный уровень',  sub:'Устная жалоба не помогла — переходите к письменной. Это создаёт юридическую ответственность школы.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование письменного ответа'] },
      },
      written: {
        danger:  { icon:'🔴', title:'Экстренный уровень', sub:'Школа проигнорировала — жалуйтесь в акимат и параллельно в полицию.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат','🚔 Заявление в полицию'] },
        safe:    { icon:'🟡', title:'Эскалация в акимат', sub:'Школа не ответила на письменное заявление — следующий шаг: отдел образования акимата.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат'] },
      },
    },
    cyber: {
      first:   { danger: { icon:'🟡', title:'Кибербуллинг — серьёзный уровень', sub:'По Правилам № 506 кибербуллинг — ответственность школы, даже если произошёл вне школы.', docs:['📝 Документ 1: Заявление директору','📸 Памятка по фиксации кибербуллинга'] }, safe: { icon:'🟢', title:'Школьный трек', sub:'Зафиксируйте доказательства и подайте заявление директору. Бот поможет с обоими документами.', docs:['📝 Документ 1: Заявление директору','📸 Памятка по фиксации кибербуллинга'] } },
      verbal:  { danger: { icon:'🟡', title:'Кибербуллинг продолжается', sub:'Устная жалоба не помогла — нужен письменный документ. Школа обязана ответить официально.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа','📸 Памятка по фиксации'] }, safe: { icon:'🟢', title:'Письменное заявление', sub:'Самое время подать официальное заявление — это меняет ответственность школы.', docs:['📝 Документ 1: Заявление директору','📸 Памятка по фиксации кибербуллинга'] } },
      written: { danger: { icon:'🟡', title:'Эскалация', sub:'Школа проигнорировала — переходите к акимату.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат'] }, safe: { icon:'🟢', title:'Эскалация в акимат', sub:'Следующий шаг после молчания школы — отдел образования.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат'] } },
    },
    psycho: {
      first:   { danger: { icon:'🟡', title:'Психологическое давление', sub:'Изоляция и систематические унижения — это буллинг по Правилам № 506. Школа обязана реагировать.', docs:['📝 Документ 1: Заявление директору','📸 Памятка по фиксации'] }, safe: { icon:'🟢', title:'Школьный трек', sub:'Начните с официального заявления директору. Это запустит обязательную процедуру по № 506.', docs:['📝 Документ 1: Заявление директору'] } },
      verbal:  { danger: { icon:'🟡', title:'Нужен письменный документ', sub:'Устная жалоба не работает при систематическом давлении. Письменное заявление — другой уровень.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа'] }, safe: { icon:'🟢', title:'Письменное заявление', sub:'Переходите к официальному формату — это обязывает школу дать письменный ответ.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа'] } },
      written: { danger: { icon:'🟡', title:'Эскалация в акимат', sub:'Если школа не ответила — следующий уровень: отдел образования акимата.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат'] }, safe: { icon:'🟢', title:'Жалоба в акимат', sub:'Школа проигнорировала — подаём в вышестоящий орган.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат'] } },
    },
    extortion: {
      first:   { danger: { icon:'🔴', title:'Вымогательство — экстренный уровень', sub:'Вымогательство — уголовное дело. Параллельно: школа и полиция (102).', docs:['📝 Документ 1: Заявление директору','🚔 Заявление в полицию','📋 Чек-лист доказательств'] }, safe: { icon:'🟡', title:'Серьёзный уровень', sub:'Вымогательство требует параллельного обращения: школа + полиция.', docs:['📝 Документ 1: Заявление директору','🚔 Заявление в полицию'] } },
      verbal:  { danger: { icon:'🔴', title:'Экстренный уровень', sub:'Устной жалобы недостаточно. Немедленно письменное заявление в школу и в полицию.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа','🚔 Заявление в полицию'] }, safe: { icon:'🟡', title:'Серьёзный уровень', sub:'Вымогательство не прекращается — нужен официальный трек.', docs:['📝 Документ 1: Заявление директору','📬 Документ 2: Требование ответа','🚔 Заявление в полицию'] } },
      written: { danger: { icon:'🔴', title:'Экстренный + акимат', sub:'Школа не реагирует на вымогательство — акимат и прокуратура.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат','🚔 Заявление в полицию'] }, safe: { icon:'🟡', title:'Эскалация', sub:'Школа проигнорировала — жалуйтесь в акимат.', docs:['📬 Документ 2: Требование ответа','🏛️ Документ 4: Жалоба в акимат'] } },
    },
  };

  let answers = {};

  function showStep(stepId) {
    ['calcStep1','calcStep2','calcStep3','calcResult'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.hidden = (id !== stepId);
    });
  }

  function showResult() {
    const type   = answers[1];
    const school = answers[2];
    const danger = answers[3];

    const r = (RESULTS[type]?.[school]?.[danger]) || RESULTS[type]?.[school]?.safe || { icon:'📋', title:'Маршрут определён', sub:'Бот поможет с нужными документами.', docs:['📝 Документ 1: Заявление директору'] };

    document.getElementById('calcIcon').textContent = r.icon;
    document.getElementById('calcTitle').textContent = r.title;
    document.getElementById('calcSub').textContent = r.sub;

    const docsEl = document.getElementById('calcDocs');
    docsEl.innerHTML = r.docs.map(d => {
      const parts = d.split(' ');
      const emoji = parts[0];
      const text  = parts.slice(1).join(' ');
      return `<div class="calc__doc-item"><span>${emoji}</span>${text}</div>`;
    }).join('');

    showStep('calcResult');
    trackEvent('calc-result', { type, school, danger, title: r.title });
  }

  widget.addEventListener('click', e => {
    const opt = e.target.closest('.calc__opt');
    if (opt) {
      const step = parseInt(opt.dataset.step);
      const val  = opt.dataset.val;
      answers[step] = val;
      if (step === 1) showStep('calcStep2');
      else if (step === 2) showStep('calcStep3');
      else if (step === 3) showResult();
    }
    if (e.target.id === 'calcRestart') {
      answers = {};
      showStep('calcStep1');
    }
  });
}

// ---- Init all ----
document.addEventListener('DOMContentLoaded', () => {
  initFaq();
  initCalc();
  initStickyCta();
  initSmoothScroll();
  initNavShadow();
  initAnalytics();
});
