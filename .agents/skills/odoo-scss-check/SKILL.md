---
name: odoo-scss-check
description: >-
  Odoo compiles SCSS with libsass (LibSass 3.6), which rejects parts of modern
  Sass and CSS syntax, and a single error breaks the styling of the whole
  bundle. Use when writing or editing any .scss file in an addon of this
  folder, or adding one to a manifest's assets; run check_scss.py afterwards.
---

# Checking SCSS against Odoo's compiler

Odoo 18 compiles SCSS with **libsass** (LibSass 3.6, deprecated since 2020), not
Dart Sass. It compiles all SCSS in an asset bundle as one source, so one error in
an addon removes the compiled styles of the whole bundle, e.g. the entire backend
in `web.assets_backend`. The error then shows only in the browser and the server
log; editing the file itself raises nothing.

## Run the check after every SCSS change

Inside the Odoo container, from this folder:

```sh
python3 .agents/skills/odoo-scss-check/check_scss.py
```

It compiles every asset bundle that contains SCSS from this folder's addons,
exactly as the server does, and prints the file, line and error for each
failure (exit status 1). Pass bundle names to check only those. It reads the
database from `/etc/odoo/odoo.conf` and writes nothing.

- An addon's SCSS is only in a bundle once the addon is **installed**. The check
  reports uninstalled addons with `SKIP`; install the addon to check it.
- Manifest `assets` changes are picked up without upgrading the module.
- If the agent runs outside the Odoo container, prefix the command with
  `diploi exec app --` and use the path the folder is mounted at there
  (`/mnt/extra-addons`).

Do not report SCSS work as done until the check passes.

## libsass pitfalls

| Fails in libsass                         | Write instead                                         |
| ---------------------------------------- | ----------------------------------------------------- |
| `@use "sass:math";`, `@forward`          | nothing: variables, mixins and functions from earlier files in the bundle are already in scope. libsass copies these rules to the CSS unchanged, so the check scans for them separately |
| `math.div($a, $b)`, any `module.fn()`    | `($a / $b)`, global functions (`percentage()`, `darken()`, …) |
| `min(100%, 50rem)`, `max(1rem, var(--x))`: CSS `min()`/`max()` with mixed units or `var()` | `unquote("min(100%, 50rem)")`; interpolate Sass values: `unquote("min(100%, #{$gap})")` |
| `rgb(0 0 0 / 50%)` and other space-separated color syntax | `rgba(0, 0, 0, .5)`, `rgba($color, .5)`, `rgba(var(--x-rgb), .5)` |
| `@media (width >= 600px)` range syntax   | `@media (min-width: 600px)`, or Bootstrap's `@include media-breakpoint-up(md)` |
| `@import "my_file";` of a local file     | add the file to the bundle in `__manifest__.py`; bundle order replaces imports |

Most modern CSS passes through unchanged: nesting with `&`, `:has()`, `:is()`,
`@container`, `@layer`, `@supports`, `clamp()`, `calc()` with `var()`,
`color-mix()`, `oklch()`, logical properties. Whether a browser supports them is
a separate question.

Undefined variables are the other common failure: a variable from another
addon or from Bootstrap only exists if its file comes earlier in the same
bundle, so the addon must depend on the module that defines it.
