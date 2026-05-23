from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from ..config import settings
from urllib.parse import urlparse
import ssl

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _connect_args(url: str) -> dict:
    if "postgresql" not in url:
        return {}
    # asyncpg strips the Supabase project-ref suffix (e.g. "postgres.xyz") from
    # the username when it parses the URL itself; pass user/password explicitly.
    p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
    args: dict = {"ssl": _ssl_ctx}
    if p.username:
        args["user"] = p.username
    if p.password:
        args["password"] = p.password
    return args


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args=_connect_args(settings.DATABASE_URL),
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
