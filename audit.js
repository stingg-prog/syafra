const { chromium } = require('playwright');

(async () => {
  const viewports = [1920, 1680, 1536, 1440, 1280, 1024, 768, 375];

  for (const width of viewports) {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
      viewport: { width, height: 900 },
    });
    const page = await context.newPage();
    await page.goto('http://localhost:8000/', { waitUntil: 'networkidle', timeout: 15000 });

    const results = await page.evaluate(() => {
      const cw = document.documentElement.clientWidth;
      const sw = document.documentElement.scrollWidth;
      const overflowEls = [];

      const all = document.querySelectorAll('*');
      for (const el of all) {
        const style = window.getComputedStyle(el);
        // Skip position:fixed elements and their children
        if (style.position === 'fixed') continue;
        // Check if any ancestor is position:fixed
        let parent = el.parentElement;
        let isInFixed = false;
        while (parent) {
          const pStyle = window.getComputedStyle(parent);
          if (pStyle.position === 'fixed') { isInFixed = true; break; }
          parent = parent.parentElement;
        }
        if (isInFixed) continue;

        const rect = el.getBoundingClientRect();
        if (rect.right > cw + 0.5 || rect.left < -0.5) {
          const tag = el.tagName.toLowerCase();
          const cls = el.className && typeof el.className === 'string'
            ? el.className.slice(0, 120) : '';
          overflowEls.push({
            tag,
            class: cls,
            left: Math.round(rect.left * 100) / 100,
            right: Math.round(rect.right * 100) / 100,
            width: Math.round(rect.width * 100) / 100,
          });
        }
      }

      return { clientWidth: cw, scrollWidth: sw, diff: sw - cw, overflowCount: overflowEls.length, elements: overflowEls };
    });

    const status = results.diff === 0 ? 'PASS' : 'FAIL';
    console.log(`${status} | ${width}px | clientWidth=${results.clientWidth} scrollWidth=${results.scrollWidth} diff=${results.diff} overflowEls=${results.overflowCount}`);

    if (results.elements.length > 0 && results.diff > 0) {
      for (const el of results.elements) {
        console.log(`  >> TAG:${el.tag} CLS:${el.class} L:${el.left} R:${el.right} W:${el.width}`);
      }
    }

    await browser.close();
  }
})();
