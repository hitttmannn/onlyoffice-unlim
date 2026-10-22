#!/usr/bin/env python3
"""Install a separate Docs 10 and mobile app; switch endpoints only with explicit switch action."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
NC=Path('/var/www/nextcloud')
PRIVATE=ROOT/'private/nc-mobile'
APP=NC/'apps/onlyoffice_mobile'
VHOST=Path('/etc/apache2/sites-enabled/default-ssl.conf')
PROXY=Path('/etc/apache2/onlyoffice-unlim-mobile-proxy.conf')
INCLUDE='    IncludeOptional /etc/apache2/onlyoffice-unlim-mobile-proxy.conf\n'
PUBLIC='https://nc.evgeny-a.ru:65443'
NEW_DOCS=PUBLIC+'/oo10/'
OCC=['sudo','-u','www-data','php',str(NC/'occ')]
C=['docker','compose','--file',str(ROOT/'deployment/compose.nc-mobile.yaml'),'--env-file',str(PRIVATE/'candidate.env')]

def output(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout.strip()
def call(args):subprocess.run(args,check=True)
def old_url():return output(OCC+['config:app:get','onlyoffice','DocumentServerUrl'])
def hashfile(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def health(url,wait=300):
    end=time.monotonic()+wait
    while time.monotonic()<end:
        try:
            with urllib.request.urlopen(url,timeout=5) as r:
                if r.read().strip()==b'true':return
        except Exception:pass
        time.sleep(3)
    raise RuntimeError('Healthcheck did not pass: '+url)
def dotenv(value):
    if any(c in value for c in '\r\n\x00'):raise RuntimeError('Unexpected multiline secret/header')
    return "'"+value.replace("'","\\'")+"'"
def configtest():
    result=subprocess.run(['apache2ctl','configtest'],capture_output=True,text=True)
    (PRIVATE/'apache-configtest.private.log').write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError('Apache configtest failed; see private apache-configtest.private.log')
def copy_app():
    if APP.exists():raise RuntimeError('App folder already exists; refusing to overwrite')
    shutil.copytree(ROOT/'nextcloud-app/onlyoffice_mobile',APP)
    import pwd
    account=pwd.getpwnam('www-data')
    for p in [APP,*APP.rglob('*')]:
        if p.is_symlink():raise RuntimeError('Unexpected app symlink')
        os.chown(p,account.pw_uid,account.pw_gid);p.chmod(0o755 if p.is_dir() else 0o644)
    call(['php','-l',str(APP/'lib/Controller/MobileController.php')])
def prepare():
    if PRIVATE.exists():raise RuntimeError('Preparation directory already exists; inspect previous run before retrying')
    info=json.loads(output(OCC+['status','--output=json']))
    if not str(info.get('versionstring','')).startswith('35.') or info.get('maintenance') or info.get('needsDbUpgrade'):
        raise RuntimeError('Nextcloud 35 must be installed, outside maintenance and without pending DB upgrade')
    version=ET.parse(NC/'apps/onlyoffice/appinfo/info.xml').getroot().findtext('version')
    if version!='10.2.1':raise RuntimeError('Only connector 10.2.1 has been tested')
    original=subprocess.run(['docker','inspect','onlyoffice-document-server','--format','{{.State.Running}}'],capture_output=True,text=True)
    if original.returncode or original.stdout.strip()!='true':
        retired=ROOT/'private/retired-onlyoffice/latest.json'
        if not retired.exists() or json.loads(retired.read_text()).get('phase')!='removed':
            raise RuntimeError('Original Docs must be running, or retired with the cold-backup script')
    if APP.exists() or PROXY.exists():raise RuntimeError('New app/proxy already exists; refusing overwrite')
    if shutil.disk_usage(ROOT).free<4*1024**3:raise RuntimeError('Less than 4 GiB disk free')
    mem={l.split(':')[0]:int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if len(l.split())>1 and l.split()[1].isdigit()}
    if mem['MemAvailable']<2500*1024:raise RuntimeError('Less than 2500 MiB RAM available')
    # Read the connector secret directly into a private env; never print it or send to GitHub.
    secret=output(OCC+['config:app:get','onlyoffice','jwt_secret'])
    if not secret:raise RuntimeError('Connector JWT secret is empty; refusing JWT-disabled integration')
    header_result=subprocess.run(OCC+['config:app:get','onlyoffice','jwt_header'],capture_output=True,text=True)
    if header_result.returncode not in (0,1):raise RuntimeError('Could not read JWT header configuration')
    header=header_result.stdout.strip() or 'Authorization'
    if not re.fullmatch('[A-Za-z0-9-]+',header):raise RuntimeError('Unexpected JWT header')
    if not VHOST.exists():raise RuntimeError('Expected SSL vhost file is missing')
    text=VHOST.read_text()
    matches=[m for m in re.finditer(r'<VirtualHost\s+([^>]+)>',text,re.I) if re.search(r':65443(?:\s|$)',m.group(1))]
    if len(matches)!=1 or '/oo10' in text:raise RuntimeError('Ambiguous vhost or existing /oo10 route')
    PRIVATE.mkdir(parents=True,mode=0o700)
    (ROOT/'private').chmod(0o700)
    (PRIVATE/'candidate.env').write_text('JWT_SECRET='+dotenv(secret)+'\nJWT_HEADER='+dotenv(header)+'\n')
    (PRIVATE/'candidate.env').chmod(0o600)
    shutil.copy2(VHOST.resolve(),PRIVATE/'apache-vhost-before.private.conf')
    state={'original_docs_url':old_url(),'vhost_sha256':hashfile(VHOST),'phase':'preparing'}
    (PRIVATE/'state.json').write_text(json.dumps(state,indent=2))
    plugin=PRIVATE/'plugin';plugin.mkdir(mode=0o755);plugin.chmod(0o755)
    for name in ['config.json','bridge.html','bridge.js']:
        src=ROOT/'prototype-mobile/plugin'/name
        text=src.read_text()
        if name=='bridge.html':text=text.replace('http://127.0.0.1:18780/sdkjs-plugins/v1/plugins.js','../v1/plugins.js')
        if name=='bridge.js':text=text.replace('http://127.0.0.1:18781',PUBLIC)
        (plugin/name).write_text(text);(plugin/name).chmod(0o644)
    copy_app()
    call(C+['config','--quiet']);call(C+['pull','docs']);call(C+['up','-d','--no-build','docs'])
    print('Waiting for separate local Docs 10 healthcheck...',flush=True)
    health('http://127.0.0.1:18082/healthcheck')
    if old_url()!=state['original_docs_url']:raise RuntimeError('Original connector URL changed externally; inspect before proceeding')
    state['phase']='prepared';(PRIVATE/'state.json').write_text(json.dumps(state,indent=2))
    print('PREPARED. Original connector settings unchanged. New app is not enabled; Apache not changed.')
    print('Next: python3 scripts/nc-mobile-install.py activate')
def activate():
    state=json.loads((PRIVATE/'state.json').read_text())
    if state.get('phase')!='prepared':raise RuntimeError('Run prepare successfully first')
    if old_url()!=state['original_docs_url'] or hashfile(VHOST)!=state['vhost_sha256']:
        raise RuntimeError('Connector URL or vhost changed since preparation; refusing overwrite')
    if PROXY.exists():raise RuntimeError('Proxy file already exists')
    health('http://127.0.0.1:18082/healthcheck',30)
    text=VHOST.read_text()
    matches=[m for m in re.finditer(r'<VirtualHost\s+([^>]+)>',text,re.I) if re.search(r':65443(?:\s|$)',m.group(1))]
    if len(matches)!=1:raise RuntimeError('Ambiguous vhost')
    modified=text[:matches[0].end()]+'\n'+INCLUDE+text[matches[0].end():]
    proxy='''# Managed by onlyoffice-unlim mobile test deployment
ProxyPass "/oo10/" "http://127.0.0.1:18082/" upgrade=websocket
ProxyPassReverse "/oo10/" "http://127.0.0.1:18082/"
<Location "/oo10/">
    Require all granted
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Host "nc.evgeny-a.ru:65443/oo10"
    ProxyAddHeaders Off
</Location>
'''
    call(['a2enmod','proxy','proxy_http','headers'])
    try:
        PROXY.write_text(proxy);PROXY.chmod(0o644);VHOST.write_text(modified)
        configtest();call(['apache2ctl','graceful'])
        health(NEW_DOCS+'healthcheck',30)
        for key,value in [('docs_url',NEW_DOCS),('docs_internal_url','http://127.0.0.1:18082/')]:
            output(OCC+['config:app:set','onlyoffice_mobile',key,'--value='+value])
        call(OCC+['app:enable','onlyoffice_mobile'])
        if old_url()!=state['original_docs_url']:raise RuntimeError('Original connector URL unexpectedly changed')
        state['phase']='active-test';(PRIVATE/'state.json').write_text(json.dumps(state,indent=2))
    except Exception:
        # Remove only this deployment include, retaining unrelated concurrent edits.
        current=VHOST.read_text();VHOST.write_text(current.replace(INCLUDE,''))
        PROXY.unlink(missing_ok=True)
        configtest();call(['apache2ctl','graceful'])
        subprocess.run(OCC+['app:disable','onlyoffice_mobile'],capture_output=True)
        raise
    print('TEST APP ACTIVE: '+PUBLIC+'/index.php/apps/onlyoffice_mobile/')
    print('Only administrators are allowed by default. Use DOCX/XLSX copies in the root Files folder.')
    print('Original ONLYOFFICE URL unchanged. Next: nc-mobile-install.py switch')

def switch():
    state=json.loads((PRIVATE/'state.json').read_text())
    if state.get('phase')!='active-test':raise RuntimeError('Activate the new route/app first')
    # Only endpoint settings are changed; the old secret and storage settings remain intact.
    result=subprocess.run(OCC+['config:app:get','onlyoffice','DocumentServerInternalUrl'],capture_output=True,text=True)
    state['original_internal_url']=result.stdout.strip()
    state['before_switch_url']=old_url()
    (PRIVATE/'state.json').write_text(json.dumps(state,indent=2))
    try:
        output(OCC+['config:app:set','onlyoffice','DocumentServerUrl','--value='+NEW_DOCS])
        output(OCC+['config:app:set','onlyoffice','DocumentServerInternalUrl','--value=http://127.0.0.1:18082/'])
    except Exception:
        output(OCC+['config:app:set','onlyoffice','DocumentServerUrl','--value='+state['before_switch_url']])
        output(OCC+['config:app:set','onlyoffice','DocumentServerInternalUrl','--value='+state['original_internal_url']])
        raise
    state['phase']='switched';(PRIVATE/'state.json').write_text(json.dumps(state,indent=2))
    print('Standard ONLYOFFICE connector now uses '+NEW_DOCS)
    print('For the custom phone UI open '+PUBLIC+'/index.php/apps/onlyoffice_mobile/')

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','activate','switch']);args=p.parse_args()
    if os.geteuid()!=0:raise SystemExit('Run as root on nc')
    os.umask(0o077)
    if args.action=='prepare':prepare()
    elif args.action=='activate':activate()
    else:switch()
if __name__=='__main__':main()
