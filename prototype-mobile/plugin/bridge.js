(function(){
 const ORIGIN='http://127.0.0.1:18781';let busy=false;
 window.Asc.plugin.init=function(){window.top.postMessage({type:'mobile-ready',kind:Asc.plugin.info.editorType},ORIGIN)};
 window.Asc.plugin.button=function(){};
 window.addEventListener('message',function(e){
  if(e.origin!==ORIGIN||e.source!==window.top||!e.data||e.data.type!=='mobile-command')return;
  const msg=e.data; const done=result=>{busy=false;window.top.postMessage({type:'mobile-result',id:msg.id,result},ORIGIN)};
  if(busy)return window.top.postMessage({type:'mobile-result',id:msg.id,result:{error:'Дождитесь завершения предыдущей операции'}},ORIGIN);
  const allowed=['snapshot','set','append','insert-column','delete-column','insert-row','delete-row','sheet'];
  if(!allowed.includes(msg.action))return done({error:'Недопустимая операция'});
  if(typeof msg.text!=='undefined'&&String(msg.text).length>10000)return done({error:'Слишком длинный текст'});
  if(['insert-column','delete-column','insert-row','delete-row','set'].includes(msg.action)&&Asc.plugin.info.editorType==='cell'&&!/^[A-Z]{1,3}[1-9][0-9]{0,6}$/.test(msg.cell||''))return done({error:'Некорректная ячейка'});
  busy=true;Asc.scope.req=msg;Asc.scope.kind=Asc.plugin.info.editorType;
  window.Asc.plugin.callCommand(function(){
   try{
    var q=Asc.scope.req;
    if(Asc.scope.kind==='word'){
     var doc=Api.GetDocument();
     if(q.action==='set'){
      var p=doc.GetAllParagraphs()[q.index];if(!p)throw new Error('Абзац не найден');
      if(q.expected!==undefined&&p.GetText()!==q.expected)throw new Error('Абзац изменился, обновите документ');
      p.RemoveAllElements();p.AddText(q.text);
     }else if(q.action==='append') {var p=Api.CreateParagraph();p.AddText(q.text);doc.Push(p);}
     else if(q.action!=='snapshot')throw new Error('Операция недоступна для Word');
     return {kind:'word',paragraphs:doc.GetAllParagraphs().map(function(p){return p.GetText()})};
    }
    var sheet=Api.GetActiveSheet();
    if(q.action==='sheet'){sheet=Api.GetSheets()[q.index];if(!sheet)throw new Error('Лист не найден');sheet.SetActive();}
    var range=q.cell?sheet.GetRange(q.cell):null;
    if(q.action==='set')range.SetValue(q.text);
    if(q.action==='insert-column')range.GetEntireColumn().Insert('right');
    if(q.action==='delete-column')range.GetEntireColumn().Delete('left');
    if(q.action==='insert-row')range.GetEntireRow().Insert('down');
    if(q.action==='delete-row')range.GetEntireRow().Delete('up');
    return {kind:'cell',sheet:sheet.GetName(),sheets:Api.GetSheets().map(function(s){return s.GetName()}),values:sheet.GetRange('A1:H20').GetValue()};
   }catch(e){return {error:e.message}}
  },false,msg.action!=='snapshot',done);
 });
})();
