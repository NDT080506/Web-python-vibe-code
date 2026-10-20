"""
Ứng dụng Guestbook (Sổ lưu bút) - Phiên bản BẢNG GHIM KỶ NIỆM (Corkboard & Sticky Notes).
Lấy cảm hứng từ bảng gỗ bần ghim các tấm note kỷ niệm phong cách hoài niệm, ấm áp.
Chức năng:
  - Client: Xem bảng note ghim, di chuột vào để bung nội dung và thu nhỏ khi rê ra ngoài.
  - Viết note: Tờ giấy ghi chú dán lên bảng bần.
  - Admin: Quản trị riêng tư bằng mã PIN 8888, độc quyền xóa.
"""

import os
import sqlite3
import sys
from datetime import datetime
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Đảm bảo in tiếng Việt và UTF-8 an toàn trên console Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Đường dẫn tuyệt đối
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "guestbook.db")

app = Flask(__name__, template_folder=BASE_DIR)
app.secret_key = "guestbook_corkboard_pinboard_key_2026"

# Mã PIN bảo mật trang quản trị Database
ADMIN_SECRET_PIN = "8888"


def get_db() -> sqlite3.Connection:
    """Lấy kết nối SQLite cho request hiện tại thông qua đối tượng 'g'."""
    if "db" not in g:
        db_path = app.config.get("DATABASE", DATABASE_PATH)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Tự động đóng kết nối cơ sở dữ liệu khi kết thúc request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Khởi tạo database và bảng 'entries' nếu chưa tồn tại."""
    with app.app_context():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            """
        )
        db.commit()


# Danh sách các kiểu giấy Note Pastel, Đinh Ghim (Pushpin) và hoa văn giấy đa dạng như trong ảnh
NOTE_PALETTES = [
    {"bg": "#fffde7", "border": "#fff59d", "pin": "#e53935", "tape": "rgba(255, 235, 59, 0.5)", "pattern": "blank"},   # Vàng bơ cổ điển
    {"bg": "#fce4ec", "border": "#f8bbd0", "pin": "#d81b60", "tape": "rgba(240, 98, 146, 0.4)", "pattern": "blank"},   # Hồng phấn kỷ niệm
    {"bg": "#fff3e0", "border": "#ffe0b2", "pin": "#fb8c00", "tape": "rgba(255, 183, 77, 0.4)", "pattern": "lined"},   # Cam đào có dòng kẻ
    {"bg": "#f3e5f5", "border": "#e1bee7", "pin": "#8e24aa", "tape": "rgba(186, 104, 200, 0.4)", "pattern": "blank"},  # Tím oải hương
    {"bg": "#e8f5e9", "border": "#c8e6c9", "pin": "#2e7d32", "tape": "rgba(129, 199, 132, 0.4)", "pattern": "grid"},   # Xanh mint kẻ ô
    {"bg": "#fefae0", "border": "#faedcd", "pin": "#c2410c", "tape": "rgba(212, 163, 115, 0.4)", "pattern": "lined"},  # Giấy mộc vintage
    {"bg": "#ffffff", "border": "#ece7de", "pin": "#e11d48", "tape": "rgba(203, 213, 225, 0.5)", "pattern": "polaroid"},# Trắng kem Polaroid
    {"bg": "#e0f2fe", "border": "#bae6fd", "pin": "#0284c7", "tape": "rgba(56, 189, 248, 0.4)", "pattern": "blank"},   # Xanh pastel dịu mát
]

# Góc xoay ngẫu nhiên tự nhiên như ghim tay trên bảng thật
ROTATION_ANGLES = [-2.8, 2.2, -1.6, 3.1, -2.1, 1.8, -3.4, 2.7, -1.2, 3.5, -2.5, 2.0]


def get_note_style(entry_id: int):
    """Lấy kiểu màu giấy note, màu đinh ghim và góc xoay cố định theo ID."""
    idx = int(entry_id) if entry_id else 0
    palette = NOTE_PALETTES[idx % len(NOTE_PALETTES)]
    rotation = ROTATION_ANGLES[idx % len(ROTATION_ANGLES)]
    return palette, rotation


