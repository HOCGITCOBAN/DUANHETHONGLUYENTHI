import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root=fileURLToPath(new URL('./dist/',import.meta.url));
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'};
const port=Number(process.env.PORT||5500);
const server=http.createServer(async(req,res)=>{try{const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);const file=path.resolve(root,'.'+(pathname==='/'?'/index.html':pathname));if(!file.startsWith(root)){res.writeHead(403);res.end();return}const body=await fs.readFile(file);res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(body)}catch{res.writeHead(404);res.end('Not found')}});
let activePort=port;
server.on('error',error=>{
  if(['EADDRINUSE','EACCES'].includes(error.code)&&activePort<port+10){activePort++;server.listen(activePort,'127.0.0.1');return}
  console.error(error);process.exitCode=1;
});
server.listen(activePort,'127.0.0.1',()=>console.log(`SmartExam: http://localhost:${activePort}\nGiu cua so nay mo. Nhan Ctrl+C de dung.`));
