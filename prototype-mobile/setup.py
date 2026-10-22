from pathlib import Path
import os
import secrets
root=Path(__file__).resolve().parent
(root/'data').mkdir(exist_ok=True)
p=root/'local.env'
if not p.exists():
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write('JWT_SECRET='+secrets.token_hex(32)+'\n')
print('Local environment ready. Secret is stored in local.env; do not share it.')
