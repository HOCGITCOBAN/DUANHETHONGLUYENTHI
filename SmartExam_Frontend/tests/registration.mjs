import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import test from 'node:test';

const storage = new Map();
globalThis.localStorage = {
  getItem: key => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
};
globalThis.sessionStorage = { removeItem() {} };
globalThis.window = {
  SMARTEXAM_CONFIG: { mode: 'api', baseUrl: '' },
  dispatchEvent() {},
};
const source = await fs.readFile(new URL('../dist/api.js', import.meta.url), 'utf8');
const { api } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const account = { name: 'Nguyễn Minh Anh', email: 'student@example.com', password: '  MậtKhẩu rất riêng!  ' };

test('registration sends the existing API contract and drops client role/hash fields', async () => {
  const user = { id: 'student-id', name: account.name, email: account.email, role: 'student' };
  let calls = 0;
  globalThis.fetch = async (url, request) => {
    calls++;
    assert.equal(url, '/auth/register');
    assert.equal(request.method, 'POST');
    assert.equal(request.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(request.body), account);
    return new Response(JSON.stringify(user), { status: 201 });
  };
  const result = await api.register({ ...account, role: 'admin', password_hash: 'injected' });
  assert.deepEqual(result, user);
  assert.equal(calls, 1);
  assert.equal(storage.size, 0);
});

test('duplicate email exposes the server conflict message', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Email đã được đăng ký.' }), { status: 409 });
  await assert.rejects(api.register(account), /Email đã được đăng ký/);
});

test('422 messages are translated without echoing rejected passwords or raw server input', async () => {
  const secret = 'Never echo this password';
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: [
    { loc: ['body', 'password'], msg: secret, input: secret, type: 'too_short' },
    { loc: ['body', 'full_name'], msg: 'raw name', type: 'too_long' },
  ] }), { status: 422 });
  await assert.rejects(api.register(account), error => {
    assert.match(error.message, /Mật khẩu cần từ 8 đến 128/);
    assert.match(error.message, /Họ và tên cần từ 1 đến 120/);
    assert.ok(!error.message.includes(secret));
    assert.ok(!error.message.includes('raw name'));
    return true;
  });
});

test('422 handles unknown and malformed field details with a safe generic message', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: [null,
    { loc: ['body', '__proto__'], msg: account.password },
  ] }), { status: 422 });
  await assert.rejects(api.register(account), /Thông tin đăng ký chưa hợp lệ/);
});

test('non-JSON server errors provide a stable failure without exposing the response body', async () => {
  globalThis.fetch = async () => new Response('<html>internal server details</html>', { status: 500 });
  await assert.rejects(api.register(account), /Yêu cầu thất bại \(500\)/);
});

test('network failures remain understandable and do not leak low-level messages', async () => {
  globalThis.fetch = async () => { throw new TypeError('private proxy failure'); };
  await assert.rejects(api.register(account), /Không thể kết nối đến máy chủ/);
});

test('aborted requests preserve the existing timeout feedback', async () => {
  globalThis.fetch = async () => { throw new DOMException('aborted', 'AbortError'); };
  await assert.rejects(api.register(account), /Máy chủ phản hồi quá lâu/);
});
