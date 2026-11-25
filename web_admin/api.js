export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}
export function errorMessage(detail) {
  const known = {
    'Account is locked': 'Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.',
    'User not found': 'Tài khoản không còn tồn tại. Vui lòng tải lại danh sách.',
    'Only learner accounts can be managed': 'Chỉ có thể khóa hoặc xóa tài khoản người học. Tài khoản quản trị được bảo vệ.',
    'Username confirmation does not match': 'Tên đăng nhập xác nhận chưa khớp.',
    'Invalid username or password': 'Tên đăng nhập hoặc mật khẩu không đúng.',
    'Admin access required': 'Tài khoản này không có quyền quản trị.',
    'Could not validate credentials': 'Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.',
    'Not authenticated': 'Vui lòng đăng nhập để tiếp tục.',
    'Data conflict; name or slug already exists': 'Tên từ vựng, tên chủ đề hoặc slug đã tồn tại.',
    'Topic still contains vocabulary': 'Chủ đề còn từ vựng. Hãy chuyển các từ sang chủ đề khác trước khi xóa.',
    'Topic not found': 'Chủ đề không còn tồn tại. Vui lòng tải lại dữ liệu.',
    'Vocabulary not found': 'Từ vựng không còn tồn tại. Vui lòng tải lại dữ liệu.',
    'Existing example cannot be cleared in this editor': 'Không thể để trống câu ví dụ đã có. Hãy nhập câu ví dụ.',
    'Invalid or duplicate vocabulary meaning ID': 'Danh sách nghĩa đã thay đổi. Hãy tải lại từ vựng rồi sửa tiếp.',
    'Invalid or duplicate vocabulary example ID': 'Danh sách ví dụ đã thay đổi. Hãy tải lại từ vựng rồi sửa tiếp.',
    'Cannot connect to backend': 'Không kết nối được backend. Kiểm tra backend đang chạy và BACKEND_URL.',
    'Backend timed out': 'Backend phản hồi quá lâu. Vui lòng thử lại.',
  };
  if (Array.isArray(detail)) return detail.map(e => `${(e.loc || []).filter(x => x !== 'body').join('.')}: ${e.msg}`).join('; ');
  return known[detail] || (typeof detail === 'string' ? detail : 'Yêu cầu không thành công. Vui lòng thử lại.');
}
export async function request(path, { token, method = 'GET', body, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method, signal,
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(body ? { 'Content-Type': 'application/json' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('Không kết nối được máy chủ. Vui lòng kiểm tra kết nối.', 0);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(data?.detail), response.status);
  return data;
}
