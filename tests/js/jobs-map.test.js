const test=require('node:test');
const assert=require('node:assert/strict');
const {clusters}=require('../../assets/jobs/jobs-map.js');
test('agrupa por proximidad en pantalla y separa puntos al ampliar',()=>{
  const points=[{x:100,y:100},{x:110,y:110},{x:300,y:200}];
  assert.deepEqual(clusters(points,44).map(g=>g.points.length),[2,1]);
  assert.equal(clusters(points.map(p=>({x:p.x*10,y:p.y*10})),44).length,3);
});
test('conserva todos los puntos de varias empresas en una misma ciudad',()=>{
  const points=Array.from({length:30},(_,i)=>({x:100,y:100,company:'Company '+i}));
  const groups=clusters(points,44);
  assert.equal(groups.length,1);
  assert.equal(new Set(groups[0].points.map(p=>p.company)).size,30);
});
