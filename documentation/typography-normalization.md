# Typography Normalization Plan

Goal: Make the rest of the application follow the navigation bar’s typography and font sizes with very few exceptions, while minimizing churn and preserving vendor/plugin behavior.

## Principles
- Single primary text family across the app; navbar defines the baseline.
- Single canonical size scale (CSS variables) used everywhere.
- Keep icon packs minimal; provide a deprecation path for extras.
- Favor tokens over hard-coded values. Inline styles should be replaced by classes.
- Be Bootstrap-aligned: map our tokens to Bootstrap’s variables where useful.

## Current navbar baselines (Bootstrap)
- Brand size: var(--bs-navbar-brand-font-size) = 1.25rem (from bootstrap.min.css)
- Nav-link size: var(--bs-nav-link-font-size) (not set by default; effectively ~1rem). We will set it explicitly.
- Body font family: var(--bs-body-font-family)

## Canonical families
- Base body/headings: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif
- Monospace (code/logs): 'SF Mono', 'Fira Mono' or 'Fira Code' fallback -> var(--bs-font-monospace) where possible
- Icons: Prefer "Font Awesome 6 Free" and "Material Icons Outlined"; phase out older/duplicates.

## Canonical size scale (tokens)
Define in a single place (e.g., app/static/css/themes.css or typography.css) and map navbar to it.

:root {
  /* Canonical scale */
  --font-size-xs: 0.75rem;   /* 12px */
  --font-size-sm: 0.875rem;  /* 14px */
  --font-size-base: 1rem;    /* 16px */
  --font-size-md: 1.125rem;  /* 18px */
  --font-size-lg: 1.25rem;   /* 20px (navbar brand) */
  --font-size-xl: 1.5rem;    /* 24px */
  --font-size-2xl: 2rem;     /* 32px */
  --font-size-3xl: 3rem;     /* 48px */

  /* Navbar mapping */
  --bs-navbar-brand-font-size: var(--font-size-lg);
  --bs-nav-link-font-size: var(--font-size-base);
  --bs-body-font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

Backwards-compat aliasing (to stabilize pages referencing var(--text-*)): add temporary aliases, then refactor.

:root {
  --text-xs: var(--font-size-xs);
  --text-sm: var(--font-size-sm);
  --text-base: var(--font-size-base);
  --text-md: var(--font-size-md);
  --text-lg: var(--font-size-lg);
  --text-xl: var(--font-size-xl);
}

## Usage guidelines
- Body text: var(--font-size-base)
- Small text, captions, badges: var(--font-size-sm) or var(--font-size-xs)
- Subtitles, secondary headings: var(--font-size-md)
- H1–H3 typical: lg (20), xl (24), 2xl (32); 3xl (48) reserved for prominent hero sections only
- Navbar: brand var(--font-size-lg), nav links var(--font-size-base)
- Avoid one-off px/em unless absolutely necessary; prefer the scale.

## JS alignment
- Replace hard-coded canvas/Chart.js sizes (e.g., 17px, 24px) with values derived from CSS variables. Examples:
  - Read computed sizes from a reference element that uses the token (e.g., a hidden .typography-probe element) or inject the CSS variable into JS via data-attributes.
  - For canvas text: ctx.font = `${computedSizePx}px ${preferredFamily}` using computedSizePx from var(--font-size-*)
- Unify JS fontFamily to the base: use 'Inter' stack by default, read from getComputedStyle(body).fontFamily.

## Plugins
- Do not modify vendor bundles. Create lightweight overrides to make plugin text inherit from body font and size tokens (e.g., override 'Open Sans' to inherit/base family).
- Respect plugin-specific utilities (e.g., var(--fc-small-font-size,.85em)) but make visible text consistent with our base.

## Icons policy
- Keep: Font Awesome 6 Free, Material Icons Outlined
- Phase out: Font Awesome 5 variants, Material Design Iconic Font, Themify, Fontello, duplicate FA brands if not needed
- Migration: replace icon usages gradually; provide a mapping where feasible

## Exceptions policy
- Landing pages and marketing hero sections may use 2xl/3xl; single-off extremes (e.g., 80px/140px) only where strictly justified.
- PDF/report exports may keep specific sizes for layout fidelity, but should still map to our scale when possible.

## Rollout plan
1) Foundation (low risk)
   - Define the canonical tokens and alias --text-* to --font-size-* (no visual change intended)
   - Set --bs-body-font-family, --bs-navbar-brand-font-size, --bs-nav-link-font-size based on the scale
2) Adoption (incremental)
   - Replace inline font-size in templates with classes bound to tokens
   - Update app/static/css to use --font-size-* instead of hard-coded px/rem/em
   - Adjust JS to read tokens for font sizes and font family
3) Rationalize icons
   - Start using Font Awesome 6 Free + Material Icons Outlined only in new work
   - Create an icon deprecation list and gradually migrate old usages
4) Cleanup
   - Remove --text-* aliases after codebase stops using them
   - Remove dead icon packs once migrations complete

## Success criteria
- All major pages render with the same base family and consistent heading/body scale
- No hard-coded font sizes in templates/JS for standard text
- Third-party plugins visually integrate with site typography via minimal overrides
- Icon packs reduced to the chosen set

