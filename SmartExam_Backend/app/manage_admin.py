"""Grant admin to one existing account from the database owner's terminal."""

import argparse
import sys
from unicodedata import normalize

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_database_url, make_engine
from app.models import User


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cấp quyền admin cho một tài khoản đã đăng ký.")
    parser.add_argument("email", nargs="?", help="Email tài khoản; bỏ trống để nhập khi chạy.")
    args = parser.parse_args(argv)
    try:
        raw_email = args.email if args.email is not None else input("Email tài khoản đã đăng ký: ")
        email = str(
            TypeAdapter(EmailStr).validate_python(normalize("NFC", raw_email.strip()).casefold())
        )
    except (ValidationError, EOFError, KeyboardInterrupt):
        print("Chưa nhập email hợp lệ. Không thay đổi tài khoản.", file=sys.stderr)
        return 1

    engine = None
    try:
        engine = make_engine(get_database_url())
        with Session(engine) as session:
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                print("Không tìm thấy tài khoản. Hãy đăng ký email này trước.", file=sys.stderr)
                return 1
            if user.role == "admin":
                print("Tài khoản này đã có quyền admin.")
                return 0
            user.role = "admin"
            session.commit()
        print("Đã cấp quyền admin. Đăng xuất rồi đăng nhập lại trên trình duyệt.")
        return 0
    except SQLAlchemyError:
        print(
            "Không cập nhật được CSDL. Kiểm tra DATABASE_URL và chạy migration trước.",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
