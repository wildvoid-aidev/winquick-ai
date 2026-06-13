// ── Mobile Menu Toggle ──
const toggle = document.getElementById('menuToggle');
const links = document.querySelector('.nav-links');
if (toggle && links) {
  toggle.addEventListener('click', () => {
    links.classList.toggle('open');
    toggle.classList.toggle('active');
  });
  document.querySelectorAll('.nav-links a').forEach(a => {
    a.addEventListener('click', () => links.classList.remove('open'));
  });
}

// ── Scroll Reveal Animations ──
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('revealed');
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.feature-card, .step, .download-card, .donate-card').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(24px)';
  el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
  observer.observe(el);
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.feature-card, .step, .download-card, .donate-card').forEach(el => {
    el.classList.add('revealed');
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
  });
});

// ── Parallax Glow Spheres ──
document.addEventListener('mousemove', e => {
  const x = (e.clientX / window.innerWidth - 0.5) * 30;
  const y = (e.clientY / window.innerHeight - 0.5) * 30;
  document.querySelectorAll('.glow-sphere').forEach((el, i) => {
    const factor = i === 0 ? 1 : -1;
    el.style.transform = `translate(${x * factor}px, ${y * factor}px)`;
  });
});
