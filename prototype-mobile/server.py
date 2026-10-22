import base64, hashlib, hmac, json, os, time, urllib.request, urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
ROOT=Path('/prototype'); DATA=Path('/prototype-data'); SECRET=os.environ['JWT_SECRET'].encode()
SESSIONS={}
DATA.mkdir(parents=True,exist_ok=True)
for name in ('sample.docx','sample.xlsx'):
 if not (DATA/name).exists():
  (DATA/name).write_bytes((Path('/var/www/onlyoffice/documentserver/document-templates/new/default')/name.replace('sample.','new.')).read_bytes())
GUID='asc.{9A38C060-94C7-4C39-B813-F5AA14661045}'
def jwt(data):
 def enc(v):return base64.urlsafe_b64encode(json.dumps(v,separators=(',',':')).encode()).rstrip(b'=')
 body=enc({'alg':'HS256','typ':'JWT'})+b'.'+enc(data)
 return (body+b'.'+base64.urlsafe_b64encode(hmac.new(SECRET,body,hashlib.sha256).digest()).rstrip(b'=')).decode()
def verify(token):
 a,b,c=token.split('.');expected=base64.urlsafe_b64encode(hmac.new(SECRET,(a+'.'+b).encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
 if not hmac.compare_digest(c,expected):raise ValueError('signature')
 return json.loads(base64.urlsafe_b64decode(b+'='*(-len(b)%4)))
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def send(self,data,kind='application/json',status=200):
  if not isinstance(data,bytes):data=json.dumps(data).encode()
  self.send_response(status);self.send_header('Access-Control-Allow-Origin','http://127.0.0.1:18780');self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  u=urllib.parse.urlsplit(self.path); q=urllib.parse.parse_qs(u.query);name=q.get('file',['sample.docx'])[0]
  if name not in ('sample.docx','sample.xlsx'):return self.send({'error':'file'},status=400)
  if u.path=='/revision':return self.send({'revision':(DATA/name).stat().st_mtime_ns})
  if u.path=='/config':
   ext=name.split('.')[-1]; key=hashlib.sha256((name+str((DATA/name).stat().st_mtime_ns)).encode()).hexdigest()[:40]
   cfg={'documentType':'word' if ext=='docx' else 'cell','type':'desktop','width':'100%','height':'100%',
   'document':{'fileType':ext,'key':key,'title':name,'url':'http://127.0.0.1:8090/files/'+name},
   'editorConfig':{'lang':'ru','mode':'edit','callbackUrl':'http://127.0.0.1:8090/callback?file='+name,'user':{'id':'local-prototype','name':'Prototype'},'customization':{'compactHeader':True,'compactToolbar':True},'plugins':{'autostart':[GUID],'pluginsData':['http://127.0.0.1:18781/plugin/config.json']}}}
   SESSIONS[name]=key
   cfg['token']=jwt(cfg);return self.send(cfg)
  if u.path.startswith('/files/'):
   f=DATA/u.path.rsplit('/',1)[-1]
   if f.name not in ('sample.docx','sample.xlsx'):return self.send({},status=404)
   return self.send(f.read_bytes(),'application/octet-stream')
  if u.path=='/':f=ROOT/'index.html'
  elif u.path.startswith('/plugin/') and '..' not in u.path:f=ROOT/u.path.lstrip('/')
  else:return self.send({},status=404)
  if not f.is_file():return self.send({},status=404)
  return self.send(f.read_bytes(),{'.html':'text/html','.js':'application/javascript','.json':'application/json'}.get(f.suffix,'text/plain'))
 def do_POST(self):
  try:
   u=urllib.parse.urlsplit(self.path)
   if u.path=='/save':
    name=urllib.parse.parse_qs(u.query).get('file',[''])[0]
    if name not in SESSIONS:return self.send({'error':'session'},status=400)
    command={'c':'forcesave','key':SESSIONS[name]};command['token']=jwt(command)
    request=urllib.request.Request('http://127.0.0.1/command',data=json.dumps(command).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=15) as r:reply=json.loads(r.read())
    return self.send(reply)
   if u.path!='/callback':return self.send({},status=404)
   n=int(self.headers.get('Content-Length','0'))
   if n>100000:return self.send({},status=413)
   data=json.loads(self.rfile.read(n));token=data.get('token')
   if not token:
    auth=self.headers.get('Authorization','');token=auth[7:] if auth.startswith('Bearer ') else ''
   signed=verify(token)
   # Outbox token may wrap the callback payload.
   payload=signed.get('payload',signed)
   if any(payload.get(k)!=data.get(k) for k in ('key','status','url')):raise ValueError('callback signature mismatch: '+','.join(k for k in ('key','status','url') if payload.get(k)!=data.get(k)))
   name=urllib.parse.parse_qs(u.query)['file'][0]
   if name not in ('sample.docx','sample.xlsx') or data.get('key')!=SESSIONS.get(name):raise ValueError('file session')
   if data.get('status') in (2,6):
    url=urllib.parse.urlsplit(data['url'])
    if url.scheme!='http' or url.hostname!='127.0.0.1' or url.port not in (80,18780) or not url.path.startswith('/cache/'):raise ValueError('download origin')
    with urllib.request.urlopen(data['url'],timeout=30) as r:content=r.read(30*1024*1024)
    tmp=DATA/(name+'.tmp');tmp.write_bytes(content);tmp.replace(DATA/name)
    with (DATA/'events.jsonl').open('a') as f:f.write(json.dumps({'file':name,'status':data['status'],'bytes':len(content)})+'\n')
   self.send({'error':0})
  except Exception as e:
   with (DATA/'events.jsonl').open('a') as f:f.write(json.dumps({'error':type(e).__name__,'detail':str(e)[:100]})+'\n')
   self.send({'error':1},status=400)
ThreadingHTTPServer(('0.0.0.0',8090),Handler).serve_forever()
