#!/usr/bin/env python3
"""Compile every Odoo asset bundle that contains SCSS from this folder's addons.

Odoo compiles SCSS lazily, when a browser first requests a bundle, and reports
failures only inside the served CSS. This script compiles the bundles up front,
the same way the server does, so a broken stylesheet is caught right after the
edit.

Run it inside the Odoo container:

    python3 .agents/skills/odoo-scss-check/check_scss.py

Exit status: 0 when every bundle compiles, 1 on SCSS errors, 2 when the check
itself could not run.
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

ADDONS_DIR = Path(__file__).resolve().parents[3]
PREPROCESSED = ('.scss', '.sass', '.less')
RX_MODULE_RULE = re.compile(r'^\s*@(use|forward)\b')
RX_LINE = re.compile(r'on line (\d+)(?::(\d+))? of /?stdin')


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument(
        '-c', '--config',
        default=os.environ.get('ODOO_RC', '/etc/odoo/odoo.conf'),
        help='Odoo configuration file (default: %(default)s)',
    )
    parser.add_argument(
        '-d', '--database',
        help='database to check against (default: db_name from the config, '
             'then $DATABASE)',
    )
    parser.add_argument(
        'bundles', nargs='*',
        help='only check these bundles (default: every bundle that contains '
             'SCSS from this folder)',
    )
    return parser.parse_args()


def local_addons():
    return {
        path.parent.name
        for path in ADDONS_DIR.glob('*/__manifest__.py')
    }


def is_local_stylesheet(url, addons):
    parts = url.lstrip('/').split('/', 1)
    return parts[0] in addons and url.endswith(PREPROCESSED)


def module_rules(addons):
    """libsass copies @use/@forward to the CSS untouched instead of failing."""
    for addon in sorted(addons):
        for path in sorted((ADDONS_DIR / addon).glob('static/**/*.scss')):
            with path.open(encoding='utf-8', errors='replace') as file:
                for number, line in enumerate(file, 1):
                    if RX_MODULE_RULE.match(line):
                        url = '/' + str(path.relative_to(ADDONS_DIR))
                        yield url, number, line.strip()


def candidate_bundles(env, installed):
    """Every bundle name declared by an installed manifest or an ir.asset."""
    from odoo.modules.module import get_manifest

    bundles = set(env['ir.asset'].sudo().search([]).mapped('bundle'))
    for addon in installed:
        bundles.update((get_manifest(addon) or {}).get('assets', {}))
    # "addon._name" bundles are only ever included into other bundles.
    return sorted(
        name for name in bundles
        if name.count('.') == 1 and not name.split('.')[1].startswith('_')
    )


def locate(bundle):
    """Find the stylesheet that breaks the bundle's SCSS compilation.

    libsass reports positions in the concatenated bundle, and some errors
    ("Internal Error: ...") carry no position at all, so bisect: compile
    ever longer prefixes of the bundle until one fails. Returns
    (url, line, column, message, source line), or None; line, column
    and source line are None when libsass gives no position.
    """
    from odoo.addons.base.models.assetsbundle import (
        CompileError, ScssStylesheetAsset,
    )

    assets = [a for a in bundle.stylesheets
              if isinstance(a, ScssStylesheetAsset)]
    sources = [a.get_source() for a in assets]

    def error_of_source(source):
        try:
            assets[0].compile(source)
        except CompileError as e:
            return str(e)
        return None

    def error_of(count):
        return error_of_source('\n'.join(sources[:count]))

    if not assets or not error_of(len(assets)):
        return None
    low, high = 1, len(assets)
    while low < high:
        middle = (low + high) // 2
        if error_of(middle):
            high = middle
        else:
            low = middle + 1

    error = error_of(low)
    source = sources[low - 1].split('\n')
    line = column = excerpt = None
    match = RX_LINE.search(error)
    if match:
        # libsass miscounts lines in large bundles, so measure from a
        # sentinel placed where this asset's "/*! id */" marker line is.
        sentinel = error_of_source('\n'.join(
            sources[:low - 1] + ['@error "check_scss sentinel";']))
        marker = RX_LINE.search(sentinel or '')
        if marker:
            line = int(match.group(1)) - int(marker.group(1))
            column = match.group(2)
            if 0 < line < len(source):
                excerpt = source[line].strip()
    return assets[low - 1].url or '<inline>', line, column, error, excerpt


def describe(bundle, error):
    message = error.split('This error occurred while compiling the bundle')[0]
    message = message.split('\n')[0].strip()
    where = locate(bundle)
    if not where:
        return message
    url, line, column, located, excerpt = where
    position = url
    if line is not None:
        position += f':{line}' + (f':{column}' if column else '')
    first_line = located.split('\n')[0].strip()
    description = f'{position}: {first_line}'
    if excerpt:
        description += f'\n      >> {excerpt}'
    return description


def main():
    args = parse_args()
    addons = local_addons()
    if not addons:
        print(f'No addons (directories with __manifest__.py) in {ADDONS_DIR}.')
        return 0

    try:
        import odoo
        from odoo import SUPERUSER_ID, api
        from odoo.modules.module import get_manifest
        from odoo.modules.registry import Registry
    except ImportError:
        print('Cannot import odoo. Run this inside the Odoo container.',
              file=sys.stderr)
        return 2

    odoo.tools.config.parse_config(['-c', args.config])
    # The server logs every compile error with the full bundle file list;
    # this script prints a shorter version of the same error instead.
    logging.basicConfig(level=logging.ERROR)
    logging.getLogger('odoo').setLevel(logging.ERROR)

    database = (
        args.database
        or odoo.tools.config['db_name']
        or os.environ.get('DATABASE')
    )
    if not database:
        print('No database given; pass --database.', file=sys.stderr)
        return 2

    registry = Registry(database)
    cr = registry.cursor()
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        installed = env['ir.asset']._get_installed_addons_list()

        for addon in sorted(addons - set(installed)):
            assets = (get_manifest(addon) or {}).get('assets', {})
            if any(str(path).endswith(PREPROCESSED)
                   for paths in assets.values() for path in paths):
                print(f'SKIP  {addon}: not installed in "{database}", so its '
                      f'SCSS is in no bundle. Install it to check it.')

        failed = checked = 0
        for url, number, line in module_rules(addons):
            failed += 1
            print(f'FAIL  {url}:{number}: Odoo\'s libsass has no module '
                  f'system; this rule ends up in the CSS unchanged and does '
                  f'nothing. Assets are shared through the bundle instead.')
            print(f'      >> {line}')

        errors = {}  # raw error -> [description, bundle names]
        for name in args.bundles or candidate_bundles(env, installed):
            try:
                files, _external = env['ir.qweb']._get_asset_content(name)
            except Exception as e:  # noqa: BLE001 - report and keep going
                print(f'FAIL  {name}: cannot resolve bundle: {e}')
                failed += 1
                continue
            if not args.bundles and not any(
                    is_local_stylesheet(f['url'], addons) for f in files):
                continue

            bundle = env['ir.qweb']._get_asset_bundle(name, js=False)
            bundle.preprocess_css()
            checked += 1
            if not bundle.css_errors:
                print(f'OK    {name}')
                continue
            failed += 1
            for error in bundle.css_errors:
                # Bundles that include one another fail on the same error;
                # locate it once and list every bundle it breaks.
                key = error.split('This error occurred')[0]
                if key not in errors:
                    errors[key] = [describe(bundle, error), []]
                errors[key][1].append(name)

        for description, names in errors.values():
            print(f'FAIL  {description}')
            print(f'      breaks: {", ".join(names)}')

        if not checked and not failed:
            print('No installed addon from this folder adds SCSS to a bundle.')
        return 1 if failed else 0
    finally:
        cr.rollback()
        cr.close()


if __name__ == '__main__':
    sys.exit(main())
