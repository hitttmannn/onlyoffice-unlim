#!/usr/bin/env python3
"""Basic HTTP checks only; cannot prove editing, licensing or integration."""
import urllib.request
base='http://127.0.0.1:18080'
for path in ['/healthcheck','/web-apps/apps/api/documents/api.js']:
    with urllib.request.urlopen(base+path,timeout=15) as r:
        body=r.read()
        assert r.status==200 and body, path
        if path=='/healthcheck': assert body.strip()==b'true', body
print('PASS: healthcheck and editor API assets. Functional acceptance still required.')
