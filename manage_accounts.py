"""Local administrative bootstrap; no predefined administrator credentials."""
import argparse
import getpass
import json
from pathlib import Path

from api import DB, create_admin, migrate_auth_database


def main():
    parser = argparse.ArgumentParser(description="Quản lý tài khoản cục bộ của Web hỗ trợ lập trình.")
    parser.add_argument("command", choices=("create-admin", "migrate"))
    parser.add_argument("--db", type=Path, default=DB, help="Đường dẫn CSDL tài khoản")
    parser.add_argument("--email", help="Email quản trị mới; không tự nâng quyền tài khoản có sẵn")
    parser.add_argument("--name", help="Họ và tên quản trị")
    arguments = parser.parse_args()
    if arguments.command == "migrate":
        print(json.dumps(migrate_auth_database(arguments.db), ensure_ascii=False, indent=2))
        return
    email = arguments.email or input("Email quản trị mới: ").strip()
    name = arguments.name or input("Họ và tên quản trị: ").strip()
    password = getpass.getpass("Mật khẩu quản trị (ít nhất 12 ký tự): ")
    if password != getpass.getpass("Nhập lại mật khẩu: "):
        raise ValueError("Hai mật khẩu không khớp; chưa tạo quản trị.")
    result = create_admin(arguments.db, email, name, password)
    print("Đã tạo quản trị: " + result["username"] + ". Đăng nhập bằng email và mật khẩu vừa nhập.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from None
