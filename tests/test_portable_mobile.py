"""Portable installation uses only temp files and mocked occ/ownership calls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('portable',ROOT/'scripts/install-mobile-app.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

class PortableTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.base=Path(temp.name);(self.base/'apps').mkdir()
        self.path=self.base/'config.json'
        self.raw=json.loads((ROOT/'deployment/mobile.example.json').read_text())
        self.raw.update(nextcloud_url='https://other.example:9443/nextcloud',
            docs_url='https://office.example/editors/',docs_internal_url='http://docs:80/',
            app_dir=str(self.base/'apps/onlyoffice_mobile'),plugin_dir=str(self.base/'plugin'),
            occ_command=['docker','exec','-u','33','my-cloud','php','/var/www/html/occ'],allowed_users=['alice'])
        self.path.write_text(json.dumps(self.raw));self.cfg=M.config(self.path)

    def test_default_https_origin_is_canonical(self):
        self.assertEqual(M.url('https://CLOUD.example:443/nextcloud',origin=True),'https://cloud.example')
        self.assertEqual(M.url('https://[::1]:9443/cloud',origin=True),'https://[::1]:9443')

    def test_origin_and_portable_plugin(self):
        self.assertEqual(self.cfg['origin'],'https://other.example:9443')
        M.render_plugin(self.cfg)
        plugin=self.cfg['plugin_dir'];bridge=(plugin/'bridge.js').read_text()
        self.assertIn('https://other.example:9443',bridge)
        self.assertNotIn('127.0.0.1:18781',bridge)
        self.assertIn('../v1/plugins.js',(plugin/'bridge.html').read_text())
        self.assertEqual(plugin.stat().st_mode&0o777,0o755)
        with self.assertRaises(RuntimeError):M.render_plugin(self.cfg)

    def fake_occ(self,cfg,*args):
        self.calls.append(args)
        values={'status':json.dumps({'installed':True,'versionstring':self.version,'maintenance':False,'needsDbUpgrade':False}),
                'app:list':json.dumps({'enabled':{'onlyoffice':'10.2.1'}})}
        if args[0] in values:return values[args[0]]
        if args[0]=='config:app:get':return '10.2.1' if args[2]=='installed_version' else 'dummy-secret-never-published'
        return ''

    def test_install_no_global_upgrade_or_connector_writes(self):
        self.calls=[];self.version='35.0.2'
        with patch.object(M,'occ',side_effect=self.fake_occ),patch.object(M.os,'chown'):
            M.install_app(self.cfg)
            with self.assertRaises(RuntimeError):M.install_app(self.cfg)
        self.assertTrue((self.cfg['app_dir']/'appinfo/info.xml').exists())
        writes=[args for args in self.calls if args[0]=='config:app:set']
        self.assertEqual(len(writes),4)
        self.assertTrue(all(args[1]=='onlyoffice_mobile' for args in writes))
        self.assertIn(('app:enable','onlyoffice_mobile'),self.calls)
        self.assertFalse(any(args[0]=='upgrade' for args in self.calls))

    def test_other_nextcloud_version_is_rejected_before_copy(self):
        self.calls=[];self.version='34.0.0'
        with patch.object(M,'occ',side_effect=self.fake_occ):
            with self.assertRaises(RuntimeError):M.install_app(self.cfg)
        self.assertFalse(self.cfg['app_dir'].exists())

    def test_invalid_url_and_relative_app_path_are_rejected(self):
        for key,value in [('nextcloud_url','http://cloud.example'),('docs_url','https://user:password@docs.example/'),('app_dir','relative/onlyoffice_mobile')]:
            raw=self.raw|{key:value};self.path.write_text(json.dumps(raw))
            with self.subTest(key=key),self.assertRaises(ValueError):M.config(self.path)

if __name__=='__main__':unittest.main()
