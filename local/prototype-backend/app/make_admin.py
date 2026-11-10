"""Make an existing account an admin (or back to a normal user), from the terminal only.

    .venv\\Scripts\\python -m app.make_admin ama@example.com
    .venv\\Scripts\\python -m app.make_admin ama@example.com user

There is deliberately no web endpoint for this: only someone with access to this computer
(and its database file) can create an admin.
"""

from __future__ import annotations

import sys

from app import auth


def main(args: list[str]) -> int:
    if len(args) not in (1, 2):
        print("Usage: python -m app.make_admin <email> [admin|user]")
        return 2
    email = args[0]
    role = args[1] if len(args) == 2 else auth.ROLE_ADMIN
    try:
        user = auth.set_role(email, role)
    except auth.AuthError as error:
        print(error)
        return 1
    print(f"{user.email} is now: {user.role}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
