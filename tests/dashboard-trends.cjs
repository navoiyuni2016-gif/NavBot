// Calendar buckets are independently specified in Tashkent time.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const context={window:{},Intl,Date};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../navbot/dashboard.js'),'utf8'),context);
const model=context.window.NavDashboard.model;
const rows=['2025-12-26T12:00:00Z','2025-12-27T00:00:00Z','2025-12-31T20:00:00Z','2026-01-02T00:00:00Z','2025-02-01T00:00:00Z','2025-01-31T18:59:59Z','2026-01-03T00:00:00Z'].map(created_at=>({created_at,status:'new',section:0,service:0}));
const now=Date.parse('2026-01-02T07:00:00Z');
for(const [period,length,from,sum] of [['7d',7,'2025-12-27',3],['30d',30,'2025-12-04',4],['12m',12,'2025-02-01',5]]){
 const result=model(rows,[],period,now);assert.equal(result.daily.length,length);assert.equal(result.rangeFrom,from);assert.equal(result.rangeTo,'2026-01-02');assert.equal(result.daily.reduce((n,item)=>n+item[1],0),sum);assert.equal(result.total,7,'Changing trend interval must not change all-time totals');
 if(period==='7d')assert.equal(result.daily.find(([day])=>day==='2026-01-01')[1],1,'UTC evening belongs to the next Tashkent day');
 if(period==='12m')assert.equal(result.daily[0][0],'2025-02');
}
const leap=model([{status:'new',created_at:'2024-02-29T10:00:00Z'}],[],'30d',Date.parse('2024-03-01T10:00:00Z'));assert.equal(leap.rangeFrom,'2024-02-01');assert.equal(leap.daily.find(([day])=>day==='2024-02-29')[1],1);
assert.equal(model(rows,[],'__proto__',now).period,'7d');
console.log('PASS 7-day/30-day/12-month buckets, Tashkent midnight, year rollover, leap day, future dates, and unchanged all-time totals');
