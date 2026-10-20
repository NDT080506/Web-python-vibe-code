"""
Unit tests kiểm thử tính năng của ứng dụng Guestbook (Phân quyền Admin & Client).
Kiểm thử các kịch bản:
1. Trang chủ khi chưa có lời nhắn ("Chưa có lời nhắn nào")
2. Thêm lời nhắn hợp lệ (Client có quyền thêm)
3. Validate khi để trống hoặc chỉ có khoảng trắng
4. Client không có quyền xóa: Cố tình xóa sẽ bị chặn và bản ghi vẫn còn
5. Admin có quyền xóa: Đăng nhập Admin thành công có thể xóa vĩnh viễn bản ghi
"""

import os
import unittest
from app import app, init_db, get_db

class GuestbookTestCase(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_guestbook.db")
        app.config["TESTING"] = True
        app.config["DATABASE"] = self.test_db
        self.client = app.test_client()

        init_db()
        with app.app_context():
            db = get_db()
            db.execute("DELETE FROM entries")
            db.commit()

    def tearDown(self):
        with app.app_context():
            db = get_db()
            db.execute("DELETE FROM entries")
            db.commit()
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except Exception:
                pass

    def test_empty_guestbook(self):
        """Kiểm tra trang chủ khi chưa có lời nhắn nào."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chưa có lời nhắn nào".encode("utf-8"), response.data)

    def test_add_valid_entry(self):
        """Kiểm tra client thêm lời nhắn hợp lệ."""
        response = self.client.post(
            "/add",
            data={"name": "Nguyễn Văn A", "message": "Chúc mừng bạn khai trương sổ lưu bút!"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Nguyễn Văn A".encode("utf-8"), response.data)
        self.assertIn("Chúc mừng bạn khai trương sổ lưu bút!".encode("utf-8"), response.data)

    def test_add_empty_entry_validation(self):
        """Kiểm tra validate khi gửi dữ liệu rỗng hoặc chỉ có khoảng trắng."""
        response = self.client.post(
            "/add",
            data={"name": "   ", "message": "Nội dung có nhưng tên rỗng"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vui lòng nhập đầy đủ cả tên và nội dung".encode("utf-8"), response.data)

    def test_client_cannot_delete_entry(self):
        """Kiểm tra Client BÌNH THƯỜNG KHÔNG THỂ XÓA bản ghi (bị từ chối)."""
        # Thêm 1 bản ghi
        self.client.post(
            "/add",
            data={"name": "Bản ghi thử nghiệm", "message": "Nội dung không được phép xóa bởi client"},
            follow_redirects=True,
        )

        with app.app_context():
            db = get_db()
            entry = db.execute("SELECT id FROM entries WHERE name = ?", ("Bản ghi thử nghiệm",)).fetchone()
            entry_id = entry["id"]

        # Client cố tình gọi route xóa
        response = self.client.post(f"/delete/{entry_id}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Kiểm tra xuất hiện cảnh báo từ chối quyền
        self.assertIn("Chỉ quản trị viên (Admin) mới có quyền xóa".encode("utf-8"), response.data)

        # Kiểm tra bản ghi vẫn tồn tại trong Database
        with app.app_context():
            db = get_db()
            still_exists = db.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
            self.assertIsNotNone(still_exists)

    def test_admin_can_delete_entry(self):
        """Kiểm tra Admin CÓ QUYỀN XÓA bản ghi sau khi mở khóa mã PIN."""
        # Thêm 1 bản ghi
        self.client.post(
            "/add",
            data={"name": "Bản ghi cần xóa", "message": "Nội dung sẽ bị admin xóa"},
            follow_redirects=True,
        )

        with app.app_context():
            db = get_db()
            entry = db.execute("SELECT id FROM entries WHERE name = ?", ("Bản ghi cần xóa",)).fetchone()
            entry_id = entry["id"]

        # Admin đăng nhập bằng mã PIN 8888
        with self.client.session_transaction() as sess:
            sess["admin_authenticated"] = True

        # Admin gọi route xóa
        response = self.client.post(f"/admin/delete/{entry_id}", follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Kiểm tra bản ghi đã thực sự bị xóa khỏi Database
        with app.app_context():
            db = get_db()
            deleted_entry = db.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
            self.assertIsNone(deleted_entry)


if __name__ == "__main__":
    unittest.main()
