#!/usr/bin/env python3
"""Recreate the retired container using retained mounts; never extract over live data."""
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess

ROOT=Path(__file__).resolve().parents[1]
NAME='onlyoffice-document-server'
class DockerConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.connect('/var/run/docker.sock')

def main():
    if os.geteuid()!=0:raise SystemExit('Run as root on nc')
    state=json.loads((ROOT/'private/retired-onlyoffice/latest.json').read_text())
    info=json.loads((Path(state['snapshot'])/'container-inspect.private.json').read_text())
    present=subprocess.run(['docker','inspect',NAME],capture_output=True)
    if present.returncode==0:
        existing=json.loads(present.stdout)[0]
        if existing['Image']!=info['Image']:raise SystemExit('Refusing to replace an unexpected existing container')
    else:
        if subprocess.run(['docker','image','inspect',info['Image']],capture_output=True).returncode:
            subprocess.run(['docker','load','-i',state['saved_image']],check=True)
        for mount in info['Mounts']:
            if not Path(mount['Source']).exists():raise SystemExit('Retained mount missing; restore cold archive manually first')
        host=info['HostConfig'].copy()
        host.pop('Mounts',None)
        host['Binds']=[(m['Name'] if m['Type']=='volume' else m['Source'])+':'+m['Destination']+('' if m['RW'] else ':ro') for m in info['Mounts']]
        config=info['Config'].copy();config['Image']=info['Image'];config['HostConfig']=host
        connection=DockerConnection('localhost');connection.request('POST','/containers/create?name='+NAME,json.dumps(config),{'Content-Type':'application/json'})
        response=connection.getresponse();body=response.read();connection.close()
        if response.status!=201:raise SystemExit('Docker refused recreation (HTTP '+str(response.status)+'); private configuration retained')
    subprocess.run(['docker','start',NAME],check=True)
    settings=ROOT/'private/nc-mobile/state.json'
    if settings.exists():
        candidate=json.loads(settings.read_text())
        occ=['sudo','-u','www-data','php','/var/www/nextcloud/occ','config:app:set','onlyoffice']
        subprocess.run(occ+['DocumentServerUrl','--value='+candidate.get('before_switch_url',candidate['original_docs_url'])],check=True)
        if 'original_internal_url' in candidate:
            subprocess.run(occ+['DocumentServerInternalUrl','--value='+candidate['original_internal_url']],check=True)
    print('Original container started and recorded connector URLs restored. Retained data was not overwritten.')
if __name__=='__main__':main()
