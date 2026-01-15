# Typography Audit (Wegweiser)

## Scope and sources scanned
- Application CSS: app/static/css/**/*.css
- Landing assets: landing/sass/**/*.scss, .css
- Third-party plugins: app/static/plugins/**/*.css, .scss
- Icon font packs: app/static/fonts/**, app/static/fontawesome/**
- Templates (inline styles): app/templates/**/*.html, .jinja, .jinja2
- JS-injected styles: app/static/js/**/*.js

## Summary at a glance
- Multiple primary sans stacks in use: Inter (core), Noto Sans (landing + JS), Open Sans (plugins), Helvetica Neue (some), plus monospace stacks.
- Icon families present: Font Awesome 5/6 (Free/Brands), Material Design Icons, Material Design Iconic Font, Themify, Fontello, FullCalendar fcicons, Material Icons Outlined.
- Wide variety of sizes and units: px, rem, em, %, calc(), inherit; token sets from Bootstrap (var(--bs-...)), local (var(--font-size-...)), and ad-hoc var(--text-...).
- Large outliers: landing up to 140px; templates up to 80px and 6rem; plugins up to 78px.

## Location: Application CSS (app/static/css)
- Font families
  - 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif
  - "Helvetica Neue", sans-serif
  - Monospace: 'Fira Code'; 'Fira Mono','Consolas','Menlo','Monaco','Liberation Mono',monospace; 'Monaco','Menlo'[, 'Ubuntu Mono']; 'SF Mono','Roboto Mono',Menlo,monospace; 'Consolas','Monaco','Courier New',monospace; monospace
  - Icon/text utility: "Font Awesome 5 Free"
  - Variables: var(--bs-body-font-family), var(--bs-btn-font-family), var(--bs-font-monospace), var(--bs-font-sans-serif), var(--font-family-base), var(--font-family-headings), var(--font-heading), var(--font-mono), inherit
- Font sizes (unique)
  - rem: 0.55, 0.6, 0.625, 0.65, 0.6875, 0.7, 0.75, 0.8, 0.8125, 0.85, 0.875, 0.9, 0.9375, 0.95, 0.97, 1, 1.1, 1.125, 1.2, 1.375, 1.5, 1.75, 2, 2.5, 3, 3.5, 4, 4.5, 5
  - em: .75em, .875em, 0.75em, 0.85em, 1em, 1.1em
  - px: 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24, 32, 50
  - calc(): calc(1.275rem + .3vw), calc(1.325rem + .9vw), calc(1.375rem + 1.5vw), calc(1.3rem + .6vw), calc(1.425rem + 2.1vw), calc(1.475rem + 2.7vw), calc(1.525rem + 3.3vw), calc(1.575rem + 3.9vw), calc(1.625rem + 4.5vw)
  - Vars: var(--bs-...typography tokens), var(--font-size-xs|sm|base|md|lg|xl|2xl|3xl), var(--text-xs|sm|base|md|lg|xl), inherit

## Location: Landing assets (landing/sass)
- Font families
  - 'Noto Sans', sans-serif; "Material Icons Outlined"
- Font sizes (unique)
  - rem: 0.7, 0.75, 0.8, 0.97
  - px: 10, 13, 14, 15, 16, 18, 20, 22, 23, 24, 25, 26, 30, 32, 45, 140

## Location: Third‑party plugins (app/static/plugins)
- Font families
  - 'Open Sans', Arial, Helvetica, sans-serif; fcicons; "sans-serif, Verdana"; inherit
- Font sizes (unique)
  - em/rem: .85em, .85rem, 1em, 1.1em, 1.5em, 1.75em
  - px: 12, 13, 14, 16, 17, 18, 20, 32, 55, 60, 78
  - %/keywords: 100%, smaller, inherit
  - Vars: var(--fc-small-font-size, .85em)

## Location: Icon font packs (app/static/fonts, app/static/fontawesome)
- Font families
  - Font Awesome 5/6 (Free/Brands): "Font Awesome 5 Free", "Font Awesome 6 Free", "Font Awesome 5 Brands", "Font Awesome 6 Brands", "FontAwesome", var(--fa-style-family,"Font Awesome 6 Free")
  - Material Design: "Material Design Icons", "materialdesignicons", '#{$mdi-font-name (SCSS)'
  - Material Design Iconic: 'Material-Design-Iconic-Font'
  - Fontello: "fontello"; Themify: 'themify'
- Font sizes (utilities)
  - em: .625, .75, .875, 1, 1.25, 1.33333333, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, (4em/3), $i*1em, fa-divide(...) * 1em
  - px: 14, 18, 24, 36, 48; %/keywords: 120%, inherit

## Location: Templates and inline styles (app/templates)
- Font families
  - Inter stack; Arial, sans-serif; 'Courier New', monospace; 'Georgia', serif; monospace
- Font sizes (unique)
  - rem: 0.75, 0.85, 0.875, 0.9, 1, 1.1, 1.2, 1.25, 1.35, 1.5, 1.75, 2, 2.5, 3, 3.5, 3.75, 4, 5, 6
  - em: 0.9em; px: 10, 12, 14, 16, 18, 28, 48, 80

## Location: JS‑injected styles (app/static/js)
- Font families
  - '"Noto Sans", sans-serif' (gauge charts)
- Font sizes (examples)
  - 8px, 14px, 16px, 24px, 30px; also '17px', '24px'; inline strings 0.85rem, 2rem, 0.9em; dynamic px via Math.max(16, currentSize*0.12)

## Observations and potential issues
- Mixed primary fonts: Inter vs Noto Sans vs Open Sans (plugins) and occasional "Helvetica Neue".
- Two parallel local size token families observed: var(--font-size-*) and var(--text-*). The latter is used (e.g., device-single-refined.css) but not found defined in CSS sources scanned; consider aliasing or replacing.
- Inline styles in templates and JS introduce hard-coded sizes that diverge from tokens.
- Many icon packs co-exist; rationalization would simplify maintenance and bundle size.

## Raw references (sample paths)
- Navbar tokens from Bootstrap: app/static/css/bootstrap.min.css (e.g., --bs-navbar-brand-font-size: 1.25rem; nav-link uses var(--bs-nav-link-font-size)).
- Local theme color tokens (not sizes): app/static/css/themes.css defines --text-primary/secondary/muted, etc.
- Local size tokens: app/static/css/auth.css defines --font-size-base/sm/xl and families --font-family-base/headings.

