import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.models.db_models import User
from app.core.security import get_password_hash

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Check if admin exists
            result = await session.execute(select(User).where(User.username == "admin"))
            admin = result.scalar_one_or_none()
            
            if not admin:
                print("Seeding admin user...")
                hashed_pw = get_password_hash("password123")
                new_admin = User(
                    username="admin",
                    hashed_password=hashed_pw,
                    role="admin",
                    is_active=True
                )
                session.add(new_admin)
                print("Admin user created: admin / password123")
            else:
                print("Admin user already exists.")

if __name__ == "__main__":
    asyncio.run(seed())
