#!/usr/bin/env python3
"""Portable plugin rendering/app installation; never edits a proxy or replaces Docs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]

def url(value, origin=False):
    if not isinstance(value,str) or any(c.isspace() or ord(c)<32 for c in value):
        raise ValueError('URLs must not contain whitespace/control characters')
    parsed=urlsplit(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Public URLs must use HTTPS without credentials, query or fragment')
    port=parsed.port  # Validate port before creating files.
    if origin:
        host=parsed.hostname.encode('idna').decode('ascii').lower()
        if ':' in host:host='['+host+']'
        return 'https://'+host+(':'+str(port) if port not in (None,443) else '')
    return value.rstrip('/')+'/'

def config(path):
    cfg=json.loads(path.read_text())
    cfg['origin']=url(cfg['nextcloud_url'],origin=True)
    cfg['docs_url']=url(cfg['docs_url'])
    internal=cfg['docs_internal_url']
    parsed=urlsplit(internal)
    if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or any(c.isspace() or ord(c)<32 for c in internal):
        raise ValueError('Invalid docs_internal_url')
    parsed.port
    cfg['docs_internal_url']=internal.rstrip('/')+'/'
    cfg['app_dir']=Path(cfg['app_dir'])
    cfg['plugin_dir']=Path(cfg['plugin_dir'])
    if not cfg['app_dir'].is_absolute() or cfg['app_dir'].name!='onlyoffice_mobile' or not cfg['plugin_dir'].is_absolute():
        raise ValueError('Use absolute paths; app_dir must end in onlyoffice_mobile')
    if not isinstance(cfg['occ_command'],list) or not cfg['occ_command'] or not all(isinstance(x,str) and x for x in cfg['occ_command']):
        raise ValueError('occ_command must be a nonempty JSON array of arguments')
    users=cfg.get('allowed_users',[])
    if not isinstance(users,list) or not all(isinstance(x,str) and x for x in users):
        raise ValueError('allowed_users must be a JSON array of exact Nextcloud UIDs')
    cfg['allowed_users']=users
    cfg['owner_uid']=int(cfg.get('owner_uid',33));cfg['owner_gid']=int(cfg.get('owner_gid',33))
    if cfg['owner_uid']<0 or cfg['owner_gid']<0:raise ValueError('Invalid owner UID/GID')
    return cfg

def occ(cfg,*args):
    result=subprocess.run(cfg['occ_command']+list(args),capture_output=True,text=True)
    if result.returncode:raise RuntimeError('occ command failed: '+args[0]+'; inspect your Nextcloud logs (output withheld to protect secrets)')
    return result.stdout.strip()

def render_plugin(cfg):
    target=cfg['plugin_dir']
    if target.exists():raise RuntimeError('plugin_dir exists; refusing overwrite')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.mkdir(mode=0o755);target.chmod(0o755)
    for name in ('config.json','bridge.html','bridge.js'):
        text=(ROOT/'prototype-mobile/plugin'/name).read_text()
        if name=='bridge.html':text=text.replace('http://127.0.0.1:18780/sdkjs-plugins/v1/plugins.js','../v1/plugins.js')
        if name=='bridge.js':text=text.replace("'http://127.0.0.1:18781'",json.dumps(cfg['origin']))
        (target/name).write_text(text);(target/name).chmod(0o644)
    print('Plugin rendered:',target)
    print('Mount into Docs at /var/www/onlyoffice/documentserver/sdkjs-plugins/mobile-panel (read-only).')

def install_app(cfg):
    target=cfg['app_dir']
    if target.exists():raise RuntimeError('app_dir exists; refusing to overwrite an installed app')
    if not target.parent.is_dir():raise RuntimeError('app_dir parent must be an existing writable Nextcloud apps path')
    status=json.loads(occ(cfg,'status','--output=json'))
    if not status.get('installed') or not str(status.get('versionstring','')).startswith('35.') or status.get('maintenance') or status.get('needsDbUpgrade'):
        raise RuntimeError('Requires healthy Nextcloud 35 with no pending core upgrade')
    if occ(cfg,'config:app:get','onlyoffice','installed_version')!='10.2.1':
        raise RuntimeError('Requires enabled ONLYOFFICE connector 10.2.1')
    enabled=json.loads(occ(cfg,'app:list','--output=json')).get('enabled',{})
    if 'onlyoffice' not in enabled:raise RuntimeError('Enable/configure the ONLYOFFICE connector first')
    if not occ(cfg,'config:app:get','onlyoffice','jwt_secret'):
        raise RuntimeError('Connector JWT secret must be configured')
    # Do not modify core settings, original connector endpoints or proxy configuration.
    shutil.copytree(ROOT/'nextcloud-app/onlyoffice_mobile',target)
    for p in (target,*target.rglob('*')):
        if p.is_symlink():raise RuntimeError('Unexpected source symlink')
        os.chown(p,cfg['owner_uid'],cfg['owner_gid']);p.chmod(0o755 if p.is_dir() else 0o644)
    for key,value in [('docs_url',cfg['docs_url']),('docs_internal_url',cfg['docs_internal_url']),('allowed_users',json.dumps(cfg['allowed_users'])),('mobile_default','yes')]:
        occ(cfg,'config:app:set','onlyoffice_mobile',key,'--value='+value)
    occ(cfg,'app:enable','onlyoffice_mobile')
    print('App installed. Open '+cfg['nextcloud_url'].rstrip('/')+'/index.php/apps/onlyoffice_mobile/')
    print('Original connector endpoints and Docs were not changed. Test document copies before general use.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['check-config','render-plugin','install-app'])
    parser.add_argument('--config',type=Path,required=True)
    args=parser.parse_args();cfg=config(args.config)
    if args.action=='check-config':print('Configuration syntax OK; services, permissions and versions not checked.');return
    if os.geteuid()!=0:raise SystemExit('Run render-plugin/install-app as root on the host with the configured app/plugin paths')
    if args.action=='render-plugin':render_plugin(cfg)
    else:install_app(cfg)
if __name__=='__main__':main()
