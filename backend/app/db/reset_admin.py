import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.auth import User


async def reset_admin() -> None:
    settings = get_settings()
    email = str(settings.initial_admin_email).strip().lower()

    async with AsyncSessionFactory() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            raise RuntimeError(f"Usuário não encontrado: {email}. Execute o seed primeiro.")

        user.full_name = settings.initial_admin_name
        user.hashed_password = hash_password(settings.initial_admin_password)
        user.is_active = True
        user.is_superuser = True
        await session.commit()
        print(f"Administrador redefinido: {email}")


if __name__ == "__main__":
    asyncio.run(reset_admin())
