#!/usr/bin/env python3
"""Build the pinned baseline locally and prepare an isolated staging config."""
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    os.chdir(ROOT)
    subprocess.run(['bash', 'scripts/preflight.sh'], check=True)
    lock = json.loads(Path('runtime-candidate.json').read_text())
    base = lock['image']
    if lock['platform'] != 'linux/amd64' or not re.fullmatch(r'onlyoffice/documentserver@sha256:[a-f0-9]{64}', base):
        raise SystemExit('STOP: unsupported or unpinned baseline')
    values = {
        'BASE_IMAGE': base,
        'CANDIDATE_IMAGE': 'onlyoffice-unlim:10.0.0-169-baseline',
        'SOURCE_URL': 'https://github.com/hitttmannn/onlyoffice-unlim',
    }
    private = Path('private.env')
    if private.is_symlink():
        raise SystemExit('STOP: private.env must not be a symlink')
    if private.exists():
        parsed = dict(line.split('=', 1) for line in private.read_text().splitlines() if line and not line.startswith('#'))
        if any(parsed.get(k) != v for k,v in values.items()) or not re.fullmatch('[a-f0-9]{64}', parsed.get('JWT_SECRET', '')):
            raise SystemExit('STOP: existing private.env differs; review it locally without sharing secrets')
        private.chmod(0o600)
    else:
        fd = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(''.join(f'{k}={v}\n' for k,v in values.items()))
            stream.write(f'JWT_SECRET={secrets.token_hex(32)}\n')
    env = dict(os.environ, **values)
    subprocess.run(['bash', 'scripts/build.sh'], env=env, check=True)
    # Quiet validation: never print the interpolated JWT configuration.
    subprocess.run(['docker', 'compose', '--env-file', 'private.env', 'config', '--quiet'], check=True)
    print('PASS: local baseline built, private.env ready (0600), Compose config valid.')
    print('No staging services started. No image pushed. No production changes.')

if __name__ == '__main__':
    main()
