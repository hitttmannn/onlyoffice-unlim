#!/usr/bin/env python3
"""Read-only production inventory and private recovery material, not a live DB backup."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

NAME='onlyoffice-document-server'
NC=Path('/var/www/nextcloud')
ROOT=Path(__file__).resolve().parents[1]

def run(args):
    return subprocess.run(args,check=True,capture_output=True,text=True).stdout

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--save-image',action='store_true',help='Also save old image tar (requires extra disk space)')
    args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('Run on nc as root; collected configuration contains secrets')
    os.umask(0o077)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    parent=ROOT/'private'
    if parent.is_symlink():raise SystemExit('STOP: private is a symlink')
    parent.mkdir(exist_ok=True,mode=0o700);parent.chmod(0o700)
    target=parent/('production-preparation-'+stamp)
    target.mkdir(mode=0o700)
    info=json.loads(run(['docker','inspect',NAME]))
    if len(info)!=1 or info[0].get('Name')!='/'+NAME:raise SystemExit('STOP: unexpected container identity')
    container=info[0]
    (target/'container-inspect.private.json').write_text(json.dumps(info,indent=2))
    image=container['Image']
    image_meta=json.loads(run(['docker','image','inspect',image]))
    (target/'image-inspect.private.json').write_text(json.dumps(image_meta,indent=2))
    occ=['sudo','-u','www-data','php',str(NC/'occ')]
    (target/'nextcloud-status.json').write_text(run(occ+['status','--output=json']))
    (target/'onlyoffice-app-config.private.json').write_text(run(occ+['config:list','onlyoffice','--private']))
    app=NC/'apps/onlyoffice'
    version=ET.parse(app/'appinfo/info.xml').getroot().findtext('version')
    shutil.copytree(app,target/'onlyoffice-app-original',symlinks=True)
    shutil.copytree(NC/'config',target/'nextcloud-config-private',symlinks=True)
    summary={'container':NAME,'image':image,'connector_version':version,
             'state':container['State']['Status'],'mounts':[],
             'warning':'LIVE CONFIG SNAPSHOT ONLY. Database/volume consistency and restore are NOT verified.'}
    for mount in container.get('Mounts',[]):
        row={k:mount.get(k) for k in ('Type','Name','Source','Destination') if mount.get(k) is not None}
        row['allocated_kib']=int(run(['du','-sk','--',mount['Source']]).split()[0])
        summary['mounts'].append(row)
    docker_root=run(['docker','info','--format','{{.DockerRootDir}}']).strip()
    summary['free_project_bytes']=shutil.disk_usage(ROOT).free
    summary['free_docker_bytes']=shutil.disk_usage(docker_root).free
    if args.save_image:
        expected=image_meta[0].get('Size',0)
        if shutil.disk_usage(target).free<expected+1024**3:raise SystemExit('STOP: not enough room to save old image')
        subprocess.run(['docker','image','save','-o',str(target/'onlyoffice-9.2.1-image.tar'),image],check=True)
        import hashlib
        h=hashlib.sha256()
        with (target/'onlyoffice-9.2.1-image.tar').open('rb') as stream:
            while block:=stream.read(1024*1024):h.update(block)
        (target/'image.sha256').write_text(h.hexdigest()+'  onlyoffice-9.2.1-image.tar\n')
        summary['saved_image']=True
    (target/'summary-shareable.json').write_text(json.dumps(summary,indent=2))
    (target/'README.txt').write_text('Private recovery material; contains passwords/JWT/config. Do not upload.\nThis is NOT a consistent database/volume backup. Production was not stopped.\n')
    print(json.dumps(summary,indent=2))
    print('Private recovery material saved at:',target)
    print('Share ONLY the summary printed above. Do not send the private directory.')

if __name__=='__main__':main()
