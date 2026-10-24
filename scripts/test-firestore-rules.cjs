const fs=require('node:fs');
const {initializeTestEnvironment,assertSucceeds,assertFails}=require('@firebase/rules-unit-testing');
const {doc,setDoc,getDoc,getDocs,collection,updateDoc}=require('firebase/firestore');
(async()=>{
  const env=await initializeTestEnvironment({projectId:'demo-yago-private',firestore:{rules:fs.readFileSync('firestore.rules','utf8')}});
  const uid='ylQ3m3XoCHTd0cwP7UQet7cSRpt1';
  const path=`users/${uid}/applications/gh-test`;
  const record={id:'gh-test',company:'Studio',title:'VFX Artist',url:'https://example.com/job',location:'Madrid',status:'applied',appliedAt:'2026-10-24T12:00:00Z',updatedAt:'2026-10-24T12:00:00Z',notes:'Private'};
  try{
    const owner=env.authenticatedContext(uid).firestore(),other=env.authenticatedContext('another-user').firestore(),anon=env.unauthenticatedContext().firestore();
    await assertSucceeds(setDoc(doc(owner,path),record));
    await assertSucceeds(getDoc(doc(owner,path)));
    await assertSucceeds(getDocs(collection(owner,`users/${uid}/applications`)));
    await assertSucceeds(updateDoc(doc(owner,path),{status:'interview'}));
    await assertFails(getDoc(doc(anon,path)));
    await assertFails(getDocs(collection(anon,`users/${uid}/applications`)));
    await assertFails(getDoc(doc(other,path)));
    await assertFails(setDoc(doc(other,path),record));
    await assertFails(setDoc(doc(owner,`users/another-user/applications/gh-test`),record));
    await assertFails(updateDoc(doc(owner,path),{status:'anything'}));
    await assertFails(updateDoc(doc(owner,path),{notes:'x'.repeat(2001)}));
    await assertFails(updateDoc(doc(owner,path),{url:'javascript:alert(1)'}));
    await assertFails(updateDoc(doc(owner,path),{unexpected:'value'}));
    await assertFails(setDoc(doc(anon,'portfolio/main'),{test:true}));
    console.log('14 private Firestore authorization/schema checks passed');
  }finally{await env.cleanup();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
