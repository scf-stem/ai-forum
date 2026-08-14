"""Small audited administration CLI.

Usage: ``python -m app.cli set-admin user@example.com``.
"""
import argparse
import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.ops import EvaluationCase
from app.evaluation_dataset import dataset_rows


async def set_admin(email: str, enabled: bool) -> None:
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"user not found: {email}")
        user.is_admin = enabled
        await db.commit()
        print(f"{email}: is_admin={enabled}")


async def seed_gold_set(email: str, version: str) -> None:
    async with AsyncSessionLocal() as db:
        admin = (await db.execute(select(User).where(
            User.email == email.lower(), User.is_admin.is_(True)))).scalar_one_or_none()
        if admin is None:
            raise SystemExit("creator must be an existing administrator")
        created = 0
        for row in dataset_rows(version):
            exists = (await db.execute(select(EvaluationCase.id).where(
                EvaluationCase.version == version,
                EvaluationCase.question == row["question"]))).scalar_one_or_none()
            if not exists:
                db.add(EvaluationCase(**row, created_by=admin.id)); created += 1
        await db.commit()
        print(f"gold set {version}: created={created}, total=100")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("set-admin")
    command.add_argument("email")
    command.add_argument("--disable", action="store_true")
    seed = subparsers.add_parser("seed-gold-set")
    seed.add_argument("email")
    seed.add_argument("--version", default="v1")
    args = parser.parse_args()
    if args.command == "set-admin":
        asyncio.run(set_admin(args.email, not args.disable))
    elif args.command == "seed-gold-set":
        asyncio.run(seed_gold_set(args.email, args.version))


if __name__ == "__main__":
    main()
