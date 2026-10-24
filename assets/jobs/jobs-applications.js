(function(root){
  'use strict';
  var C=root.VfxJobsCore,esc=C.escapeHtml;
  var labels={applied:'Enviada',interview:'Entrevista',offer:'Oferta recibida',rejected:'Rechazada',withdrawn:'Retirada'};
  var records={},error='',writeError='',busy=false,listeners=[],epoch=0,version=0,lastSync='';
  var base='https://firestore.googleapis.com/v1/projects/portfolio-44b20/databases/(default)/documents/users/';
  function auth(){return root.VfxPrivateAuth;}
  function user(){return auth()&&auth().user;}
  function notify(){listeners.forEach(function(fn){fn();});}
  function message(e){return e.status===403?'Falta publicar las reglas privadas de candidaturas en Firebase (firestore.rules).':e.status===401?'La sesión ha caducado. Vuelve a iniciar sesión.':'No se pudo sincronizar. Comprueba la conexión y reintenta; el cambio no se ha confirmado.';}
  function fields(record){var out={};Object.keys(record).forEach(function(k){out[k]={stringValue:String(record[k])};});return out;}
  function decode(doc){var out={};Object.keys(doc.fields||{}).forEach(function(k){out[k]=doc.fields[k].stringValue||'';});return out;}
  async function request(path,options){
    var account=user();if(!account)throw new Error('Inicia sesión');
    var jwt=await auth().token();
    var response=await fetch(base+encodeURIComponent(account.uid)+'/applications'+path,Object.assign({},options,{headers:{Authorization:'Bearer '+jwt,'Content-Type':'application/json'}}));
    if(!response.ok){var e=new Error('No se pudo sincronizar');e.status=response.status;throw e;}
    return response.status===204?{}:response.json();
  }
  async function refresh(){
    if(!user())return;var current=epoch,currentVersion=version;
    try{
      var next={},page='';
      do{var data=await request('?pageSize=300'+(page?'&pageToken='+encodeURIComponent(page):''));(data.documents||[]).forEach(function(d){var r=decode(d);if(r.id)next[r.id]=r;});page=data.nextPageToken||'';}while(page);
      if(epoch!==current||version!==currentVersion)return;
      var changed=JSON.stringify(records)!==JSON.stringify(next)||!!error||!lastSync;
      records=next;error=writeError;lastSync=new Date().toISOString();if(changed)notify();
    }catch(e){if(epoch===current){error=message(e);notify();}}
  }
  async function save(job,status,changes){
    if(!user())throw new Error('Inicia sesión para sincronizar tus candidaturas.');
    if(!labels[status])throw new Error('Estado no válido');
    if(busy)throw new Error('Espera a que termine la sincronización anterior.');
    var current=epoch;version++;busy=true;error='';writeError='';notify();
    try{
      var old=records[job.id],now=new Date().toISOString();
      var record=old?Object.assign({},old):{id:job.id,company:String(job.company).slice(0,200),title:String(job.title).slice(0,300),url:C.safeUrl(job.url)||'',location:String(job.location||'').slice(0,500),status:status,appliedAt:now,updatedAt:now,notes:''};
      record.status=status;record.updatedAt=now;
      if(changes){if(typeof changes.notes==='string')record.notes=changes.notes.slice(0,2000);if(changes.appliedAt)record.appliedAt=changes.appliedAt;}
      // Update only edited fields on existing records, preserving changes from the other device.
      var patch=old?{status:status,updatedAt:now}:record;
      if(old&&changes){if(typeof changes.notes==='string')patch.notes=record.notes;if(changes.appliedAt)patch.appliedAt=record.appliedAt;}
      var mask=old?'?'+Object.keys(patch).map(function(k){return 'updateMask.fieldPaths='+k;}).join('&'):'';
      await request('/'+encodeURIComponent(job.id)+mask,{method:'PATCH',body:JSON.stringify({fields:fields(patch)})});
      if(epoch===current){records[job.id]=record;lastSync=now;}
    }catch(e){if(epoch===current){error=message(e);writeError=error;}throw new Error(message(e));}
    finally{if(epoch===current){busy=false;notify();}}
  }
  async function remove(id){
    if(!user()||busy||!records[id])return false;
    var current=epoch;version++;busy=true;error='';writeError='';notify();
    try{
      await request('/'+encodeURIComponent(id),{method:'DELETE'});
      if(epoch===current){delete records[id];lastSync=new Date().toISOString();}
      return true;
    }catch(e){if(epoch===current){error=message(e);writeError=error;}return false;}
    finally{if(epoch===current){busy=false;notify();}}
  }
  var applicationView='all',applicationDays='0';
  function mount(el){
    if(!user()){
      el.innerHTML='<h3>Mis candidaturas</h3><p>Inicia sesión con el mismo email y contraseña de Firebase que utilizas en la web. Tus candidaturas son privadas y se sincronizan con el móvil.</p><form data-app-login><label>Email<input type="email" name="email" autocomplete="username" required></label><label>Contraseña<input type="password" name="password" autocomplete="current-password" required></label><button class="jp-btn" type="submit">Iniciar sesión</button><p role="status" data-app-login-error></p></form>';
      el.querySelector('form').onsubmit=async function(e){e.preventDefault();var form=e.target,button=form.querySelector('button');button.disabled=true;try{await auth().signIn(form.email.value.trim(),form.password.value);form.password.value='';await refresh();notify();}catch(err){el.querySelector('[data-app-login-error]').textContent='No se pudo iniciar sesión. Comprueba el email y la contraseña.';}finally{button.disabled=false;}};
      return;
    }
    var list=Object.keys(records).map(function(id){return records[id];}).filter(function(r){var closed=['rejected','withdrawn'].indexOf(r.status)>=0;if(applicationView==='active'&&closed||applicationView==='closed'&&!closed)return false;var age=Date.now()-Date.parse(r.appliedAt);return applicationDays==='0'||age>=0&&age<Number(applicationDays)*86400000;}).sort(function(a,b){return b.appliedAt.localeCompare(a.appliedAt);});
    el.innerHTML='<h3>Mis candidaturas</h3><p>Cuenta: '+esc(user().email||'Administrador')+' · '+list.length+' candidaturas privadas</p><div class="jp-actions"><button class="jp-btn" data-app-refresh>Sincronizar ahora</button><button class="jp-btn" data-app-logout>Cerrar sesión</button></div>'+(error?'<p class="jp-warn" role="alert">'+esc(error)+'</p>':'<p role="status">'+(busy?'Guardando…':lastSync?'Sincronizado '+esc(C.timeAgo(lastSync)):'Conectando con Firebase…')+'</p>')+
      '<details><summary>Añadir una candidatura que ya enviaste</summary><form data-app-manual><label>Empresa<input name="company" maxlength="200" required></label><label>Puesto<input name="title" maxlength="300" required></label><label>Enlace (opcional)<input name="url" type="url"></label><label>Fecha de envío<input name="date" type="date" required value="'+new Date().toISOString().slice(0,10)+'"></label><button class="jp-btn" type="submit" '+(busy?'disabled':'')+'>Guardar candidatura</button></form></details>'+
      '<div class="jp-actions"><label>Seguimiento<select data-app-view><option value="all">Todas</option><option value="active">En seguimiento</option><option value="closed">Cerradas</option></select></label><label>Fecha de envío<select data-app-days><option value="0">Cualquier fecha</option><option value="7">Última semana</option><option value="30">Último mes</option></select></label></div>'+
      (list.length?'<ul class="jp-colist">'+list.map(function(r){return '<li class="jp-co"><h4>'+esc(r.title)+'</h4><p>'+esc(r.company)+' · Enviada '+esc(C.formatDate(r.appliedAt))+'</p><label>Estado<select data-app-status="'+esc(r.id)+'" '+(busy?'disabled':'')+'>'+Object.keys(labels).map(function(s){return '<option value="'+s+'" '+(r.status===s?'selected':'')+'>'+labels[s]+'</option>';}).join('')+'</select></label>'+(C.safeUrl(r.url)?'<p><a href="'+esc(C.safeUrl(r.url))+'" target="_blank" rel="noopener noreferrer">Abrir oferta ↗</a></p>':'')+'<details><summary>Notas privadas</summary><form data-app-notes="'+esc(r.id)+'"><textarea name="notes" maxlength="2000" aria-label="Notas privadas">'+esc(r.notes)+'</textarea><button class="jp-btn" '+(busy?'disabled':'')+'>Guardar notas</button></form></details><button class="jp-btn" data-app-delete="'+esc(r.id)+'" '+(busy?'disabled':'')+'>Eliminar candidatura</button></li>';}).join('')+'</ul>':'<p>Aún no has marcado candidaturas. Usa «He enviado mi candidatura» en una oferta o añade una anterior.</p>');
    el.querySelector('[data-app-view]').value=applicationView;
    el.querySelector('[data-app-days]').value=applicationDays;
    el.querySelector('[data-app-view]').onchange=function(e){applicationView=e.target.value;mount(el);};
    el.querySelector('[data-app-days]').onchange=function(e){applicationDays=e.target.value;mount(el);};
    el.querySelector('[data-app-refresh]').onclick=refresh;
    el.querySelector('[data-app-logout]').onclick=function(){auth().signOut();};
    el.querySelectorAll('[data-app-status]').forEach(function(select){select.onchange=function(){var r=records[select.dataset.appStatus];save(r,select.value).catch(function(){});};});
    el.querySelectorAll('[data-app-delete]').forEach(function(button){button.onclick=function(){if(root.confirm('¿Eliminar esta candidatura del móvil y la web? No retira el CV enviado. Puedes conservar el historial cambiando el estado a Retirada o Rechazada.'))remove(button.dataset.appDelete);};});
    el.querySelectorAll('[data-app-notes]').forEach(function(form){form.onsubmit=function(e){e.preventDefault();var r=records[form.dataset.appNotes];save(r,r.status,{notes:form.notes.value}).catch(function(){});};});
    el.querySelector('[data-app-manual]').onsubmit=function(e){e.preventDefault();var f=e.target;save({id:'manual-'+Date.now()+'-'+Math.random().toString(36).slice(2,9),company:f.elements.namedItem('company').value,title:f.elements.namedItem('title').value,url:f.elements.namedItem('url').value,location:''},'applied',{appliedAt:new Date(f.elements.namedItem('date').value+'T12:00:00Z').toISOString()}).catch(function(){});};
  }
  root.addEventListener('vfx-auth-change',function(){epoch++;version++;records={};error='';writeError='';busy=false;lastSync='';notify();if(user())refresh();});
  root.addEventListener('focus',function(){if(user())refresh();});
  setInterval(function(){if(user()&&!document.hidden&&!busy)refresh();},15000);
  root.VfxApplications={mount:mount,save:save,remove:remove,refresh:refresh,labels:labels,get:function(id){return records[id];},subscribe:function(fn){listeners.push(fn);}};
})(window);
