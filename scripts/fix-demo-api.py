#!/usr/bin/env python3
"""Reversible local example config override; staging project only."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ['docker', 'compose', '--project-name', 'onlyoffice-unlim-stage',
           '--file', str(ROOT / 'compose.yaml'), '--env-file', str(ROOT / 'private.env')]
PATCH = r'''
import json, os, shutil
from pathlib import Path
p = Path('/etc/onlyoffice/documentserver-example/local.json')
backup = p.with_name('local.json.before-api-fix.bak')
absent = p.with_name('local.json.before-api-fix.absent')
if p.is_symlink():
    raise SystemExit('STOP: local.json is a symlink; inspect manually')
if action == 'restore':
    if backup.exists():
        shutil.copy2(backup, p)
    elif absent.exists():
        p.unlink(missing_ok=True)
    else:
        raise SystemExit('STOP: no saved original config')
    print('Original example local config restored.')
else:
    cfg = json.loads(p.read_text()) if p.exists() else {}
    server = cfg.setdefault('server', {})
    if not isinstance(server, dict):
        raise SystemExit('STOP: unexpected server config structure')
    if not backup.exists() and not absent.exists():
        if p.exists():
            shutil.copy2(p, backup)
            backup.chmod(0o600)
        else:
            absent.touch(mode=0o600)
    server['apiUrl'] = 'web-apps/apps/api/documents/api.js'
    # Retain the file's current owner/mode and all JWT and other config fields.
    with p.open('w') as f:
        json.dump(cfg, f, indent=2)
        f.write('\n')
    if absent.exists():
        p.chmod(0o644)
    print('Set server.apiUrl for staging example; original config saved privately.')
'''

def main():
    action = sys.argv[1] if len(sys.argv) == 2 else 'apply'
    if action not in {'apply', 'restore'}:
        raise SystemExit('Usage: python3 scripts/fix-demo-api.py [apply|restore]')
    subprocess.run(COMPOSE + ['exec', '-T', 'docs', 'python3', '-'],
                   input='action = ' + repr(action) + '\n' + PATCH,
                   text=True, cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT/'scripts/demo.py'), 'stop'], check=True)
    subprocess.run([sys.executable, str(ROOT/'scripts/demo.py'), 'start'], check=True)
    print('Reload the editor with Ctrl+Shift+R. If unchanged, run this script with restore.')
    print('This is a candidate config fix, not yet validated against the installed example code.')

if __name__ == '__main__':
    main()
