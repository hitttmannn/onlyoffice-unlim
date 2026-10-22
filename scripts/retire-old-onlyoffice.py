#!/usr/bin/env python3
"""Stop, cold-archive mounted Docs data, then remove ONLY the old container (never -v)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
NAME='onlyoffice-document-server'
EXPECTED='sha256:162eed1e2e272eda5d08b5ed3d7a3556b8d21b5911f26e8d343ca315abcd0b88'

def run(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout

def main():
    if os.geteuid()!=0:raise SystemExit('Run as root on nc')
    os.umask(0o077)
    info=json.loads(run(['docker','inspect',NAME]))[0]
    if info['Name']!='/'+NAME or info['Image']!=EXPECTED:
        raise SystemExit('STOP: old container identity differs from the recorded nc container')
    # These files were already created by the user; no image or mount gets deleted.
    preparations=list((ROOT/'private').glob('production-preparation-*/onlyoffice-9.2.1-image.tar'))
    if not preparations:raise SystemExit('STOP: saved old image tar was not found')
    parent=ROOT/'private/retired-onlyoffice';parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    target=parent/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');target.mkdir(mode=0o700)
    (target/'container-inspect.private.json').write_text(json.dumps(info,indent=2))
    paths=[]
    for m in info.get('Mounts',[]):
        source=m['Source']
        if not (source.startswith('/app/onlyoffice/DocumentServer/') or source.startswith('/var/lib/docker/volumes/')):
            raise SystemExit('STOP: unexpected mount source; container was not stopped')
        paths.append(source.lstrip('/'))
    if not paths:raise SystemExit('STOP: no mounts recorded')
    allocated=sum(int(run(['du','-sk','/'+p]).split()[0])*1024 for p in paths)
    if shutil.disk_usage(target).free < allocated*2+1024**3:
        raise SystemExit('STOP: insufficient free space for cold data archive')
    was_running=info['State']['Running']
    try:
        if was_running:
            print('Stopping old Docs. Its standard editor is unavailable until the new endpoint is activated.',flush=True)
            subprocess.run(['docker','stop','--time','60',NAME],check=True)
        archive=target/'mounted-data-cold.tar'
        subprocess.run(['tar','--sparse','--acls','--xattrs','--numeric-owner','-cpf',str(archive),'-C','/',*paths],check=True)
        h=hashlib.sha256()
        with archive.open('rb') as f:
            while block:=f.read(1024*1024):h.update(block)
        (target/'data.sha256').write_text(h.hexdigest()+'  mounted-data-cold.tar\n')
        (target/'mounts.private.json').write_text(json.dumps(info['Mounts'],indent=2))
        # No -v, no image/volume removal, no prune.
        subprocess.run(['docker','rm',NAME],check=True)
        state={'phase':'removed','image':info['Image'],'snapshot':str(target),'saved_image':str(preparations[-1])}
        (parent/'latest.json').write_text(json.dumps(state,indent=2))
    except Exception:
        # Keep service recoverable when archive creation fails.
        present=subprocess.run(['docker','inspect',NAME],capture_output=True).returncode==0
        if present and was_running:subprocess.run(['docker','start',NAME],check=False)
        raise
    print('Old container removed. All volumes, bind directories and image are retained.')
    print('Cold data archive and private container configuration:',target)
    print('Do not share this private folder. Continue with nc-mobile-install.py prepare.')

if __name__=='__main__':main()
