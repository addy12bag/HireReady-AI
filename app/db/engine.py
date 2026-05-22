from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

settings = get_settings()

is_sqlite = settings.database_url.startswith("sqlite")

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    **({} if is_sqlite else {"pool_size": 5, "max_overflow": 10}),
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
