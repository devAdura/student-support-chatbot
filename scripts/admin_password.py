"""Run privately to generate a hash; never commit the resulting value."""

from getpass import getpass
from werkzeug.security import generate_password_hash

if __name__ == "__main__":
    password = getpass("New administrator password (at least 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters.")
    if password != getpass("Confirm password: "):
        raise SystemExit("Passwords did not match.")
    print(generate_password_hash(password))
