(function (root) {
  'use strict';
  var seq = 0;
  function project(p) { return {x:(Number(p.lon)+180)/360*1000,y:(90-Number(p.lat))/180*500}; }
  // Group in screen space: markers stay readable at every zoom level.
  function clusters(points, radius) {
    var groups=[];
    points.forEach(function(p) {
      var group=groups.find(function(g) { return Math.hypot(g.x-p.x,g.y-p.y)<radius; });
      if(!group) { groups.push({x:p.x,y:p.y,points:[p]}); return; }
      group.points.push(p);
      group.x=group.points.reduce(function(n,a){return n+a.x;},0)/group.points.length;
      group.y=group.points.reduce(function(n,a){return n+a.y;},0)/group.points.length;
    });
    return groups;
  }
  function mount(el, data, jobs, config) {
    var C=root.VfxJobsCore, esc=C.escapeHtml, id='company-map-'+(++seq);
    var located=data.locations.companies.filter(function(c){return c.locations.length;});
    var missing=data.locations.companies.filter(function(c){return !c.locations.length;});
    var selected='', query='', zoom=1, tx=0, ty=0, width=0, height=0, base=1, groups=[];
    var pointers=new Map(), gesture=null, moved=false, resizeObserver;
    var byName={}; config.forEach(function(c){byName[c.name]=c;});
    var paths=data.world.polygons.map(function(poly){return '<path d="M'+poly.map(function(p){return Number(p[0])+','+Number(p[1]);}).join('L')+'Z"/>';}).join('');
    el.innerHTML='<div class="ji-controls"><label>Buscar empresa o ciudad<input type="search" data-map-search placeholder="Por ejemplo: Hexworks, Barcelona…"></label><label>Empresa<select data-map-company><option value="">Todas las empresas</option>'+located.slice().sort(function(a,b){return a.name.localeCompare(b.name);}).map(function(c){return '<option>'+esc(c.name)+'</option>';}).join('')+'</select></label><button class="jp-btn" data-map-reset>Ver todo el mundo</button></div>'+
      '<p class="ji-map-help">Morado: varias empresas · Verde: una empresa. El punto verde abre su ubicación sin mover el mapa. Arrastra para explorar y usa rueda o pellizco para ampliar. También puedes usar las flechas y las teclas + y −.</p>'+
      '<div class="ji-map-layout"><div class="ji-map-stage"><div class="ji-map-surface" tabindex="0" role="region" aria-label="Mapa interactivo de empresas"><svg data-map-svg role="group" aria-label="Empresas agrupadas por ubicación"></svg></div><div class="ji-map-tools"><button class="jp-btn" data-map-zoom="1" aria-label="Ampliar mapa">+</button><button class="jp-btn" data-map-zoom="-1" aria-label="Reducir mapa">−</button></div><span class="ji-map-scale" data-map-scale></span></div><div class="ji-map-selection" id="'+id+'" data-map-detail aria-live="polite"></div></div>'+
      '<p>'+located.length+' empresas localizadas · '+missing.length+' sin ubicación verificada.</p><details><summary>Sin ubicación verificada</summary><p>'+missing.map(function(c){return esc(c.name);}).join(' · ')+'</p></details>';
    var surface=el.querySelector('.ji-map-surface'), svg=el.querySelector('[data-map-svg]'), panel=el.querySelector('[data-map-detail]');
    function matching() {
      return located.filter(function(c){return (!selected||selected===c.name)&&(!query||(c.name+' '+c.locations.map(function(p){return p.city;}).join(' ')).toLocaleLowerCase().includes(query));});
    }
    function companyJobs(c) {
      return jobs.filter(function(j){return j.company===c.name&&j.status==='active'&&!j.viaAggregator&&!/^(az-|sig-)/.test(j.id);});
    }
    function showCompanies(list, title) {
      var unique={}; list.forEach(function(c){unique[c.name]=c;});
      list=Object.keys(unique).sort().map(function(n){return unique[n];});
      panel.innerHTML='<h4>'+esc(title)+'</h4><p>'+list.length+' empresa'+(list.length===1?'':'s')+'</p>'+ (list.length?'<ul class="ji-map-results">'+list.map(function(c){var offers=companyJobs(c);return '<li><button class="ji-company-pick" data-pick-company="'+esc(c.name)+'"><strong>'+esc(c.name)+'</strong><span>'+esc(c.locations.map(function(p){return p.city;}).filter(function(p,i,a){return a.indexOf(p)===i;}).join(' · '))+'</span><span>'+offers.length+' ofertas VFX activas</span></button></li>';}).join('')+'</ul>':'<p>No hay empresas que coincidan.</p>');
    }
    function showCompany(c, locations) {
      locations=locations||c.locations;
      var cfg=byName[c.name]||byName[c.sharedSource]||{}, offers=companyJobs(c), url=C.safeUrl(cfg.careersUrl);
      panel.innerHTML='<h4>'+esc(c.name)+'</h4><p>'+esc(locations.map(function(p){return p.city;}).join(' · '))+'</p><button class="jp-btn" data-show-offices="'+esc(c.name)+'">Ver todas sus sedes</button>'+(c.sharedSource?'<p>Portal compartido con '+esc(c.sharedSource)+'</p>':'')+'<p><strong>'+offers.length+'</strong> ofertas VFX activas</p>'+ (url?'<a class="jp-btn" href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">Portal de empleo ↗</a>':'')+'<ul class="ji-map-results">'+offers.map(function(j){var u=C.safeUrl(j.url);return u?'<li><a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+esc(j.title)+'</a></li>':'';}).join('')+'</ul><details><summary>Fuente de las ubicaciones</summary>'+locations.map(function(p){var u=C.safeUrl(p.evidence);return u?'<p><a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+esc(p.city)+' ↗</a></p>':'';}).join('')+'</details>';
    }
    function limitPan() {
      var scale=base*zoom, mapWidth=1000*scale, mapHeight=500*scale;
      tx=mapWidth<=width?(width-mapWidth)/2:Math.max(width-mapWidth-40,Math.min(40,tx));
      ty=mapHeight<=height?(height-mapHeight)/2:Math.max(height-mapHeight-40,Math.min(40,ty));
    }
    function draw() {
      limitPan();
      var scale=base*zoom, points=[];
      matching().forEach(function(c){c.locations.forEach(function(p){var point=project(p);points.push({x:point.x*scale+tx,y:point.y*scale+ty,company:c,location:p,world:point});});});
      groups=clusters(points,44);
      svg.setAttribute('viewBox','0 0 '+width+' '+height);
      svg.innerHTML='<g transform="translate('+tx+' '+ty+') scale('+scale+')" fill="#263c52" stroke="#49667f" stroke-width="'+(.5/scale)+'">'+paths+'</g>'+groups.filter(function(g){return g.x>-25&&g.y>-25&&g.x<width+25&&g.y<height+25;}).map(function(g){var i=groups.indexOf(g), names=Array.from(new Set(g.points.map(function(p){return p.company.name;}))), count=names.length, label=count===1?names[0]:count+' empresas';return '<g role="button" tabindex="0" data-map-cluster="'+i+'" aria-label="'+esc(label)+'" aria-controls="'+id+'" transform="translate('+g.x+' '+g.y+')"><title>'+esc(names.join(', '))+'</title><circle r="'+(count>1?19:13)+'" fill="'+(count>1?'#a997ff':'#69e2ce')+'" stroke="#101b2c" stroke-width="3"/><circle r="23" fill="transparent"/>'+ (count>1?'<text text-anchor="middle" y="5" font-size="13" font-weight="700" fill="#101725" pointer-events="none">'+count+'</text>':'<circle r="4" fill="#102233" pointer-events="none"/>')+(selected?'<text x="'+(g.x>width/2?-20:20)+'" text-anchor="'+(g.x>width/2?'end':'start')+'" y="5" font-size="13" fill="#fff" stroke="#101725" stroke-width="4" paint-order="stroke" pointer-events="none">'+esc(g.points[0].location.city)+'</text>':'')+'</g>';}).join('');
      el.querySelector('[data-map-scale]').textContent=zoom.toFixed(1)+'×';
    }
    function resize(reset) {
      var oldWidth=width, oldHeight=height;
      width=surface.clientWidth; height=surface.clientHeight; base=Math.min(width/1000,height/500);
      if(reset||!oldWidth) { zoom=1; tx=(width-1000*base)/2;ty=(height-500*base)/2; }
      else {tx+=(width-oldWidth)/2;ty+=(height-oldHeight)/2;}
      draw();
    }
    function zoomAt(factor,x,y) {
      var next=Math.max(1,Math.min(24,zoom*factor)), ratio=next/zoom;
      tx=x-(x-tx)*ratio;ty=y-(y-ty)*ratio;zoom=next;draw();
    }
    function focusPoints(points) {
      if(!points.length)return;
      var xs=points.map(function(p){return p.x;}), ys=points.map(function(p){return p.y;});
      var minX=Math.min.apply(null,xs), maxX=Math.max.apply(null,xs),minY=Math.min.apply(null,ys),maxY=Math.max.apply(null,ys);
      zoom=Math.max(1,Math.min(14,Math.min((width-100)/Math.max(25,maxX-minX),(height-100)/Math.max(25,maxY-minY))/base));
      tx=width/2-(minX+maxX)/2*base*zoom;ty=height/2-(minY+maxY)/2*base*zoom;draw();
    }
    function pick(name) {
      var c=located.find(function(c){return c.name===name;});if(!c)return;
      selected=name; query='';el.querySelector('[data-map-search]').value='';el.querySelector('[data-map-company]').value=name;
      focusPoints(c.locations.map(project)); showCompany(c);
    }
    function openCluster(index) {
      var g=groups[index]; if(!g)return;
      var companies=g.points.map(function(p){return p.company;}), names=new Set(companies.map(function(c){return c.name;}));
      if(names.size===1) {showCompany(companies[0],g.points.map(function(p){return p.location;}));return;}
      var points=g.points.map(function(p){return p.world;});
      showCompanies(companies,'Empresas en esta zona');
      if(points.some(function(p){return Math.hypot(p.x-points[0].x,p.y-points[0].y)>1;}))focusPoints(points);
    }
    function reset() {
      selected='';query='';el.querySelector('[data-map-search]').value='';el.querySelector('[data-map-company]').value='';
      resize(true);showCompanies(located,'Explora las empresas');
    }
    function pointerPosition(e) {var r=surface.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
    function currentGesture() {
      var ps=Array.from(pointers.values());
      return {x:ps.reduce(function(n,p){return n+p.x;},0)/ps.length,y:ps.reduce(function(n,p){return n+p.y;},0)/ps.length,distance:ps.length>1?Math.hypot(ps[0].x-ps[1].x,ps[0].y-ps[1].y):0};
    }
    surface.onpointerdown=function(e){if(e.button&&e.button!==0)return;pointers.set(e.pointerId,pointerPosition(e));surface.setPointerCapture(e.pointerId);gesture=currentGesture();moved=false;};
    surface.onpointermove=function(e){if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,pointerPosition(e));var next=currentGesture();if(pointers.size>1||Math.hypot(next.x-gesture.x,next.y-gesture.y)>1)moved=true;if(next.distance&&gesture.distance)zoomAt(next.distance/gesture.distance,gesture.x,gesture.y);tx+=next.x-gesture.x;ty+=next.y-gesture.y;gesture=next;draw();};
    function release(e) {
      var wasMoved=moved, point=pointerPosition(e);
      pointers.delete(e.pointerId);gesture=pointers.size?currentGesture():null;
      if(!wasMoved&&e.type!=='pointercancel') {var index=groups.findIndex(function(g){return Math.hypot(point.x-g.x,point.y-g.y)<=24;});if(index>=0)openCluster(index);}
    }
    surface.onpointerup=release;surface.onpointercancel=release;
    surface.addEventListener('wheel',function(e){e.preventDefault();var p=pointerPosition(e);zoomAt(Math.exp(-e.deltaY*.002),p.x,p.y);},{passive:false});
    surface.ondblclick=function(e){var p=pointerPosition(e);zoomAt(2,p.x,p.y);};
    surface.onkeydown=function(e){var target=e.target.closest('[data-map-cluster]');if(target&&(e.key==='Enter'||e.key===' ')){e.preventDefault();openCluster(Number(target.dataset.mapCluster));return;}var delta={ArrowLeft:[55,0],ArrowRight:[-55,0],ArrowUp:[0,55],ArrowDown:[0,-55]}[e.key];if(delta){e.preventDefault();tx+=delta[0];ty+=delta[1];draw();}else if(['+','=','-'].includes(e.key)){e.preventDefault();zoomAt(e.key==='-'?.8:1.25,width/2,height/2);}};
    el.querySelector('[data-map-company]').onchange=function(e){if(e.target.value)pick(e.target.value);else reset();};
    el.querySelector('[data-map-search]').oninput=function(e){selected='';query=e.target.value.trim().toLocaleLowerCase();el.querySelector('[data-map-company]').value='';resize(true);showCompanies(matching(),query?'Resultados de búsqueda':'Explora las empresas');};
    el.querySelector('[data-map-reset]').onclick=reset;
    el.querySelectorAll('[data-map-zoom]').forEach(function(b){b.onclick=function(){zoomAt(Number(b.dataset.mapZoom)>0?1.5:1/1.5,width/2,height/2);};});
    panel.onclick=function(e){var b=e.target.closest('[data-pick-company]'), offices=e.target.closest('[data-show-offices]');if(b)pick(b.dataset.pickCompany);if(offices)pick(offices.dataset.showOffices);};
    resize(true);showCompanies(located,'Explora las empresas');
    resizeObserver=new ResizeObserver(function(){if(el.isConnected&&surface.clientWidth)resize(false);});resizeObserver.observe(surface);
    return function(){resizeObserver.disconnect();};
  }
  root.VfxCompanyMap={mount:mount,clusters:clusters};
  if(typeof module!=='undefined')module.exports=root.VfxCompanyMap;
})(typeof window!=='undefined'?window:globalThis);
