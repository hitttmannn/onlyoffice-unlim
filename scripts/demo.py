#!/usr/bin/env python3
"""Control only the built-in example inside the fixed staging Compose project."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ['docker', 'compose', '--project-name', 'onlyoffice-unlim-stage',
          '--file', str(ROOT / 'compose.yaml'), '--env-file', str(ROOT / 'private.env'),
          'exec', '-T', 'docs', 'supervisorctl']
NAMES = {'ds:example', 'example', 'ds-example'}

def select_service(output):
    matches = [line.split()[0] for line in output.splitlines()
               if line.split() and line.split()[0] in NAMES]
    if len(matches) != 1:
        raise ValueError('Expected exactly one known example service; do not start all services')
    return matches[0]

def main():
    action = sys.argv[1] if len(sys.argv) == 2 else 'status'
    if action not in {'start', 'stop', 'status'}:
        raise SystemExit('Usage: python3 scripts/demo.py [start|stop|status]')
    result = subprocess.run(PREFIX + ['status'], cwd=ROOT, capture_output=True, text=True)
    # supervisorctl status can return nonzero when a registered service is stopped.
    try:
        name = select_service(result.stdout)
    except ValueError as error:
        print(result.stdout, end='')
        print(result.stderr, end='', file=sys.stderr)
        raise SystemExit(str(error))
    subprocess.run(PREFIX + [action if action != 'status' else 'status', name], cwd=ROOT, check=True)
    if action == 'start':
        print('Open http://127.0.0.1:18080/example/ through an SSH tunnel.')
        print('Use disposable test documents only. Nextcloud integration is not tested here.')

if __name__ == '__main__':
    main()
