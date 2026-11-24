// Auth thật qua Backend; nội dung đề thi demo được lưu cục bộ trên trình duyệt.
const pageHost = window.location.hostname;
const apiHost = !pageHost || pageHost === 'localhost' ? '127.0.0.1' : pageHost;
window.SMARTEXAM_CONFIG = { mode: 'api-demo', baseUrl: `http://${apiHost}:8000` };
