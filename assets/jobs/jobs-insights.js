(function (root) {
  'use strict';
  var C = root.VfxJobsCore, esc = C.escapeHtml;
  var colors = ['#b39aff','#56d5bd','#ffbb70','#69b9ff','#f391ba','#d8dc73','#adbacf'];
  var labels = {custom:'Web propia',greenhouse:'Greenhouse',teamtailor:'Teamtailor',workday:'Workday',workable:'Workable',lever:'Lever',smartrecruiters:'SmartRecruiters',ashby:'Ashby',personio:'Personio',recruitee:'Recruitee','massive-wp':'WordPress',room8:'WordPress',epic:'Greenhouse',ea:'Portal EA',bamboo:'BambooHR',pinpoint:'Pinpoint',infiniteplus:'Web propia',mercurysteam:'Web propia',mundfish:'Web propia',axiomvfx:'Web propia'};
  function platform(type) { return labels[type] || type || 'Sin identificar'; }
  function statistics(jobs, companies) {
    var counts = {}, types={};
    (companies || []).forEach(function(c) { types[c.name]=c.type; if(c.enabled !== false) counts[platform(c.type)] = 0; });
    (jobs || []).forEach(function(j) {
      if (j.status !== 'active' || !['ats','official-site'].includes(j.sourceKind || j.source) || j.viaAggregator || /^(az-|sig-)/.test(j.id)) return;
      var name = platform(types[j.company] || j.ats); counts[name] = (counts[name] || 0) + 1;
    });
    return Object.keys(counts).map(function(name) { return {name:name,count:counts[name]}; }).sort(function(a,b) { return b.count-a.count || a.name.localeCompare(b.name); });
  }
  function chart(rows) {
    var total = rows.reduce(function(n,r){return n+r.count;},0), offset=0;
    var arcs=rows.filter(function(r){return r.count;}).map(function(r,i){var percent=r.count/total*100;var h='<circle r="42" cx="60" cy="60" fill="none" stroke="'+colors[i%colors.length]+'" stroke-width="13" pathLength="100" stroke-dasharray="'+percent+' '+(100-percent)+'" stroke-dashoffset="'+(-offset)+'" transform="rotate(-90 60 60)"/>';offset+=percent;return h;}).join('');
    return '<div class="ji-chart"><svg viewBox="0 0 120 120" role="img" aria-label="'+total+' ofertas activas por plataforma"><circle r="42" cx="60" cy="60" fill="none" stroke="#293044" stroke-width="13"/>'+arcs+'<text x="60" y="60" text-anchor="middle" fill="currentColor" font-size="21">'+total+'</text><text x="60" y="75" text-anchor="middle" fill="currentColor" font-size="8">ofertas activas</text></svg><ol class="ji-ranking">'+rows.map(function(r,i){return '<li><span>'+esc(r.name)+'</span><strong>'+r.count+'</strong><span>'+ (total?Math.round(r.count/total*100):0)+'%</span></li>';}).join('')+'</ol></div>';
  }
  function mount(el, data, jobs, companies) {
    var selected='', zoom=1, names=true;
    var located=data.locations.companies.filter(function(c){return c.locations.length;}), missing=data.locations.companies.filter(function(c){return !c.locations.length;});
    var rows=statistics(jobs,companies), total=rows.reduce(function(n,r){return n+r.count;},0);
    el.innerHTML='<h2>Radar global</h2><p>Ubicaciones publicadas por las empresas, aproximadas al centro de cada ciudad. No representan todas sus sedes ni la ubicación de cada vacante.</p><div class="jp-co"><h3>Ofertas por plataforma</h3><p>'+total+' ofertas VFX activas de portales directos, incluidas coincidencias posibles. Sin filtros personales, cerradas ni agregadores.</p>'+chart(rows)+'<p>Más ofertas: '+esc(rows.filter(function(r){return r.count;}).slice(0,1).map(function(r){return r.name+' ('+r.count+')';}).join('') || 'Sin ofertas')+'. Menos: '+esc(rows.length?rows.filter(function(r){return r.count===rows[rows.length-1].count;}).map(function(r){return r.name;}).join(', '):'sin datos')+'.</p></div><div class="jp-co"><h3>Mapa de empresas</h3><div class="ji-controls"><label>Empresa <select data-map-company><option value="">Todas ('+located.length+')</option>'+located.map(function(c){return '<option>'+esc(c.name)+'</option>';}).join('')+'</select></label><button class="jp-btn" data-zoom="1" aria-label="Ampliar mapa">+</button><button class="jp-btn" data-zoom="-1" aria-label="Reducir mapa">−</button><label><input type="checkbox" data-map-names checked> Nombres</label></div><p>Desplázate por el mapa al ampliarlo. Selecciona una empresa para verla sin nombres superpuestos.</p><div class="ji-map-scroll" tabindex="0" aria-label="Mapa mundial, desplazable"><div data-map-canvas></div></div><div data-map-detail aria-live="polite"></div><details><summary>Sin ubicación verificada ('+missing.length+')</summary><p>'+missing.map(function(c){return esc(c.name);}).join(' · ')+'</p></details><p class="jp-co-m">Cartografía: Natural Earth, dominio público. Ubicaciones: portales de empleo y páginas oficiales.</p></div>';
    function draw() {
      var groups={}; located.forEach(function(c){if(selected&&c.name!==selected)return;c.locations.forEach(function(p){var k=p.lat+','+p.lon;var g=groups[k]||(groups[k]={p:p,companies:[]});g.companies.push(c);});});
      var paths=data.world.polygons.map(function(poly){return '<path d="M'+poly.map(function(p){return Number(p[0])+','+Number(p[1]);}).join('L')+'Z"/>';}).join('');
      var markers=Object.keys(groups).map(function(k){var g=groups[k],x=(g.p.lon+180)/360*1000,y=(90-g.p.lat)/180*500;return '<g><circle cx="'+x+'" cy="'+y+'" r="3" fill="#63e1ca"/><title>'+esc(g.p.city+': '+g.companies.map(function(c){return c.name;}).join(', '))+'</title>'+ (names?g.companies.map(function(c,i){return '<text x="'+(x+5)+'" y="'+(y+i*9)+'" font-size="8" fill="#f3efff" stroke="#101725" stroke-width="2" paint-order="stroke">'+esc(c.name)+'</text>';}).join(''):'')+'</g>';}).join('');
      el.querySelector('[data-map-canvas]').innerHTML='<svg viewBox="0 0 1000 500" role="img" aria-label="Ubicaciones de empresas" style="width:'+zoom*100+'%;display:block"><rect width="1000" height="500" fill="#0d1727"/><g fill="#293b51" stroke="#496079" stroke-width=".4">'+paths+'</g>'+markers+'</svg>';
      var current=located.filter(function(c){return !selected||c.name===selected;});
      el.querySelector('[data-map-detail]').innerHTML='<p>'+located.length+' empresas localizadas · '+missing.length+' sin ubicación verificada.</p><details'+(selected?' open':'')+'><summary>Ubicaciones y fuentes</summary><ul>'+current.map(function(c){return '<li><strong>'+esc(c.name)+'</strong>'+ (c.sharedSource?' · portal compartido con '+esc(c.sharedSource):'')+': '+c.locations.map(function(p){var u=C.safeUrl(p.evidence);return u?'<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+esc(p.city)+'</a>':esc(p.city);}).join(', ')+'</li>';}).join('')+'</ul></details>';
    }
    function centerSelection() {
      if(!selected) return;
      var company=located.filter(function(c){return c.name===selected;})[0];
      var points=company.locations, lon=points.reduce(function(n,p){return n+Number(p.lon);},0)/points.length, lat=points.reduce(function(n,p){return n+Number(p.lat);},0)/points.length;
      var surface=el.querySelector('.ji-map-scroll'), svg=el.querySelector('[data-map-canvas] svg');
      surface.scrollLeft=(lon+180)/360*svg.getBoundingClientRect().width-surface.clientWidth/2;
      surface.scrollTop=(90-lat)/180*svg.getBoundingClientRect().height-surface.clientHeight/2;
    }
    el.querySelector('[data-map-company]').onchange=function(e){selected=e.target.value;draw();centerSelection();};
    el.querySelector('[data-map-names]').onchange=function(e){names=e.target.checked;draw();};
    el.querySelectorAll('[data-zoom]').forEach(function(b){b.onclick=function(){zoom=Math.max(1,Math.min(5,zoom+Number(b.dataset.zoom)*.5));draw();centerSelection();};});
    el.querySelectorAll('.ji-ranking li').forEach(function(row,i) { row.style.borderLeft='4px solid '+colors[i%colors.length]; row.style.paddingLeft='10px'; });
    draw();
  }
  root.VfxJobsInsights={mount:mount,statistics:statistics,platform:platform};
  if(typeof module!=='undefined') module.exports=root.VfxJobsInsights;
})(typeof window!=='undefined'?window:globalThis);
