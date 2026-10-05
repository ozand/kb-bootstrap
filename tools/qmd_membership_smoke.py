"""Explicitly consented synthetic QMD 2.8.3 membership smoke, not an auto-test.

Run only after owner consent to one hook-free TEMP update. Retains owned state.
"""
import argparse
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
import yaml
from kb_bootstrap.bounded_process import run_bounded
from kb_bootstrap.qmd_adapter import installed_launch, MODEL_DEFAULTS

POSITIVE = ('canonical.md', 'nested/проверка.md')
NEGATIVE = ('raw/a.md', 'RaW/a.md', 'nested/RESEARCH/a.md',
            'research/a.md', 'LESSONS/a.md', '.hidden/a.md',
            'nested/.secret/a.md', '.hidden.md', 'INDEX.md',
            'nested/LoG.md', 'other.txt')
IGNORE = ['**/[rR][aA][wW]/**', '**/[rR][eE][sS][eE][aA][rR][cC][hH]/**',
          '**/[lL][eE][sS][sS][oO][nN][sS]/**', '**/.*', '**/.*/**',
          '**/[iI][nN][dD][eE][xX].[mM][dD]', '**/[lL][oO][gG].[mM][dD]']


def prepare(base):
    root = base / 'canonical'
    state = base / 'state'
    cwd = base / 'cwd'
    cwd.mkdir()
    (state / 'config').mkdir(parents=True)
    (state / 'cache/qmd').mkdir(parents=True)
    tokens = {}
    for number, name in enumerate(POSITIVE + NEGATIVE):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tokens[name] = 'membershiptoken%02dquartz' % number
        path.write_text('# Synthetic\n' + tokens[name] + '\n', encoding='utf-8')
    config = {'collections': {'fixture': {'path': str(root), 'pattern': '**/*.md',
              'ignore': IGNORE}}, 'models': MODEL_DEFAULTS}
    (state / 'config/membership.yml').write_text(yaml.safe_dump(config), encoding='utf-8')
    return root, state, cwd, tokens

def execute(consented=False):
    import os
    if not consented:
        raise ValueError('explicit synthetic update consent required')
    launch, reason = installed_launch()
    if reason:
        raise RuntimeError(reason)
    base = Path(tempfile.mkdtemp(prefix='kb-qmd-membership-'))
    root, state, cwd, tokens = prepare(base)
    before = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in tokens}
    env = {k: v for k, v in os.environ.items() if not (k.startswith('QMD_') or k.startswith('XDG_') or k.startswith('NODE_') or k == 'INDEX_PATH')}
    database = state / 'cache/qmd/membership.sqlite'
    env.update(QMD_CONFIG_DIR=str(state / 'config'), XDG_CACHE_HOME=str(state / 'cache'), INDEX_PATH=str(database))
    version, reason = run_bounded(launch + ['--version'], cwd, env)
    import re
    if reason or not re.fullmatch(rb'qmd 2\.8\.3(?: \([0-9a-f]{7,40}\))?\r?\n?', version):
        raise RuntimeError('pinned version unavailable; scratch preserved')
    # Exactly one authorized mutation; do not retry it implicitly.
    output, reason = run_bounded(launch + ['--index', 'membership', 'update'], cwd, env)
    if reason:
        raise RuntimeError('update failed; scratch preserved: ' + reason)
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        actual = {row[0] for row in connection.execute("SELECT path FROM documents WHERE collection=? AND active=1", ('fixture',))}
        collections = {row[0] for row in connection.execute('SELECT DISTINCT collection FROM documents')}
    if actual != set(POSITIVE) or collections != {'fixture'}:
        raise AssertionError('indexed membership mismatch; scratch preserved')
    for name, token in tokens.items():
        raw, reason = run_bounded(launch + ['--index', 'membership', 'search', '-c', 'fixture', '--format', 'json', '-n', '10', '--', token], cwd, env)
        if reason:
            raise RuntimeError('lexical query failed; scratch preserved')
        hits = json.loads(raw.decode('utf-8'))
        if bool(hits) != (name in POSITIVE):
            raise AssertionError('lexical membership mismatch; scratch preserved')
    after = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in tokens}
    if after != before or (state / 'cache/qmd/models').exists():
        raise AssertionError('unexpected source/model artifacts; scratch preserved')
    return {'status': 'OK', 'indexed': len(actual), 'excluded': len(NEGATIVE),
            'queries': len(tokens), 'version': version.decode().strip(),
            'scope': 'synthetic-only; egress-unverified', 'scratch_retained': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--consent-synthetic-update', action='store_true', required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.consent_synthetic_update)))

