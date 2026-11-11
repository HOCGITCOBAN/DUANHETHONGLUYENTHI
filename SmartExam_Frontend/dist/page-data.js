// Load only the collections needed by the selected page. A missing exam/history
// collection must not block account information or the question/subject catalog.
export async function loadPageData(api, path, isAdmin, localData=false) {
  const data={subjects:[],exams:[],questions:[],history:[],unavailable:[]};
  const dashboard=path==='/dashboard';
  const subjects=!isAdmin&&path==='/subjects';
  const questionBank=isAdmin&&['/admin/subjects','/admin/questions'].includes(path);
  const examManagement=isAdmin&&path==='/admin/exams';
  const examList=!isAdmin&&path==='/exams';
  const stats=isAdmin&&path==='/admin/stats';
  const attempt=!isAdmin&&(path.startsWith('/attempt/')||path.startsWith('/result/'));
  const jobs=[];
  async function load(key, request, allowMissing=false) {
    try {
      data[key]=await request();
    } catch(error) {
      if(allowMissing&&!localData&&error.status===404)data.unavailable.push(key);
      else throw error;
    }
  }
  if(dashboard||subjects||questionBank||examManagement||examList||attempt){
    jobs.push(load('subjects',()=>api.subjects(isAdmin)));
  }
  if(isAdmin&&(dashboard||questionBank||examManagement)){
    jobs.push(load('questions',()=>api.questions()));
  }
  if(dashboard||examManagement||examList||stats||(localData&&subjects)){
    jobs.push(load('exams',()=>api.exams(isAdmin),true));
  }
  if(!isAdmin&&(dashboard||path==='/history')){
    jobs.push(load('history',()=>api.history(),true));
  }
  await Promise.all(jobs);
  return data;
}
