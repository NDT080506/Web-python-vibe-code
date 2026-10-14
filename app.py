"""
Ứng dụng Guestbook (Sổ lưu bút) - Phiên bản Phân Quyền Admin & Client.
Quy định quyền:
  - Phía Client: Chỉ được xem và viết lời nhắn (KHÔNG CÓ NÚT XÓA).
  - Phía Admin: Độc quyền xóa các bản ghi trong trang quản trị /admin/db (Bảo vệ bằng mã PIN 8888).
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
app.secret_key = "guestbook_admin_protected_secret_key_2026"

# Mã PIN bảo mật trang quản trị Database
ADMIN_SECRET_PIN = "8888"


def get_db() -> sqlite3.Connection:
    """Lấy kết nối SQLite cho request hiện tại thông qua đối tượng 'g'."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
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


# Bảng màu Gradient Rực Rỡ Bắt Mắt (Không có màu xanh)
AVATAR_GRADIENTS = [
    "linear-gradient(135deg, #ff007a 0%, #ff5e36 100%)",  # Neon Pink to Sunset Orange
    "linear-gradient(135deg, #7928ca 0%, #ff0080 100%)",  # Electric Violet to Hot Magenta
    "linear-gradient(135deg, #ff4b1f 0%, #ff9068 100%)",  # Fiery Coral to Peach
    "linear-gradient(135deg, #f12711 0%, #f5af19 100%)",  # Flame Red to Electric Mango
    "linear-gradient(135deg, #8a2387 0%, #e94057 50%, #f27121 100%)",  # Poly Sunset Trio
    "linear-gradient(135deg, #b000b5 0%, #ff3366 100%)",  # Deep Purple to Neon Raspberry
    "linear-gradient(135deg, #ff0844 0%, #ffb199 100%)",  # Cherry Blossom Pop
]

ACCENT_COLORS = ["#ff007a", "#ff5e36", "#7928ca", "#f5af19", "#e94057", "#ff3366"]


def get_avatar_info(name: str):
    """Tạo chữ cái đầu và gán màu gradient rực rỡ bắt mắt theo tên tác giả."""
    clean_name = name.strip() if name else "?"
    words = clean_name.split()
    if len(words) >= 2:
        initials = (words[0][0] + words[-1][0]).upper()
    else:
        initials = clean_name[:2].upper()

    hash_val = sum(ord(c) for c in clean_name)
    color_gradient = AVATAR_GRADIENTS[hash_val % len(AVATAR_GRADIENTS)]
    accent = ACCENT_COLORS[hash_val % len(ACCENT_COLORS)]
    return initials, color_gradient, accent


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
        "get_avatar_info": get_avatar_info,
        "format_time": format_time_display,
    }


# =====================================================================
# PHÍA CLIENT: CÔNG KHAI CHỈ ĐƯỢC XEM VÀ VIẾT (KHÔNG ĐƯỢC XÓA)
# =====================================================================

@app.route("/", methods=["GET"])
def index():
    """Trang chủ: Client chỉ xem danh sách các lời nhắn và nút viết lời nhắn."""
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
    """Route Thêm lời nhắn: Dành cho mọi khách ghé thăm."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not message:
            error = "Vui lòng nhập đầy đủ cả tên và nội dung lời nhắn (không được để trống)!"
            return render_template("add.html", error=error, name=name, message=message)

        # Lấy giờ thực tế hiện tại của hệ thống (Local Time / GMT+7)
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

        flash("✨ Lời nhắn của bạn đã được đăng thành công vào sổ lưu bút!", "success")
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

    # Nếu admin đã đăng nhập thì thực hiện xóa
    db = get_db()
    cursor = db.execute("SELECT id FROM entries WHERE id = ?", (entry_id,))
    entry = cursor.fetchone()

    if entry is None:
        flash(f"Lời nhắn #{entry_id} không tồn tại hoặc đã được xóa trước đó.", "warning")
    else:
        db.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        db.commit()
        flash(f"Đã xóa thành công lời nhắn #{entry_id} khỏi cơ sở dữ liệu.", "info")

    return redirect(url_for("admin_database"))


# =====================================================================
# PHÍA ADMIN: ĐỘC QUYỀN QUẢN TRỊ VÀ XÓA BẢN GHI (BẢO MẬT MÃ PIN)
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

    # Tính tổng số bản ghi thực tế trong cơ sở dữ liệu
    total_count = db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]

    # Tìm kiếm theo ID nếu có tham số search_id
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
    """
    Route XÓA ĐỘC QUYỀN của Admin:
    Chỉ Admin sau khi mở khóa mới thực thi được.
    """
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
    print("💖 SỔ LƯU BÚT FLASK (ADMIN-ONLY DELETE PROTECTION)")
    print(f"📁 Tệp Database:          {DATABASE_PATH}")
    print("🌐 Trang chủ công khai:    http://127.0.0.1:5000")
    print("🔐 Quản trị DB Bí mật:    http://127.0.0.1:5000/admin/db (Mã PIN: 8888)")
    print("=" * 65)
    app.run(debug=True, host="127.0.0.1", port=5000)
