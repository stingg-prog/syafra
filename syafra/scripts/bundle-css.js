/**
 * CSS Bundle Script
 * Concatenates all modular CSS files into a single production stylesheet.
 *
 * Usage: node scripts/bundle-css.js
 * Output: static/css/bundle.css
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const OUTPUT = path.join(ROOT, 'static', 'css', 'bundle.css');

const CSS_FILES = [
    // Core layer
    'static/css/core/fonts.css',
    'static/css/core/variables.css',
    'static/css/core/base.css',
    'static/css/core/typography.css',
    'static/css/core/animations.css',
    'static/css/core/responsive.css',
    // Layout layer
    'static/css/layout/navbar.css',
    'static/css/layout/footer.css',
    // Section layer
    'static/css/sections/announcement.css',
    'static/css/sections/hero.css',
    'static/css/sections/trust-bar.css',
    'static/css/sections/categories.css',
    'static/css/sections/collections.css',
    'static/css/sections/banner.css',
    'static/css/sections/testimonials.css',
    'static/css/sections/instagram.css',
    'static/css/sections/newsletter.css',
    // Component layer
    'static/css/components/buttons.css',
    'static/css/components/cards.css',
    'static/css/components/product-card.css',
    'static/css/components/badges.css',
    'static/css/components/forms.css',
    // Page layer
    'static/css/pages/product-detail.css',
    'static/css/pages/cart.css',
    'static/css/pages/checkout.css',
];

let bundle = '/* SYAFRA Production CSS Bundle */\n';
let totalSize = 0;

CSS_FILES.forEach((file) => {
    const filePath = path.join(ROOT, file);
    try {
        const content = fs.readFileSync(filePath, 'utf8');
        bundle += `\n/* === ${path.basename(file)} === */\n`;
        bundle += content;
        totalSize += content.length;
    } catch (err) {
        console.warn(`Warning: Could not read ${file}: ${err.message}`);
    }
});

// Also append Tailwind output (utility classes)
const tailwindPath = path.join(ROOT, 'static', 'css', 'output.css');
try {
    const tailwind = fs.readFileSync(tailwindPath, 'utf8');
    bundle += `\n/* === Tailwind CSS Output === */\n`;
    bundle += tailwind;
    totalSize += tailwind.length;
} catch (err) {
    console.warn(`Warning: Could not read output.css: ${err.message}`);
}

fs.writeFileSync(OUTPUT, bundle, 'utf8');

const sizeKB = (Buffer.byteLength(bundle, 'utf8') / 1024).toFixed(1);
console.log(`Bundle created: ${OUTPUT}`);
console.log(`Size: ${sizeKB} KB (${CSS_FILES.length} files merged)`);
