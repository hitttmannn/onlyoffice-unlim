const settings=document.querySelector('#mobile-settings').dataset;const ORIGIN=new URL(settings.docsUrl).origin, $=s=>document.querySelector(s);let bridge,model,sequence=0,pending=new Map(),selection={index:0,cell:'A1'},unsaved=false;
const state=s=>$('#status').textContent=s;
function send(action,extra={}){if(!bridge)return Promise.reject(Error('Редактор ещё не готов'));document.body.classList.add('busy');return new Promise((resolve,reject)=>{const id=++sequence;const timer=setTimeout(()=>{pending.delete(id);document.body.classList.remove('busy');reject(Error('Нет ответа редактора'))},15000);pending.set(id,{resolve,reject,timer});bridge.postMessage({type:'mobile-command',id,action,...selection,...extra},ORIGIN)})}
function choose(index,cell,text){selection={index,cell};$('#value').value=text||'';$('#selection').textContent=model.kind==='word'?'Абзац '+(index+1):'Ячейка '+cell}
function render(m){const changedSheet=model&&model.kind==='cell'&&m.kind==='cell'&&model.sheet!==m.sheet;model=m;$('#sheet-picker').hidden=m.kind!=='cell';if(changedSheet){selection={index:0,cell:'A1'};$('#value').value='';$('#selection').textContent='Выберите ячейку на листе «'+m.sheet+'»'};const container=$('#oo-content');container.replaceChildren();$('#append').hidden=m.kind!=='word';$('#structure').hidden=m.kind!=='cell';if(m.kind==='word'){m.paragraphs.forEach((text,i)=>{const b=document.createElement('button');b.className='para';b.textContent=text.trim()||'Пустой абзац';b.onclick=()=>choose(i,'A1',text);container.append(b)})}else{const select=$('#sheet-select');select.title=m.sheet;select.replaceChildren();m.sheets.forEach((name,i)=>{const o=new Option(name,String(i),name===m.sheet,name===m.sheet);select.add(o)});select.onchange=()=>run('sheet',{index:Number(select.value)});$('#sheet-count').textContent='Лист '+(m.sheets.indexOf(m.sheet)+1)+' из '+m.sheets.length;const grid=document.createElement('div');grid.className='grid';const table=document.createElement('table');m.values.forEach((row,r)=>{const tr=document.createElement('tr');row.forEach((value,c)=>{const td=document.createElement('td');td.textContent=String(value);td.dataset.cell=String.fromCharCode(65+c)+(r+1);td.onclick=()=>{container.querySelectorAll('.selected').forEach(x=>x.classList.remove('selected'));td.classList.add('selected');choose(0,td.dataset.cell,String(value))};tr.append(td)});table.append(tr)});grid.append(table);container.append(grid)}}
async function run(action,extra={}){try{const result=await send(action,extra);if(result.error)throw Error(result.error);if(!['snapshot','sheet'].includes(action)){unsaved=true;const fresh=await send('snapshot');if(fresh.error)throw Error(fresh.error);render(fresh)}else render(result);state(unsaved?'Изменения в редакторе. Нажмите «Сохранить файл».':'Документ открыт')}catch(e){state('Ошибка: '+e.message)}}
window.addEventListener('message',e=>{if(e.origin!==ORIGIN||!e.data)return;if(e.data.type==='mobile-ready'){if(bridge&&bridge!==e.source)return;bridge=e.source;run('snapshot')}if(e.source===bridge&&e.data.type==='mobile-result'){const p=pending.get(e.data.id);if(p){clearTimeout(p.timer);pending.delete(e.data.id);document.body.classList.remove('busy');p.resolve(e.data.result||{error:'Пустой ответ SDK'})}}});
$('#refresh').onclick=()=>run('snapshot');$('#apply').onclick=()=>run('set',{text:$('#value').value,...(model.kind==='word'?{expected:model.paragraphs[selection.index]}:{})});$('#append').onclick=()=>run('append',{text:$('#value').value});document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>{if(b.dataset.action.startsWith('delete')&&!confirm('Удалить целиком выбранную строку или столбец?'))return;run(b.dataset.action)});
$('#save').onclick=async()=>{if(!unsaved){state('Изменений для сохранения нет');return}try{state('Запрошено сохранение…');const before=await fetch(settings.revisionUrl).then(r=>r.json());let data;for(let attempt=0;attempt<20;attempt++){await new Promise(r=>setTimeout(r,1000));data=await fetch(settings.saveUrl,{method:'POST',headers:{requesttoken:OC.requestToken}}).then(r=>r.json());if(data.error!==4)break}if(data.error)throw Error('Сервер: '+data.error);let saved=false;for(let i=0;i<30;i++){await new Promise(r=>setTimeout(r,1000));const after=await fetch(settings.revisionUrl).then(r=>r.json());if(after.revision!==before.revision){saved=true;break}}if(!saved)throw Error('Подтверждение записи не получено');unsaved=false;state('Файл сохранён')}catch(e){state('Ошибка сохранения: '+e.message)}};
window.addEventListener('beforeunload',e=>{if(unsaved){e.preventDefault();e.returnValue=''}});
fetch(settings.configUrl).then(r=>r.json()).then(config=>{
 if(config.error)throw Error(config.error);
 const script=document.createElement('script');script.src=settings.docsUrl+'web-apps/apps/api/documents/api.js';
 script.onload=()=>{config.events={onError:e=>state('Ошибка редактора: '+e.data.errorCode)};window.editor=new DocsAPI.DocEditor('engine',config)};
 script.onerror=()=>state('Не удалось загрузить ONLYOFFICE');document.head.append(script);
}).catch(e=>state(e.message));

// Keep browser pinch zoom available and scale document content independently of controls.
const viewport=document.querySelector('meta[name="viewport"]');
if(viewport){viewport.content=viewport.content.split(',').filter(part=>!/^\s*(maximum-scale|minimum-scale|user-scalable)\s*=/i.test(part)).join(',')+', user-scalable=yes';}
let documentZoom=100;
function setDocumentZoom(value){
 documentZoom=Math.max(50,Math.min(200,value));
 $('#oo-content').style.setProperty('--oo-document-zoom',documentZoom/100);
 $('#zoom-level').textContent=documentZoom+'%';
 $('#zoom-out').disabled=documentZoom===50;$('#zoom-in').disabled=documentZoom===200;
}
$('#zoom-out').onclick=()=>setDocumentZoom(documentZoom-10);
$('#zoom-in').onclick=()=>setDocumentZoom(documentZoom+10);
$('#zoom-reset').onclick=()=>setDocumentZoom(100);
