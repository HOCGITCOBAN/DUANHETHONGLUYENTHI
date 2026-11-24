import assert from 'node:assert/strict';
import fs from 'node:fs/promises';

globalThis.sessionStorage = { removeItem() {} };
globalThis.window = { SMARTEXAM_CONFIG: { mode: 'api', baseUrl: '' }, dispatchEvent() {} };
globalThis.Event ||= class Event { constructor(type) { this.type = type; } };
const source = await fs.readFile(new URL('../dist/api.js', import.meta.url), 'utf8');
const { api } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const attemptResult = {
  id: 'attempt-1', status: 'submitted', score: 75, correct_count: 1, passed: true,
  answers: { q1: 'o1' },
  snapshot: { title: 'Kiểm tra mẫu', pass_score: 60, questions: [
    { id: 'q1', text: 'Câu hỏi?', points: 1, explanation: 'Lời giải.', options: [
      { id: 'o1', text: 'Đúng', is_correct: true }, { id: 'o2', text: 'Sai', is_correct: false },
    ] },
  ] },
};
let resultCalls = 0;
globalThis.fetch = async url => {
  if (url === '/auth/login') return new Response(JSON.stringify({ access_token: 'token' }));
  if (url === '/auth/me') return new Response(JSON.stringify({ id: 'u1', role: 'student' }));
  assert.equal(url, '/attempts/attempt-1/result');
  resultCalls++;
  if (resultCalls === 1) throw new TypeError('temporary network disconnect');
  return new Response(JSON.stringify(attemptResult));
};

await api.login('student@example.com', 'password');
const result = await api.result('attempt-1');
assert.equal(resultCalls, 2, 'GET result retries one temporary connection failure');
assert.equal(result.score, 75);
assert.equal(result.correct_count, 1);
assert.equal(result.snapshot.questions[0].options[0].is_correct, true);
assert.equal(result.snapshot.questions[0].explanation, 'Lời giải.');

console.log('PASS: result endpoint returns score, correct count, pass state, selected answer, and review details; transient GET connection failure is retried.');
