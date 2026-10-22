#!/usr/bin/env python3
"""Staging-only loopback relay for example URLs generated from the SSH tunnel."""
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
PREFIX = ['docker', 'compose', '--project-name', 'onlyoffice-unlim-stage', '--file',
          str(ROOT/'compose.yaml'), '--env-file', str(ROOT/'private.env'), 'exec', '-T', 'docs']
CONF = '''# Managed by onlyoffice-unlim staging loopback fix
server {
    listen 127.0.0.1:18080;
    server_name localhost;
    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
    }
}
'''
CODE = r'''
from pathlib import Path
import subprocess
p = Path('/etc/nginx/conf.d/zz-onlyoffice-unlim-stage-loopback.conf')
marker = '# Managed by onlyoffice-unlim staging loopback fix'
if p.exists() and (p.is_symlink() or not p.read_text().startswith(marker)):
    raise SystemExit('STOP: unmanaged nginx config exists')
original = p.read_bytes() if p.exists() else None
if action == 'restore':
    p.unlink(missing_ok=True)
else:
    p.write_text(conf)
try:
    subprocess.run(['nginx', '-t'], check=True)
    subprocess.run(['nginx', '-s', 'reload'], check=True)
except subprocess.CalledProcessError:
    if original is None:
        p.unlink(missing_ok=True)
    else:
        p.write_bytes(original)
    raise
print('Staging loopback relay ' + ('removed' if action == 'restore' else 'configured'))
'''
if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv)==2 else 'apply'
    if action not in {'apply', 'restore'}:
        raise SystemExit('Usage: python3 scripts/fix-demo-loopback.py [apply|restore]')
    subprocess.run(PREFIX+['python3','-'], input='action='+repr(action)+'\nconf='+repr(CONF)+'\n'+CODE,
                   text=True, check=True)
