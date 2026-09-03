from getpass import getpass

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database.models import User


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def main():
    username = input("Enter admin username: ").strip()
    password = getpass("Enter admin password: ")

    if not username or not password:
        print("Username and password are required.")
        return

    db: Session = SessionLocal()

    try:
        existing_user = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if existing_user:
            print("Username already exists.")
            return

        admin = User(
            username=username,
            password_hash=pwd_context.hash(password),
            role="ADMIN",
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print(f"Admin user '{username}' created successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()