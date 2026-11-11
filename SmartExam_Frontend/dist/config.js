// Auth thật qua Backend; nội dung đề thi demo được lưu cục bộ trên trình duyệt.
const apiHost = window.location.hostname || '127.0.0.1';
window.SMARTEXAM_CONFIG = { mode: 'api-demo', baseUrl: `http://${apiHost}:8000` };