def format_time_display(dt_str: str) -> str:
    """
    Định dạng chuỗi ngày giờ từ SQLite thành dạng thân thiện chuẩn giờ Việt Nam:
    Ví dụ: '2026-10-14 21:36:45' -> '21:36:45 - 14/10/2026'
    """
    if not dt_str:
        return ""
    try:
        dt = datetime.strptime(str(dt_str).strip(), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M:%S - %d/%m/%Y")
    except Exception:
        return str(dt_str)


@app.context_processor
def utility_processor():
    return {
        "get_note_style": get_note_style,
        "format_time": format_time_display,
    }


# =====================================================================
# PHÍA CLIENT: BẢNG GHIM GỖ BẦN HIỂN THỊ CÁC TỜ NOTE KỶ NIỆM
# =====================================================================

@app.route("/", methods=["GET"])
def index():
    """Trang chủ: Bảng ghim bần (Corkboard) chứa toàn bộ các tờ note."""
    db = get_db()
    entries = db.execute(
        """
        SELECT id, name, message, created_at
        FROM entries
        ORDER BY id DESC
        """
    ).fetchall()
    return render_template("index.html", entries=entries, total_entries=len(entries))


@app.route("/add", methods=["GET", "POST"])
def add_entry():
    """Route Viết lời nhắn mới: Trình bày dạng tờ giấy note đặt trên bàn gỗ."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not message:
            error = "Vui lòng nhập đầy đủ cả tên và nội dung lời nhắn (không được để trống)!"
            return render_template("add.html", error=error, name=name, message=message)

        current_local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db = get_db()
        db.execute(
            """
            INSERT INTO entries (name, message, created_at)
            VALUES (?, ?, ?)
            """,
            (name, message, current_local_time),
        )
        db.commit()

        flash("📌 Đã ghim thành công lời nhắn của bạn lên bảng kỷ niệm!", "success")
        return redirect(url_for("index"))

    return render_template("add.html", error=None, name="", message="")


@app.route("/delete/<int:entry_id>", methods=["GET", "POST"])
def delete_entry(entry_id: int):
    """
    Chặn toàn bộ phía client tự ý xóa bản ghi.
    Nếu người dùng chưa xác thực quyền Admin -> từ chối và báo lỗi ngay.
    """
    if not session.get("admin_authenticated"):
        flash("⛔ Quyền bị từ chối: Chỉ quản trị viên (Admin) mới có quyền xóa các bản ghi!", "warning")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()

    if entry is None:
        flash(f"Lời nhắn #{entry_id} không tồn tại hoặc đã được xóa trước đó.", "warning")
    else:
        db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        db.commit()
        flash(f"Đã gỡ lời nhắn #{entry_id} khỏi bảng lưu bút.", "info")

    return redirect(url_for("admin_database"))


# =====================================================================
# PHÍA ADMIN: QUẢN TRỊ BÍ MẬT & ĐỘC QUYỀN XÓA (BẢO VỆ MÃ PIN 8888)
# =====================================================================

@app.route("/admin/db", methods=["GET", "POST"])
def admin_database():
    """Trang quản trị cơ sở dữ liệu SQLite bí mật (cần mã PIN 8888)."""
    pin = request.args.get("pin") or request.form.get("pin")
    if pin == ADMIN_SECRET_PIN:
        session["admin_authenticated"] = True

    if request.args.get("action") == "logout":
        session.pop("admin_authenticated", None)
        flash("Đã khóa trang quản trị cơ sở dữ liệu.", "info")
        return redirect(url_for("index"))

    if not session.get("admin_authenticated"):
        login_error = "Mã PIN bảo mật không chính xác!" if request.method == "POST" else None
        return render_template("admin_login.html", error=login_error)

    db = get_db()
    schema_info = db.execute("PRAGMA table_info(entries)").fetchall()

    total_count = db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]

    search_id = request.args.get("search_id", "").strip()
    if search_id and search_id.isdigit():
        entries = db.execute(
            "SELECT * FROM entries WHERE id = ? ORDER BY id DESC",
            (int(search_id),),
        ).fetchall()
    else:
        entries = db.execute("SELECT * FROM entries ORDER BY id DESC").fetchall()

    file_size_bytes = os.path.getsize(DATABASE_PATH) if os.path.exists(DATABASE_PATH) else 0

    return render_template(
        "admin_db.html",
        schema=schema_info,
        entries=entries,
        db_path=DATABASE_PATH,
        file_size_bytes=file_size_bytes,
        total_records=total_count,
        search_id=search_id,
    )


@app.route("/admin/delete/<int:entry_id>", methods=["POST"])
def admin_delete_entry(entry_id: int):
    """Route XÓA ĐỘC QUYỀN của Admin."""
    if not session.get("admin_authenticated"):
        flash("⛔ Bạn cần đăng nhập mã PIN để thực hiện thao tác xóa!", "warning")
        return redirect(url_for("admin_database"))

    db = get_db()
    cursor = db.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()

    if entry is None:
        flash(f"Bản ghi #{entry_id} không tồn tại hoặc đã được xóa trước đó.", "warning")
    else:
        db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        db.commit()
        flash(f"🗑️ Đã xóa vĩnh viễn bản ghi #{entry_id} khỏi SQLite!", "info")

    return redirect(url_for("admin_database"))


if __name__ == "__main__":
    init_db()
    print("=" * 65)
    print("📌 SỔ LƯU BÚT BẢNG GHIM GỖ BẦN (CORKBOARD EDITION)")
    print(f"📁 Tệp Database:          {DATABASE_PATH}")
    print("🌐 Bảng ghim công khai:    http://127.0.0.1:5000")
    print("🔐 Quản trị DB Bí mật:    http://127.0.0.1:5000/admin/db (Mã PIN: 8888)")
    print("=" * 65)
    app.run(debug=True, host="127.0.0.1", port=5000)
