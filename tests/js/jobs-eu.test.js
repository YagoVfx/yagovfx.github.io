const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../../assets/jobs/jobs-core.js');
test('UE incluye sus 27 países y excluye Europa genérica y países no miembros',()=>{
  for(const code of 'AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE'.split(' '))assert.equal(C.isEU({countryCode:code}),true,code);
  for(const location of ['Remote, Europe','London, United Kingdom','Zurich, Switzerland','Oslo, Norway','Osaka, Japan','Dublin, Ohio, USA','Paris, Texas, USA'])assert.equal(C.isEU({location}),false,location);
  for(const location of ['Madrid','Bucharest, Romania','Berlin','Malmö','Remote - EU','Barcelona or London'])assert.equal(C.isEU({location}),true,location);
  assert.equal(C.isEU({remoteScope:'Spain'}),true);
  assert.equal(C.isEU({location:'Paris',countryCode:'US'}),false);
});
test('el filtro UE se conserva, genera chip y se puede quitar',()=>{
  const f={...C.defaultFilters,location:'eu'};
  const jobs=C.normalizeJobs([{id:'1',title:'VFX Artist',company:'One',location:'Madrid',ats:'greenhouse',url:'https://example.com/1',status:'active'},{id:'2',title:'VFX Artist',company:'Two',location:'London, UK',ats:'greenhouse',url:'https://example.com/2',status:'active'}]);
  assert.deepEqual(C.applyFilters(jobs,f).map(j=>j.id),['1']);
  assert.equal(C.sanitizeFilters(f).location,'eu');
  assert.equal(C.chipLabel('location',f),'Unión Europea');
});
