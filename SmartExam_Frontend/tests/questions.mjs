import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import test from 'node:test';

const storage = new Map();
globalThis.localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
};
globalThis.sessionStorage = { removeItem() {} };
globalThis.window = { SMARTEXAM_CONFIG: { mode: 'api', baseUrl: '' }, dispatchEvent() {} };
const source = await fs.readFile(new URL('../dist/api.js', import.meta.url), 'utf8');
const { api } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const question = {
  subject_id: 'js', text: 'Khai báo biến có phạm vi khối?', difficulty: 'easy',
  explanation: 'let có phạm vi khối.', is_active: true,
  options: [{ id: 'a', text: 'let', is_correct: true }, { id: 'b', text: 'var', is_correct: false }],
};

test('question requests use the JWT and include only supported fields', async () => {
  globalThis.fetch = async url => new Response(JSON.stringify(url === '/auth/login'
    ? { access_token: 'test-token' }
    : { id: 'admin', name: 'Admin', role: 'admin' }));
  await api.login('admin@example.com', 'test-password');
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/admin/questions');
    assert.equal(request.method, 'POST');
    assert.equal(request.headers.Authorization, 'Bearer test-token');
    assert.deepEqual(JSON.parse(request.body), question);
    return new Response(JSON.stringify({ ...question, id: 'question-id' }), { status: 201 });
  };
  const saved = await api.saveQuestion({ ...question, role: 'admin',
    options: question.options.map(option => ({ ...option, question_id: 'injected', position: 9 })),
  });
  assert.equal(saved.id, 'question-id');
  assert.equal(storage.size, 0);
});

test('editing puts the question id in the URL and preserves option ids and order', async () => {
  const edited = { ...question, options: [...question.options].reverse() };
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/admin/questions/question-id');
    assert.equal(request.method, 'PATCH');
    assert.deepEqual(JSON.parse(request.body), edited);
    return new Response(JSON.stringify({ ...edited, id: 'question-id' }));
  };
  await api.saveQuestion({ ...edited, id: 'question-id' });
});

test('hiding sends a partial patch without overwriting content or options', async () => {
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/admin/questions/question-id');
    assert.equal(request.method, 'PATCH');
    assert.deepEqual(JSON.parse(request.body), { is_active: false });
    return new Response(JSON.stringify({ ...question, id: 'question-id', is_active: false }));
  };
  assert.equal((await api.saveQuestion({ id: 'question-id', is_active: false })).is_active, false);
});

test('listing includes subject, difficulty and false status filters', async () => {
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/admin/questions?subject_id=js&difficulty=hard&is_active=false');
    assert.equal(request.method, 'GET');
    return new Response('[]');
  };
  assert.deepEqual(await api.questions({ subject_id: 'js', difficulty: 'hard', is_active: false }), []);
});

test('invalid options produce actionable Vietnamese feedback without echoing raw input', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: [
    { loc: ['body', 'options'], msg: 'untrusted raw content', input: 'private input' },
  ] }), { status: 422 });
  await assert.rejects(api.saveQuestion(question), error => {
    assert.match(error.message, /2–6 phương án/);
    assert.match(error.message, /đúng một đáp án đúng/);
    assert.ok(!error.message.includes('untrusted'));
    assert.ok(!error.message.includes('private'));
    return true;
  });
});

test('missing subjects and forbidden operations preserve server business errors', async () => {
  for (const [status, detail] of [
    [404, 'Không tìm thấy môn học.'], [403, 'Bạn không có quyền thực hiện thao tác này.'],
  ]) {
    globalThis.fetch = async () => new Response(JSON.stringify({ detail }), { status });
    await assert.rejects(api.saveQuestion(question), error => error.message === detail);
  }
  assert.equal(storage.size, 0);
});

test('HTTP errors retain status for page-specific handling', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 });
  await assert.rejects(api.exams(), error => error.status === 404 && error.message === 'Not Found');
});

test('subject edits exclude the id from the body for the strict backend schema', async () => {
  globalThis.fetch = async (url, request) => {
    assert.equal(url, '/admin/subjects/js');
    assert.equal(request.method, 'PATCH');
    assert.deepEqual(JSON.parse(request.body), { name: 'JavaScript', slug: 'js', is_active: true });
    return new Response('{}');
  };
  await api.saveSubject({ id: 'js', name: 'JavaScript', slug: 'js', is_active: true });
});
