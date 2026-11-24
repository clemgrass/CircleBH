// Mediciones del prototipo de mejoras (`mejoras_armas.html`), sin navegador.
//
// Prototipo desechable, como la página: no se mantiene ni se testea. Lo que midió está en
// `docs/investigaciones/2026-11-24-mejoras.md`.
//
// Uso, desde la raíz del repo (con Node):
//
//     awk '/<script>/{f=1;next}/<\/script>/{f=0}f' docs/prototipos/mejoras_armas.html > /tmp/proto.js
//     node docs/prototipos/medir_mejoras.js /tmp/proto.js dano
//     node docs/prototipos/medir_mejoras.js /tmp/proto.js variedad [partidas] [tarjetas]
//
// `dano`: 20 s de cada arma sola y con cada tarjeta; líneas por segundo y destruidos.
// `variedad`: partidas con tarjetas elegidas al azar; cuántas formas finales distintas salen.
const fs = require("fs");
const src = fs.readFileSync(process.argv[2], "utf8");
const mode = process.argv[3] || "variedad";

// Un DOM falso: lo justo para que el script de la página corra y se pueda hacer clic.
function el(tag) {
  return {
    tag, children: [], listeners: {}, attrs: {}, textContent: "", className: "", hidden: false,
    disabled: false, clientWidth: 400, width: 0, height: 0,
    set innerHTML(v) { this.children = []; }, get innerHTML() { return ""; },
    appendChild(c) { this.children.push(c); return c; },
    addEventListener(t, f) { this.listeners[t] = f; },
    setAttribute(k, v) { this.attrs[k] = v; },
    querySelector() { return el("span"); },
    click() { this.listeners.click && this.listeners.click(); },
    getContext() { return new Proxy({}, { get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true; } }); },
  };
}
const ids = {};
global.document = { getElementById: (id) => (ids[id] ??= el("div")), createElement: el, documentElement: {} };
global.window = { devicePixelRatio: 1 };
global.getComputedStyle = () => ({ getPropertyValue: () => "#fff" });
let rafCb = () => {};
global.requestAnimationFrame = (f) => { rafCb = f; };
global.performance = { now: () => 0 };
// El script es el de nuestro propio prototipo, leído de un archivo local: no hay entrada externa.
eval(src);

const names = ["Punto", "Recta", "Seno", "Círculo", "Espiral", "Rosa"];
const tab = (i) => ids.tabs.children[i];
const hand = () => ids.hand.children;

if (mode === "dano") {
  let now = 0;
  const run = (s) => { for (let i = 0; i < s * 30; i++) { now += 1000 / 30; rafCb(now); } };
  names.forEach((name, ti) => {
    tab(ti).click();
    run(20);
    console.log(`${name.padEnd(8)} sin tarjeta: ${ids.sNow.textContent}`);
    const n = hand().length;
    for (let ci = 0; ci < n; ci++) {
      tab(ti).click();
      hand()[ci].click();
      run(20);
      console.log(`   ${ids.nextName.textContent.padEnd(26)} ${ids.sNext.textContent}`);
    }
  });
} else {
  const RUNS = Number(process.argv[4] || 2000);
  const PICKS = Number(process.argv[5] || 8);
  // Azar con semilla (mulberry32), para que la medición se repita igual.
  let seed = 1;
  const rand = () => { seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  // La clase de forma: la estructura de la fórmula (términos, grado del avance y operadores)
  // y los k de los armónicos. Lo que solo escala (v, A, cooldown, tamaño) no cuenta.
  const shapeClass = () => {
    const ks = [...ids.params.textContent.matchAll(/\bk(₂?) = ([\d,]+)/g)].map((m) => m[2]).join(",");
    return `${ids.formula.textContent}|k=${ks}`;
  };
  names.forEach((name, ti) => {
    tab(ti).click();
    const counts = new Map();
    for (let r = 0; r < RUNS; r++) {
      ids.reset.click();
      for (let i = 0; i < PICKS && hand().length; i++) {
        hand()[Math.floor(rand() * hand().length)].click();
        ids.take.click();
      }
      const c = shapeClass();
      counts.set(c, (counts.get(c) || 0) + 1);
    }
    const top = Math.max(...counts.values());
    // Entropía de Shannon: 2^H es la cantidad de formas "efectivas", pesadas por frecuencia.
    let H = 0;
    for (const n of counts.values()) { const q = n / RUNS; H -= q * Math.log2(q); }
    console.log(`${name.padEnd(8)} formas distintas: ${String(counts.size).padStart(4)} · la más común: ${(100 * top / RUNS).toFixed(1).padStart(5)} % · efectivas 2^H: ${Math.pow(2, H).toFixed(0)}`);
  });
}
