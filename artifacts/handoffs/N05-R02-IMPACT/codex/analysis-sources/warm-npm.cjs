const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cacache = require('C:/Program Files/nodejs/node_modules/npm/node_modules/cacache');
const root = 'D:/Agent/DeepSeekHarness/IntelligentLogisticsDispatchingAgent';
const temp = 'C:/Users/30382/AppData/Local/Temp/IntelligentLogisticsDispatchingAgent-n05-r02-impact';
const source = 'C:/Users/30382/AppData/Local/Temp/N05-independent/2026-10-04-main/npm-cache/_cacache';
const dest = path.join(temp, 'npm-cache/_cacache');
const started = new Date().toISOString();
(async () => {
  const lock = JSON.parse(fs.readFileSync(path.join(root, 'package-lock.json'), 'utf8'));
  const rows=[];
  for (const [pkg, entry] of Object.entries(lock.packages)) {
    if (!entry.resolved?.startsWith('https://registry.npmjs.org/') || !entry.integrity) continue;
    const key='make-fetch-happen:request-cache:'+entry.resolved;
    const old=await cacache.get(source, key);
    const integrity='sha512-'+crypto.createHash('sha512').update(old.data).digest('base64');
    if (integrity !== entry.integrity) throw new Error('locked integrity mismatch '+pkg);
    // Official cacache writes content/index atomically; do not copy live cache files.
    await cacache.put(dest, key, old.data, {integrity:entry.integrity, metadata:old.metadata});
    const check=await cacache.get(dest,key);
    if (!check.data.equals(old.data)) throw new Error('destination content mismatch '+pkg);
    rows.push({package:pkg,url:entry.resolved,integrity,bytes:old.data.length});
  }
  if (rows.length!==3) throw new Error('expected exactly three locked tarballs');
  const result={task_id:'N05-R02-IMPACT',scope:'exclusive task npm cache environment only; no source, lock, test, global setting or Gate fields changed',started_at:started,finished_at:new Date().toISOString(),passed:true,packages:rows,network_requests:0};
  fs.writeFileSync(path.join(temp,'npm-cache-warm.json'),JSON.stringify(result,null,2)+'\n');
  process.stdout.write(JSON.stringify(result)+'\n');
})().catch(err=>{process.stderr.write(err.stack+'\n');process.exitCode=1;});
