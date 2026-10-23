(function (root) {
  'use strict';
  var C=root.VfxJobsCore, esc=C.escapeHtml;
  var colors=['#b39aff','#56d5bd','#ffbb70','#69b9ff','#f391ba','#d8dc73','#adbacf','#ff837c','#61c8df','#cf9cf1','#90cca2','#d5a884','#c1bcff'];
  var labels={custom:'Web propia',greenhouse:'Greenhouse',teamtailor:'Teamtailor',workday:'Workday',workable:'Workable',lever:'Lever',smartrecruiters:'SmartRecruiters',ashby:'Ashby',personio:'Personio',recruitee:'Recruitee','massive-wp':'WordPress',room8:'WordPress',epic:'Greenhouse',ea:'Portal EA',bamboo:'BambooHR',pinpoint:'Pinpoint',infiniteplus:'Web propia',mercurysteam:'Web propia',mundfish:'Web propia',axiomvfx:'Web propia'};
  function platform(type) {return labels[type]||type||'Sin identificar';}
  function statistics(jobs,companies) {
    var counts={},types={};
    (companies||[]).forEach(function(c){types[c.name]=c.type;if(c.enabled!==false)counts[platform(c.type)]=0;});
    (jobs||[]).forEach(function(j){
      if(j.status!=='active'||!['ats','official-site'].includes(j.sourceKind||j.source)||j.viaAggregator||/^(az-|sig-)/.test(j.id))return;
      var name=platform(types[j.company]||j.ats);counts[name]=(counts[name]||0)+1;
    });
    return Object.keys(counts).map(function(name){return {name:name,count:counts[name]};}).sort(function(a,b){return b.count-a.count||a.name.localeCompare(b.name);});
  }
  function chart(rows) {
    var total=rows.reduce(function(n,r){return n+r.count;},0),offset=0;
    var arcs=rows.filter(function(r){return r.count;}).map(function(r,i){
      var percent=r.count/total*100;
      var arc='<circle r="42" cx="60" cy="60" fill="none" stroke="'+colors[i%colors.length]+'" stroke-width="13" pathLength="100" stroke-dasharray="'+percent+' '+(100-percent)+'" stroke-dashoffset="'+(-offset)+'" transform="rotate(-90 60 60)"/>';
      offset+=percent;return arc;
    }).join('');
    return '<div class="ji-chart"><svg viewBox="0 0 120 120" role="img" aria-label="'+total+' ofertas activas por plataforma"><circle r="42" cx="60" cy="60" fill="none" stroke="#293044" stroke-width="13"/>'+arcs+'<text x="60" y="60" text-anchor="middle" fill="currentColor" font-size="21">'+total+'</text><text x="60" y="75" text-anchor="middle" fill="currentColor" font-size="8">ofertas activas</text></svg><ol class="ji-ranking">'+rows.map(function(r,i){return '<li style="border-left:4px solid '+colors[i%colors.length]+';padding-left:10px"><span>'+esc(r.name)+'</span><strong>'+r.count+'</strong><span>'+(total?Math.round(r.count/total*100):0)+'%</span></li>';}).join('')+'</ol></div>';
  }
  function mount(el,data,jobs,companies) {
    if(el.disposeCompanyMap)el.disposeCompanyMap();
    var rows=statistics(jobs,companies),total=rows.reduce(function(n,r){return n+r.count;},0);
    var most=rows.length&&rows[0].count?rows[0].name+' ('+rows[0].count+')':'Sin ofertas';
    var least=rows.length?rows.filter(function(r){return r.count===rows[rows.length-1].count;}).map(function(r){return r.name;}).join(', '):'Sin datos';
    el.innerHTML='<h2>Radar global</h2><p>Ubicaciones publicadas por las empresas, aproximadas al centro de cada ciudad. No representan todas sus sedes ni la ubicación de cada vacante.</p><div class="jp-co"><h3>Ofertas por plataforma</h3><p>'+total+' ofertas VFX activas de portales directos, incluidas coincidencias posibles. Sin filtros personales, cerradas ni agregadores.</p>'+chart(rows)+'<p>Más ofertas: '+esc(most)+'. Menos: '+esc(least)+'.</p></div><div class="jp-co"><h3>Mapa de empresas</h3><div data-company-map></div><p class="jp-co-m">Cartografía: Natural Earth, dominio público. Ubicaciones: portales de empleo y páginas oficiales.</p></div>';
    el.disposeCompanyMap=root.VfxCompanyMap.mount(el.querySelector('[data-company-map]'),data,jobs,companies);
  }
  root.VfxJobsInsights={mount:mount,statistics:statistics,platform:platform};
  if(typeof module!=='undefined')module.exports=root.VfxJobsInsights;
})(typeof window!=='undefined'?window:globalThis);
