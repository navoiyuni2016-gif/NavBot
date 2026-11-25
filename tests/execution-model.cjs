const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};vm.runInNewContext(fs.readFileSync('navbot/execution.js','utf8'),context);
const {rows,deadlineState}=context.window.NavExecution;
assert.equal(rows(['new','in_progress','pending_approval','returned','closed'].map(status=>({status,created_at:'2020-01-01'}))).length,3);
const now=Date.parse('2026-11-25T07:00:00Z');
for(const [deadline,expected] of [[null,'none'],['invalid','none'],['2026-11-25T06:59:59Z','overdue'],['2026-11-25T07:00:00Z','near'],['2026-11-26T07:00:00Z','near'],['2026-11-26T07:00:01Z','normal']]) assert.equal(deadlineState({deadline},24,now),expected);
console.log('PASS execution status scope and deadline boundaries');
