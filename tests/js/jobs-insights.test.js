const test = require('node:test');
const assert = require('node:assert/strict');
globalThis.VfxJobsCore = require('../../assets/jobs/jobs-core.js');
const I = require('../../assets/jobs/jobs-insights.js');
test('cuenta ofertas activas directas por plataforma real, incluye fuentes con cero y no duplica sedes', () => {
  const config = [{name:'Room8',type:'room8'},{name:'Epic Games',type:'epic'},{name:'CI Games',type:'teamtailor',studios:['Hexworks']},{name:'Empty',type:'workday'}];
  const base = {status:'active',sourceKind:'official-site',viaAggregator:false};
  const rows = I.statistics([
    {...base,id:'r8-1',company:'Room8',ats:'custom'},
    {...base,id:'epic-1',company:'Epic Games',ats:'greenhouse'},
    {...base,id:'epic-2',company:'Epic Games',ats:'greenhouse'},
    {...base,id:'az-1',company:'Epic Games',ats:'greenhouse'},
    {...base,id:'old',company:'Room8',ats:'custom',status:'closed'},
    {...base,id:'signal',company:'Room8',ats:'custom',viaAggregator:true},
  ],config);
  assert.deepEqual(rows.map(r=>[r.name,r.count]),[['Greenhouse',2],['WordPress',1],['Teamtailor',0],['Workday',0]]);
});
test('un catálogo vacío genera una estadística vacía',()=>assert.deepEqual(I.statistics([],[]),[]));
