(function () {
  const PREF_KEY = 'splineBgEnabled';
  const MODE_KEY = 'splineBgMode';
  const COLOR_KEY = 'splineBgColor';
  const INTENSITY_KEY = 'splineBgIntensity';
  const POINTS_KEY = 'splineBgPoints';

  const canvas = document.getElementById('spline-bg');
  const splineElement = document.getElementById('spline-viewer');
  const toggle = document.getElementById('bg-toggle');
  const settings = document.getElementById('bg-settings');
  const modeSelect = document.getElementById('bg-mode');
  const colorInput = document.getElementById('bg-color');
  const intensityInput = document.getElementById('bg-intensity');
  const pointsSelect = document.getElementById('bg-points');
  const resetBtn = document.getElementById('bg-reset');
  const closeBtn = document.getElementById('bg-close');

  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let w = 0, h = 0, DPR = window.devicePixelRatio || 1;
  let POINT_COUNT = parseInt(localStorage.getItem(POINTS_KEY) || '6', 10);
  const points = [];
  const mouse = { x: -9999, y: -9999 };
  let rafId = null;

  function prefersReduced() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  // Mode: 'spline', 'canvas', 'auto'
  let mode = localStorage.getItem(MODE_KEY) || 'auto';
  let enabled = (localStorage.getItem(PREF_KEY) !== null) ? (localStorage.getItem(PREF_KEY) === 'true') : !prefersReduced();

  // Color / intensity defaults
  const defaultColor = (() => {
    const root = getComputedStyle(document.documentElement);
    const css = root.getPropertyValue('--secondary-color') || '#009cbf';
    return css.trim();
  })();
  let color = localStorage.getItem(COLOR_KEY) || defaultColor;
  let intensity = parseFloat(localStorage.getItem(INTENSITY_KEY) || '1');

  function hexToRgb(hex) {
    if (!hex) return [0,150,200];
    hex = hex.trim();
    if (hex.startsWith('rgb')) {
      const parts = hex.replace(/[rgba() ]/g,'').split(',');
      return parts.slice(0,3).map(v => parseInt(v,10));
    }
    if (hex.startsWith('#')) hex = hex.slice(1);
    if (hex.length === 3) hex = hex.split('').map(c => c+c).join('');
    const num = parseInt(hex, 16);
    return [ (num >> 16) & 255, (num >> 8) & 255, num & 255 ];
  }

  function splineSupported() {
    return !!(window.customElements && window.customElements.get && window.customElements.get('spline-viewer'));
  }

  // Wait for the spline-viewer element to be defined and loaded
  function whenSplineReady(callback) {
    if (window.customElements && window.customElements.get && window.customElements.get('spline-viewer')) {
      callback();
    } else if (window.customElements && window.customElements.whenDefined) {
      window.customElements.whenDefined('spline-viewer').then(callback).catch(() => {});
    } else {
      // Graceful fallback: try after a small delay
      setTimeout(() => { if (document.getElementById('spline-viewer')) callback(); }, 1000);
    }
  }

  function resize() {
    DPR = window.devicePixelRatio || 1;
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = Math.floor(w * DPR);
    canvas.height = Math.floor(h * DPR);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    ctx.setTransform(DPR,0,0,DPR,0,0);

    points.length = 0;
    for (let i = 0; i < POINT_COUNT; i++) {
      points.push({ x: w * (i / (POINT_COUNT - 1)), y: h / 2, vx: 0, vy: 0 });
    }

    // make sure the spline viewer covers viewport (some browsers may need CSS reflow)
    if (splineElement) {
      splineElement.style.width = w + 'px';
      splineElement.style.height = h + 'px';
    }
  }

  function onPointer(e) {
    const p = e.touches ? e.touches[0] : e;
    mouse.x = p.clientX;
    mouse.y = p.clientY;
  }

  function applySettings() {
    // update inputs
    if (colorInput) colorInput.value = toHex(color);
    if (intensityInput) intensityInput.value = intensity;
    if (pointsSelect) pointsSelect.value = ''+POINT_COUNT;
    if (modeSelect) modeSelect.value = mode;
  }

  function toHex(c) {
    // ensure hex string
    if (!c) return '#009cbf';
    c = c.trim();
    if (c.startsWith('#')) return c;
    // try rgb
    if (c.startsWith('rgb')) {
      const parts = c.replace(/[rgba() ]/g,'').split(',').slice(0,3).map(v => parseInt(v,10));
      return '#'+parts.map(n => n.toString(16).padStart(2,'0')).join('');
    }
    return c;
  }

  function update() {
    if (POINT_COUNT <= 1) return;
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const influenceX = (mouse.x === -9999) ? 0 : (mouse.x - w / 2) * 0.05;
      const influenceY = (mouse.y === -9999) ? 0 : (mouse.y - h / 2) * 0.12;
      const mid = (POINT_COUNT - 1) / 2;
      const factor = 1 - Math.min(1, Math.abs(i - mid) / (POINT_COUNT));

      const tx = w * (i / (POINT_COUNT - 1)) + influenceX * factor;
      const ty = h / 2 + influenceY * ((i - mid) / (POINT_COUNT / 2));

      p.vx += (tx - p.x) * 0.06;
      p.vy += (ty - p.y) * 0.06;
      p.vx *= 0.86; p.vy *= 0.86;
      p.x += p.vx; p.y += p.vy;
    }
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = 'rgba(10,18,26,0.02)';
    ctx.fillRect(0, 0, w, h);

    const rgb = hexToRgb(color);

    for (let layer = 0; layer < 3; layer++) {
      ctx.beginPath();
      const offsetY = (layer - 1) * 8;
      ctx.moveTo(points[0].x, points[0].y + offsetY);
      for (let i = 1; i < points.length - 1; i++) {
        const p0 = points[i];
        const p1 = points[i + 1];
        const cx = (p0.x + p1.x) / 2;
        const cy = (p0.y + p1.y) / 2 + offsetY;
        ctx.quadraticCurveTo(p0.x, p0.y + offsetY, cx, cy);
      }
      ctx.lineWidth = 1.6 + layer * 1.2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      const baseAlpha = Math.max(0.03, 0.18 - layer * 0.05);
      const a = Math.min(1, Math.max(0, baseAlpha * intensity));
      ctx.strokeStyle = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;
      ctx.stroke();
    }

    if (mouse.x !== -9999) {
      ctx.beginPath();
      const r = 22 * Math.min(2, Math.max(0.6, intensity));
      const rgb = hexToRgb(color);
      const grd = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, r);
      grd.addColorStop(0, `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${0.08 * intensity})`);
      grd.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grd;
      ctx.fillRect(mouse.x - r, mouse.y - r, r * 2, r * 2);
    }
  }

  function loop() { update(); draw(); rafId = requestAnimationFrame(loop); }
  function startLoop() { if (rafId == null) { rafId = requestAnimationFrame(loop); } }
  function stopLoop() { if (rafId != null) { cancelAnimationFrame(rafId); rafId = null; } }

  function enable() {
    canvas.style.display = 'block';
    canvas.classList.remove('spline-disabled');
    startLoop();
    if (toggle) toggle.setAttribute('aria-pressed', 'true');
    localStorage.setItem(PREF_KEY, 'true');
  }
  function disable() {
    canvas.style.display = 'none';
    canvas.classList.add('spline-disabled');
    stopLoop();
    if (toggle) toggle.setAttribute('aria-pressed', 'false');
    localStorage.setItem(PREF_KEY, 'false');
  }

  function openSettings() {
    if (!settings) return;
    settings.setAttribute('aria-hidden', 'false');
    settings.style.display = 'block';
  }
  function closeSettings() {
    if (!settings) return;
    settings.setAttribute('aria-hidden', 'true');
    settings.style.display = 'none';
  }

  function resetSettings() {
    color = defaultColor;
    intensity = 1;
    POINT_COUNT = 6;
    localStorage.removeItem(COLOR_KEY);
    localStorage.removeItem(INTENSITY_KEY);
    localStorage.removeItem(POINTS_KEY);
    applySettings();
    resize();
  }

  function initUI() {
    if (!colorInput || !intensityInput || !pointsSelect) return;
    colorInput.value = toHex(color);
    intensityInput.value = intensity;
    pointsSelect.value = ''+POINT_COUNT;

    colorInput.addEventListener('input', (e) => {
      color = e.target.value;
      localStorage.setItem(COLOR_KEY, color);
    });
    intensityInput.addEventListener('input', (e) => {
      intensity = parseFloat(e.target.value);
      localStorage.setItem(INTENSITY_KEY, ''+intensity);
    });
    pointsSelect.addEventListener('change', (e) => {
      POINT_COUNT = parseInt(e.target.value, 10) || 6;
      localStorage.setItem(POINTS_KEY, ''+POINT_COUNT);
      resize();
    });
    resetBtn && resetBtn.addEventListener('click', () => { resetSettings(); });
    closeBtn && closeBtn.addEventListener('click', () => { closeSettings(); });

    // toggle opens settings when long-press or double click
    if (toggle) {
      toggle.addEventListener('dblclick', openSettings);
      toggle.addEventListener('contextmenu', (e) => { e.preventDefault(); openSettings(); });
      toggle.addEventListener('keydown', (e) => { if ((e.key === 'm' || e.key === 'M')) openSettings(); });
    }
  }

  function showSpline() {
    if (!splineElement) return;
    // Make sure the element is visible and mark it loaded
    splineElement.classList.remove('spline-disabled');
    splineElement.classList.remove('spline-error');
    splineElement.classList.add('spline-loaded');
    splineElement.style.display = 'block';
    canvas && (canvas.style.display = 'none');
    stopLoop(); // pause canvas loop
    // Show watermark block (in case the viewer shows a watermark)
    const block = document.getElementById('spline-watermark-block');
    if (block) block.classList.remove('hidden');
  }
  function hideSpline() {
    if (!splineElement) return;
    splineElement.classList.add('spline-disabled');
    splineElement.classList.remove('spline-loaded');
    splineElement.style.display = 'none';
    canvas && (canvas.style.display = 'block');
    enabled && startLoop(); // resume canvas if enabled
    // Hide watermark block when not using spline
    const block = document.getElementById('spline-watermark-block');
    if (block) block.classList.add('hidden');
  }

  function init() {
    window.addEventListener('pointermove', onPointer, { passive: true });
    window.addEventListener('touchmove', onPointer, { passive: true });
    window.addEventListener('pointerleave', () => { mouse.x = -9999; mouse.y = -9999; }, { passive: true });
    window.addEventListener('resize', resize);

    applySettings();
    initUI();
    resize();

    if (toggle) {
      toggle.addEventListener('click', (e) => {
        enabled = !enabled;
        enabled ? enable() : disable();
      });
      toggle.addEventListener('keydown', (e) => {
        if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); toggle.click(); }
      });
    }

    // Mode select handling
    if (modeSelect) {
      modeSelect.addEventListener('change', (e) => {
        mode = e.target.value;
        localStorage.setItem(MODE_KEY, mode);
        updateMode();
      });
    }

    function updateMode() {
      if (mode === 'spline') {
        whenSplineReady(() => showSpline());
      } else if (mode === 'canvas') {
        hideSpline();
      } else { // auto
        if (splineSupported()) {
          whenSplineReady(() => showSpline());
        } else {
          hideSpline();
        }
      }
    }

    // Respect reduced motion preference on init
    if (prefersReduced()) { enabled = false; }

    // Initialize spline element if present
    whenSplineReady(() => {
      if (!splineElement) return;
      // Wait until any internal assets are fetched; add a timeout fallback
      const readyTimeout = setTimeout(() => {
        // if it's still not painted, mark error class
        if (!splineElement.classList.contains('spline-loaded')) {
          splineElement.classList.add('spline-error');
          console.warn('Spline viewer did not become visible within timeout.');
        }
      }, 4000);

      // Try to detect when it has content: some implementations set a shadowRoot
      // or listen for `load` events on internal frames — we poll for children
      const poll = setInterval(() => {
        if (!splineElement) { clearInterval(poll); clearTimeout(readyTimeout); return; }
        // If the element has a non-zero clientHeight and is connected, consider it ready
        if (splineElement.clientHeight > 0 && splineElement.clientWidth > 0) {
          clearInterval(poll);
          clearTimeout(readyTimeout);
          splineElement.classList.add('spline-loaded');
          // Decide whether to show it based on mode
          updateMode();
        }
      }, 250);
    });

    // initial mode handling
    updateMode();

    if (enabled && mode !== 'spline') startLoop();
    else if (mode === 'spline' && enabled) { /* Spline will be shown by whenSplineReady */ }

  }

  // Delay init to DOMContentLoaded if needed
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();