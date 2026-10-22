"""Exercise preparation/activation with fake commands and temporary files only."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

SOURCE=Path(__file__).resolve().parents[1]

class InstallerTests(unittest.TestCase):
    def scenario(self,fail=False,retired=False):
        spec=importlib.util.spec_from_file_location('installer',SOURCE/'scripts/nc-mobile-install.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        m.ROOT=Path(tmp.name);m.NC=m.ROOT/'nc';(m.NC/'apps/onlyoffice/appinfo').mkdir(parents=True)
        (m.NC/'apps/onlyoffice/appinfo/info.xml').write_text('<info><version>10.2.1</version></info>')
        m.PRIVATE=m.ROOT/'private/nc-mobile';m.APP=m.NC/'apps/onlyoffice_mobile'
        m.VHOST=m.ROOT/'default-ssl.conf';m.VHOST.write_text('<VirtualHost *:65443>\nDocumentRoot /nextcloud\n</VirtualHost>\n')
        m.PROXY=m.ROOT/'mobile-proxy.conf'
        shutil.copytree(SOURCE/'prototype-mobile/plugin',m.ROOT/'prototype-mobile/plugin')
        events=[]
        def output(args):
            events.append(args)
            if 'status' in args:return json.dumps({'versionstring':'35.0.2','maintenance':False,'needsDbUpgrade':False})
            if 'jwt_secret' in args:return "test$secret'quoted"
            if 'jwt_header' in args:return 'Authorization'
            if 'DocumentServerUrl' in args:return 'https://old.example/'
            if 'inspect' in args:return 'true'
            return ''
        m.output=output;m.call=lambda args:events.append(args);m.health=lambda *args:None
        m.copy_app=lambda:m.APP.mkdir()
        original_run=m.subprocess.run
        if retired:
            record=m.ROOT/'private/retired-onlyoffice/latest.json'
            record.parent.mkdir(parents=True);record.write_text(json.dumps({'phase':'removed'}))
        def fake_run(args,**kw):
            if retired and 'inspect' in args:return SimpleNamespace(returncode=1,stdout='',stderr='')
            return SimpleNamespace(returncode=0,stdout="true\n" if "inspect" in args else "Authorization\n" if "jwt_header" in args else "",stderr="")
        m.subprocess.run=fake_run
        self.addCleanup(setattr,m.subprocess,"run",original_run)
        m.prepare()
        self.assertEqual((m.PRIVATE/'plugin').stat().st_mode&0o777,0o755)
        self.assertEqual((m.PRIVATE/'candidate.env').stat().st_mode&0o777,0o600)
        self.assertIn("JWT_SECRET='test$secret\\'quoted'",(m.PRIVATE/'candidate.env').read_text())
        with self.assertRaises(RuntimeError):m.prepare()
        count=[0]
        def configtest():
            count[0]+=1
            if fail and count[0]==1:raise RuntimeError('simulated config error')
        m.configtest=configtest
        try:
            if fail:
                with self.assertRaises(RuntimeError):m.activate()
                self.assertNotIn(m.INCLUDE,m.VHOST.read_text());self.assertFalse(m.PROXY.exists())
            else:
                m.activate()
                self.assertIn(m.INCLUDE,m.VHOST.read_text())
                self.assertEqual(json.loads((m.PRIVATE/'state.json').read_text())['phase'],'active-test')
        finally:pass
        self.assertFalse(any('rm' in e or 'stop' in e for e in events))
        writes=[e for e in events if 'config:app:set' in e]
        self.assertTrue(all('onlyoffice_mobile' in e for e in writes))
        if not fail:
            m.switch()
            self.assertEqual(json.loads((m.PRIVATE/'state.json').read_text())['phase'],'switched')
            standard=[e for e in events if 'config:app:set' in e and 'onlyoffice' in e]
            self.assertEqual({e[e.index('onlyoffice')+1] for e in standard},{'DocumentServerUrl','DocumentServerInternalUrl'})
    def test_prepare_and_activate(self):self.scenario()
    def test_prepare_after_old_container_removed(self):self.scenario(retired=True)
    def test_configtest_failure_removes_own_route(self):self.scenario(fail=True)

if __name__=='__main__':unittest.main()
