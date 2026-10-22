#!/usr/bin/env python3
"""Update only the mobile UI assets, retaining private copies of installed files."""
from pathlib import Path
from datetime import datetime, timezone
import os
import shutil
import tempfile
import subprocess
import json
import argparse
ROOT=Path(__file__).resolve().parents[1]
APP=Path('/var/www/nextcloud/apps/onlyoffice_mobile')
FILES=['templates/editor.php','css/mobile.css','js/mobile.js','lib/AppInfo/Application.php','lib/Middleware/MobileOpeningMiddleware.php','appinfo/info.xml']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ui-only',action='store_true',help='Only UI assets; no occ upgrade or app version change');parser.add_argument('--config',type=Path,help='Portable installation JSON');args=parser.parse_args()
    app=APP
    occ=['sudo','-u','www-data','php','/var/www/nextcloud/occ']
    if args.config:
        if not args.ui_only:raise SystemExit('Portable updates require --ui-only; app version migrations must be reviewed separately')
        import importlib.util
        spec=importlib.util.spec_from_file_location('portable',ROOT/'scripts/install-mobile-app.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        cfg=module.config(args.config);app=cfg['app_dir'];occ=cfg['occ_command']
    files=FILES[:3] if args.ui_only else FILES
    if os.geteuid()!=0:raise SystemExit('Run as root on the host with access to the configured app directory')
    if not (app/'appinfo/info.xml').exists():raise SystemExit('Installed mobile app not found')
    status=json.loads(subprocess.run(occ+['status','--output=json'],check=True,capture_output=True,text=True).stdout)
    if status.get('maintenance') or status.get('needsDbUpgrade') or not str(status.get('versionstring','')).startswith('35.'):
        raise SystemExit('STOP: expected healthy Nextcloud 35 without a pending upgrade')
    for name in files:
        source=ROOT/'nextcloud-app/onlyoffice_mobile'/name
        if not source.is_file():raise SystemExit('Missing source file: '+name)
        if name.endswith('.php'):subprocess.run(['php','-l',str(source)],check=True)
    os.umask(0o077)
    backup=ROOT/'private'/('mobile-ui-before-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir(parents=True,mode=0o700)
    for name in files:
        target=app/name
        saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():shutil.copy2(target,saved)
    for name in files:
        target=app/name;old=app.stat()
        target.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
        os.chown(target.parent,old.st_uid,old.st_gid);target.parent.chmod(0o755)
        fd,temp=tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write((ROOT/'nextcloud-app/onlyoffice_mobile'/name).read_bytes())
            os.chown(temp,old.st_uid,old.st_gid);os.chmod(temp,0o644);os.replace(temp,target)
        finally:
            if Path(temp).exists():Path(temp).unlink()
    if not args.ui_only:subprocess.run(occ+['upgrade'],check=True)
    print('Mobile UI updated. Reload the page to load new assets. Previous UI:',backup)
if __name__=='__main__':main()
