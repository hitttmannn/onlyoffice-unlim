#!/usr/bin/env python3
"""Persist demo storage and relay, then recreate only the staging Docs service."""
from pathlib import Path
from datetime import datetime, timezone
import os
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
C = ['docker', 'compose', '--project-name', 'onlyoffice-unlim-stage', '--file',
     str(ROOT/'compose.yaml'), '--env-file', str(ROOT/'private.env')]
SOURCE = '/var/lib/onlyoffice/documentserver-example'

def main():
    os.chdir(ROOT)
    subprocess.run(C+['config', '--quiet'], check=True)
    target = ROOT/'artifacts/stage-example'
    if target.exists():
        raise SystemExit('STOP: persistent example directory already exists; do not overwrite or rerun migration')
    # Abort before recreation if the actual storage location differs.
    result = subprocess.run(C+['exec','-T','docs','stat','-c','%a %u %g',SOURCE],
                            capture_output=True, text=True, check=True)
    mode, uid, gid = result.stdout.strip().split()
    subprocess.run([sys.executable, str(ROOT/'scripts/demo.py'), 'stop'], check=True)
    target.mkdir(parents=True, mode=0o700)
    subprocess.run(C+['cp','-a','docs:'+SOURCE+'/.',str(target)], check=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = ROOT/f'artifacts/example-before-recreate-{stamp}.tar.gz'
    with archive.open('xb') as stream:
        os.chmod(archive, 0o600)
        with tarfile.open(fileobj=stream, mode='w:gz') as tar:
            tar.add(target, arcname='documentserver-example')
    # Container ds UID/GID must retain access to the bind-mounted directory.
    os.chown(target, int(uid), int(gid))
    os.chmod(target, int(mode, 8))
    print('Test data copied; private backup:', archive.name, flush=True)
    subprocess.run(C+['up','-d','--no-build','--no-deps','--force-recreate','docs'], check=True)
    deadline = time.monotonic()+300
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen('http://127.0.0.1:18080/healthcheck', timeout=5) as r:
                if r.read().strip()==b'true':
                    break
        except Exception:
            pass
        time.sleep(3)
    else:
        raise SystemExit('STOP: staging healthcheck did not become ready; inspect staging status')
    subprocess.run([sys.executable,str(ROOT/'scripts/demo.py'),'start'], check=True)
    print('PASS: recreated staging is ready. Recheck open/edit/save/download without Console.')

if __name__ == '__main__':
    main()
