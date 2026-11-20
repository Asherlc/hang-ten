(function () {
  const root = document.querySelector('[data-dc-artboard]');
  if (!root) return;

  const style = getComputedStyle(document.documentElement);
  for (const name of ['--dc-reveal-fill', '--dc-reveal-ink']) {
    const value = style.getPropertyValue(name).trim();
    if (value) root.style.setProperty(name, value);
  }

  const texts = [...root.querySelectorAll('.dc-text')].map(element => ({
    element,
    original: element.dataset.dcOriginal ?? ''
  }));
  const layers = new Map();
  for (const text of texts) {
    const layer = text.element.closest('.dc-layer[aria-label]');
    if (!layer || !text.original) continue;
    if (!layers.has(layer)) {
      layers.set(layer, { baseline: layer.getAttribute('aria-label'), tokens: new Map() });
    }
    const { tokens } = layers.get(layer);
    const key = text.original.toLowerCase();
    if (!tokens.has(key)) tokens.set(key, []);
    tokens.get(key).push(text);
  }

  for (const record of layers.values()) {
    // Match the longest original first so a step number cannot replace part
    // of the title or duration. Keep punctuation and other authored context.
    const alternatives = [...record.tokens.keys()]
      .sort((a, b) => b.length - a.length)
      .map(value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('|');
    record.pattern = new RegExp('(?<![\\p{L}\\p{N}])(?:' + alternatives + ')(?![\\p{L}\\p{N}])', 'giu');
  }

  function refresh() {
    for (const { element, original } of texts) {
      element.classList.toggle('dc-revealed', element.textContent !== original);
      element.setAttribute('aria-label', element.textContent);
    }
    for (const [layer, { baseline, tokens, pattern }] of layers) {
      const occurrences = new Map();
      const label = baseline.replace(pattern, match => {
        const key = match.toLowerCase();
        const index = occurrences.get(key) ?? 0;
        occurrences.set(key, index + 1);
        const text = tokens.get(key)?.[index];
        return text && text.element.textContent !== text.original ? text.element.textContent : match;
      });
      if (layer.getAttribute('aria-label') !== label) layer.setAttribute('aria-label', label);
    }
  }

  refresh();
  new MutationObserver(refresh).observe(root, {
    subtree: true, childList: true, characterData: true
  });
})();
