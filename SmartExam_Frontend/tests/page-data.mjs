import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import test from 'node:test';

const source=await fs.readFile(new URL('../dist/page-data.js',import.meta.url),'utf8');
const {loadPageData}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const subjects=[{id:'js',name:'JavaScript'}];
const missing=()=>Object.assign(new Error('Not Found'),{status:404});

function client(overrides={}){
  const calls=[];
  const api=Object.fromEntries(['subjects','exams','questions','history'].map(key=>[
    key, async (...args)=>{
      calls.push([key,...args]);
      if(overrides[key])return overrides[key](...args);
      throw Error('Unexpected collection: '+key);
    },
  ]));
  return {api,calls};
}

test('profile renders from the authenticated user without requesting any collection',async()=>{
  const {api,calls}=client();
  assert.deepEqual((await loadPageData(api,'/profile',false)).unavailable,[]);
  assert.deepEqual(calls,[]);
});

test('student subjects do not depend on missing exam or history APIs',async()=>{
  const {api,calls}=client({subjects:()=>subjects});
  const data=await loadPageData(api,'/subjects',false);
  assert.deepEqual(data.subjects,subjects);
  assert.deepEqual(data.unavailable,[]);
  assert.deepEqual(calls,[['subjects',false]]);
});

test('student dashboard retains real subjects and marks unavailable collections',async()=>{
  const {api}=client({subjects:()=>subjects,exams:()=>{throw missing()},history:()=>{throw missing()}});
  const data=await loadPageData(api,'/dashboard',false);
  assert.deepEqual(data.subjects,subjects);
  assert.deepEqual(data.unavailable.sort(),['exams','history']);
});

test('history page does not request subjects, exams or admin questions',async()=>{
  const {api,calls}=client({history:()=>{throw missing()}});
  assert.deepEqual((await loadPageData(api,'/history',false)).unavailable,['history']);
  assert.deepEqual(calls,[['history']]);
});

test('exam page does not request unrelated student history',async()=>{
  const {api,calls}=client({subjects:()=>subjects,exams:()=>{throw missing()}});
  assert.deepEqual((await loadPageData(api,'/exams',false)).unavailable,['exams']);
  assert.deepEqual(calls,[['subjects',false],['exams',false]]);
});

for(const path of ['/admin/questions','/admin/subjects']){
  test(path+' only requires the subject and question bank',async()=>{
    const {api,calls}=client({subjects:()=>subjects,questions:()=>[]});
    assert.deepEqual((await loadPageData(api,path,true)).unavailable,[]);
    assert.deepEqual(calls,[['subjects',true],['questions']]);
  });
}

for(const status of [401,403,500]){
  test('HTTP '+status+' remains an error instead of being treated as an unimplemented feature',async()=>{
    const error=Object.assign(new Error('HTTP '+status),{status});
    const {api}=client({history:()=>{throw error}});
    await assert.rejects(loadPageData(api,'/history',false),actual=>actual===error);
  });
}

test('network errors remain visible',async()=>{
  const error=new TypeError('Network failure');
  const {api}=client({history:()=>{throw error}});
  await assert.rejects(loadPageData(api,'/history',false),actual=>actual===error);
});

test('missing question bank is an error, never a synthetic empty bank',async()=>{
  const {api}=client({subjects:()=>subjects,questions:()=>{throw missing()}});
  await assert.rejects(loadPageData(api,'/admin/questions',true),error=>error.status===404);
});

test('a complete backend still supplies all dashboard data',async()=>{
  const exams=[{id:'exam'}],history=[{id:'attempt'}];
  const {api}=client({subjects:()=>subjects,exams:()=>exams,history:()=>history});
  const data=await loadPageData(api,'/dashboard',false);
  assert.deepEqual(data,{subjects,exams,history,questions:[],unavailable:[]});
});

test('demo subject cards retain their real local exam counts',async()=>{
  const {api,calls}=client({subjects:()=>subjects,exams:()=>[{id:'exam',subject_id:'js'}]});
  const data=await loadPageData(api,'/subjects',false,true);
  assert.equal(data.exams.length,1);
  assert.deepEqual(calls,[['subjects',false],['exams',false]]);
});

test('admin statistics only requests the exam collection before per-exam stats',async()=>{
  const {api,calls}=client({exams:()=>{throw missing()}});
  assert.deepEqual((await loadPageData(api,'/admin/stats',true)).unavailable,['exams']);
  assert.deepEqual(calls,[['exams',true]]);
});
