from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import time
import httpx
import jwt
import uuid as _uuid_mod
from slowapi import Limiter
from slowapi.util import get_remote_address


# Bucket por IP. No decodificamos JWT sin verificación — un atacante puede
# falsificar el `sub` y bypassear el rate limit per-user.
limiter = Limiter(key_func=get_remote_address)
try:
    from jwt.algorithms import ECAlgorithm, RSAAlgorithm
    _asymmetric_supported = True
except ImportError:
    _asymmetric_supported = False

from src.config import settings


# ── Supabase JWKS cache con TTL ───────────────────────────────────────────────
# Cachea TODAS las keys del JWKS (no solo la primera) y refresca cada hora.
# Esto evita que la rotación de keys en Supabase tumbe los logins.

_JWKS_TTL = 3600  # 1 hora
_jwks_keys: list = []      # lista de (alg, key_obj)
_jwks_loaded_at: float = 0


def _load_supabase_keys() -> list:
    global _jwks_keys, _jwks_loaded_at
    now = time.time()
    if _jwks_keys and (now - _jwks_loaded_at) < _JWKS_TTL:
        return _jwks_keys
    if not settings.SUPABASE_URL:
        return []
    try:
        resp = httpx.get(
            f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json", timeout=5
        )
        jwks = resp.json()
        parsed: list = []
        if _asymmetric_supported:
            for key_data in jwks.get("keys", []):
                alg = key_data.get("alg", "")
                if alg == "ES256":
                    parsed.append(("ES256", ECAlgorithm.from_jwk(key_data)))
                elif alg in ("RS256", "RS384", "RS512"):
                    parsed.append((alg, RSAAlgorithm.from_jwk(key_data)))
        if parsed:
            _jwks_keys = parsed
            _jwks_loaded_at = now
    except Exception:
        pass
    return _jwks_keys


# ── Request models ────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class RefreshRequest(BaseModel):
    token: str


class UserUpdateMeRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    document_id: Optional[str] = None


class CreateOrderRequest(BaseModel):
    items: list
    shipping_address_id: Optional[str] = None
    notes: Optional[str] = None


class CreateTransactionRequest(BaseModel):
    order_id: str
    amount: float
    payment_method: str


class ShippingAddressRequest(BaseModel):
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    postal_code: str


class ForgotPasswordRequest(BaseModel):
    email: str
    redirect_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    new_password: str


class SetUserActiveRequest(BaseModel):
    is_active: bool


class ChangeUserRoleRequest(BaseModel):
    role_name: str


# ── Circuit-breaker helpers ───────────────────────────────────────────────────

def _upstream_error(e: httpx.HTTPError) -> HTTPException:
    if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


def _proxy_error(e: httpx.HTTPStatusError) -> HTTPException:
    """Re-raise upstream JSON errors aplanando `detail` a string cuando es posible.

    El upstream (microservicios FastAPI) ya responde con `{"detail": "..."}`.
    Si re-anidábamos el body completo dentro de un nuevo `detail`, el cliente
    terminaba recibiendo `{"detail": {"detail": "..."}}` y crasheaba al
    renderizar un objeto donde esperaba un string.
    """
    try:
        body = e.response.json()
        if isinstance(body, dict):
            detail = body.get("detail", body)
        else:
            detail = body
    except Exception:
        detail = e.response.text or str(e)
    return HTTPException(status_code=e.response.status_code, detail=detail)


# ── Auth dependency ───────────────────────────────────────────────────────────

def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.split(" ", 1)[1]

    expired = False

    # 1. Supabase public keys (ES256 / RS256). Audience SIEMPRE validada.
    for alg, pub_key in _load_supabase_keys():
        try:
            return jwt.decode(token, pub_key, algorithms=[alg], audience="authenticated")
        except jwt.ExpiredSignatureError:
            expired = True
        except jwt.InvalidTokenError:
            continue

    # 2. Fallback HS256 con SUPABASE_JWT_SECRET. Audience también requerida.
    secret = settings.SUPABASE_JWT_SECRET or settings.JWT_SECRET
    if secret:
        try:
            return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        except jwt.ExpiredSignatureError:
            expired = True
        except jwt.InvalidTokenError:
            pass

    if expired:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _get_role(user: dict) -> str:
    return (user.get("user_role") or user.get("role") or "").upper()


def require_role(*roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if _get_role(user) not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(roles)}",
            )
        return user
    return dependency


def require_client_only(user: dict = Depends(get_current_user)) -> dict:
    """Blocks ADMIN and SUPERADMIN — operation is for clients only."""
    role = _get_role(user)
    if role in ("ADMIN", "SUPERADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot perform this action",
        )
    return user


# ── Router ────────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api", tags=["proxy"])
_timeout = 30


def _internal_client() -> httpx.AsyncClient:
    """httpx.AsyncClient con header X-Internal-Auth para llamar microservicios internos."""
    headers = {}
    if settings.INTERNAL_API_SECRET:
        headers["X-Internal-Auth"] = settings.INTERNAL_API_SECRET
    return httpx.AsyncClient(timeout=_timeout, headers=headers)


# ── Auth (públicos) ───────────────────────────────────────────────────────────

@router.post("/auth/register")
@limiter.limit("5/minute")
async def register(request: Request, request_data: RegisterRequest):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.IDENTITY_SERVICE_URL}/auth/register",
                json=request_data.model_dump(),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, request_data: LoginRequest):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.IDENTITY_SERVICE_URL}/auth/login",
                json=request_data.model_dump(),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/auth/refresh")
@limiter.limit("10/minute")
async def refresh_token(request: Request, request_data: RefreshRequest):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.IDENTITY_SERVICE_URL}/auth/refresh",
                json={"token": request_data.token},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/auth/logout", status_code=204)
async def logout(authorization: str = Header(None),
                 user: dict = Depends(get_current_user)):
    token = authorization.split(" ", 1)[1] if authorization else ""
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.IDENTITY_SERVICE_URL}/auth/logout",
                params={"supabase_id": user["sub"]},
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/auth/forgot-password", status_code=204)
@limiter.limit("3/minute")
async def forgot_password(request: Request, request_data: ForgotPasswordRequest):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.IDENTITY_SERVICE_URL}/auth/forgot-password",
                json=request_data.model_dump(exclude_none=True),
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/auth/change-password", status_code=204)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    request_data: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.IDENTITY_SERVICE_URL}/auth/change-password",
                json={"supabase_id": user["sub"],
                      "new_password": request_data.new_password},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


# ── Usuario autenticado ───────────────────────────────────────────────────────

@router.get("/users/me")
async def get_me(user: dict = Depends(get_current_user)):
    try:
        async with _internal_client() as client:
            response = await client.get(
                f"{settings.IDENTITY_SERVICE_URL}/auth/me",
                params={"supabase_id": user["sub"]},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/users/me")
async def update_me(
    request_data: UserUpdateMeRequest,
    user: dict = Depends(get_current_user),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.IDENTITY_SERVICE_URL}/auth/me",
                params={"supabase_id": user["sub"]},
                json=request_data.model_dump(exclude_none=True),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


# ── Admin: gestión de usuarios (SUPERADMIN only) ──────────────────────────────

@router.get("/admin/usuarios")
async def admin_list_users(
    skip: int = 0,
    limit: int = 50,
    _user: dict = Depends(require_role("SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.get(
                f"{settings.IDENTITY_SERVICE_URL}/auth/admin/users",
                params={"skip": skip, "limit": limit},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/admin/usuarios/{user_id}/activo")
async def admin_set_user_active(
    user_id: str,
    request_data: SetUserActiveRequest,
    _user: dict = Depends(require_role("SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.IDENTITY_SERVICE_URL}/auth/admin/users/{user_id}/active",
                json=request_data.model_dump(),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/admin/usuarios/{user_id}/rol")
async def admin_change_user_role(
    user_id: str,
    request_data: ChangeUserRoleRequest,
    _user: dict = Depends(require_role("SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.IDENTITY_SERVICE_URL}/auth/admin/users/{user_id}/role",
                json=request_data.model_dump(),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


# ── Catálogo (lectura pública, escritura requiere ADMIN/SUPERADMIN) ───────────

@router.get("/productos")
async def list_products(
    skip: int = 0,
    limit: int = 20,
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    q: Optional[str] = None,
    active_only: Optional[bool] = None,
):
    # active_only is explicit from the frontend. Default true for the public catalog.
    # Admin pages should pass active_only=false to see inactive products too.
    effective_active_only = True if active_only is None else active_only
    params = {"skip": skip, "limit": limit, "active_only": str(effective_active_only).lower()}
    if category_id:
        params["category_id"] = category_id
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price
    if sort_by:
        params["sort_by"] = sort_by
    try:
        async with _internal_client() as client:
            if q:
                response = await client.get(
                    f"{settings.CATALOG_SERVICE_URL}/products/search",
                    params={"q": q, "skip": skip, "limit": limit},
                )
            else:
                response = await client.get(
                    f"{settings.CATALOG_SERVICE_URL}/products",
                    params=params,
                )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/productos/{product_id}")
async def get_product(product_id: str):
    try:
        async with _internal_client() as client:
            response = await client.get(
                f"{settings.CATALOG_SERVICE_URL}/products/{product_id}"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/categorias")
async def list_categories():
    try:
        async with _internal_client() as client:
            response = await client.get(f"{settings.CATALOG_SERVICE_URL}/categories")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/productos", status_code=201)
async def create_product(
    request_data: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.CATALOG_SERVICE_URL}/products",
                json=request_data,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/productos/{product_id}")
async def update_product(
    product_id: str,
    request_data: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.CATALOG_SERVICE_URL}/products/{product_id}",
                json=request_data,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.delete("/productos/{product_id}")
async def delete_product(
    product_id: str,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.delete(
                f"{settings.CATALOG_SERVICE_URL}/products/{product_id}"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


_ALLOWED_IMG_TYPES = {"image/jpeg", "image/png", "image/webp"}
_ALLOWED_IMG_EXTS = {"jpg", "jpeg", "png", "webp"}
_MAX_IMG_SIZE = 5 * 1024 * 1024  # 5MB


def _validate_image(file: UploadFile, contents: bytes) -> str:
    """Devuelve la extensión validada o lanza HTTPException."""
    if file.content_type not in _ALLOWED_IMG_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Permitidos: {sorted(_ALLOWED_IMG_TYPES)}",
        )
    if len(contents) > _MAX_IMG_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen excede 5MB",
        )
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archivo vacío",
        )
    ext = (file.filename or "image.jpg").rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED_IMG_EXTS:
        # Si la extensión del filename no es válida pero el content-type sí, asume jpg.
        ext = "jpg"
    return ext


async def _supabase_upload(bucket: str, path: str, contents: bytes, content_type: str) -> str:
    """Sube bytes a Supabase Storage via REST (sin SDK) y devuelve la URL pública."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase Storage not configured")
    storage_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    async with httpx.AsyncClient(timeout=30.0) as sb:
        resp = await sb.post(
            storage_url,
            content=contents,
            headers={
                "Authorization": f"Bearer {settings.SUPABASE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )
    if not resp.is_success:
        try:
            body = resp.json()
            err = body.get("message") or body.get("error") or resp.text
        except Exception:
            err = resp.text
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage {resp.status_code}: {err}",
        )
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


@router.post("/productos/{product_id}/imagen")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    contents = await file.read()
    ext = _validate_image(file, contents)
    path = f"products/{product_id}.{ext}"
    public_url = await _supabase_upload(
        "product-images", path, contents, file.content_type or "image/jpeg"
    )

    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.CATALOG_SERVICE_URL}/products/{product_id}",
                json={"image_url": public_url},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/categorias", status_code=201)
async def create_category(
    request_data: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.CATALOG_SERVICE_URL}/categories",
                json=request_data,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/categorias/{category_id}")
async def update_category(
    category_id: str,
    request_data: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.CATALOG_SERVICE_URL}/categories/{category_id}",
                json=request_data,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.delete("/categorias/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    _user: dict = Depends(require_role("SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.delete(
                f"{settings.CATALOG_SERVICE_URL}/categories/{category_id}"
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


# ── Pedidos ───────────────────────────────────────────────────────────────────

@router.get("/pedidos")
async def list_orders(
    skip: int = 0,
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            params: dict = {"skip": skip, "limit": limit}
            if is_admin:
                params["is_admin"] = "true"
            else:
                params["user_id"] = user["sub"]
            response = await client.get(
                f"{settings.ORDER_SERVICE_URL}/orders",
                params=params,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/pedidos/{order_id}")
async def get_order(order_id: str, user: dict = Depends(get_current_user)):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            response = await client.get(
                f"{settings.ORDER_SERVICE_URL}/orders/{order_id}",
                params={"user_id": user["sub"], "is_admin": str(is_admin).lower()},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/pedidos/{order_id}/items")
async def get_order_items(order_id: str, user: dict = Depends(get_current_user)):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            # Verify access first
            verify = await client.get(
                f"{settings.ORDER_SERVICE_URL}/orders/{order_id}",
                params={"user_id": user["sub"], "is_admin": str(is_admin).lower()},
            )
            verify.raise_for_status()
            response = await client.get(
                f"{settings.ORDER_SERVICE_URL}/orders/{order_id}/items",
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/pedidos", status_code=201)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    request_data: CreateOrderRequest,
    user: dict = Depends(require_client_only),
):
    try:
        async with _internal_client() as client:
            params: dict = {"user_id": user["sub"]}
            if user.get("email"):
                params["user_email"] = user["email"]
            response = await client.post(
                f"{settings.ORDER_SERVICE_URL}/orders",
                json=request_data.model_dump(),
                params=params,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/pedidos/{order_id}/status")
async def update_order_status(
    order_id: str,
    request_data: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.ORDER_SERVICE_URL}/orders/{order_id}/status",
                json=request_data,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/pedidos/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    user: dict = Depends(get_current_user),
):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.ORDER_SERVICE_URL}/orders/{order_id}/cancel",
                params={"user_id": user["sub"], "is_admin": str(is_admin).lower()},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


# ── Direcciones de envío (clientes only) ─────────────────────────────────────

@router.get("/addresses")
async def list_addresses(user: dict = Depends(require_client_only)):
    try:
        async with _internal_client() as client:
            response = await client.get(
                f"{settings.ORDER_SERVICE_URL}/orders/addresses",
                params={"user_id": user["sub"]},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/addresses", status_code=201)
async def create_address(
    request_data: ShippingAddressRequest,
    user: dict = Depends(require_client_only),
):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.ORDER_SERVICE_URL}/orders/addresses",
                json=request_data.model_dump(),
                params={"user_id": user["sub"]},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/addresses/{address_id}")
async def update_address(
    address_id: str,
    request_data: dict,
    user: dict = Depends(get_current_user),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.ORDER_SERVICE_URL}/orders/addresses/{address_id}",
                json=request_data,
                params={"user_id": user["sub"]},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.delete("/addresses/{address_id}", status_code=204)
async def delete_address(
    address_id: str,
    user: dict = Depends(get_current_user),
):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            response = await client.delete(
                f"{settings.ORDER_SERVICE_URL}/orders/addresses/{address_id}",
                params={"user_id": user["sub"], "is_admin": str(is_admin).lower()},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


# ── Pagos ─────────────────────────────────────────────────────────────────────

@router.get("/pagos/transactions")
async def list_transactions(
    skip: int = 0,
    limit: int = 20,
    user: dict = Depends(get_current_user),
):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            params: dict = {"skip": skip, "limit": limit}
            if is_admin:
                params["is_admin"] = "true"
            else:
                params["user_id"] = user["sub"]
            response = await client.get(
                f"{settings.PAYMENT_SERVICE_URL}/payments/transactions",
                params=params,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/pagos/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    user: dict = Depends(get_current_user),
):
    role = _get_role(user)
    is_admin = role in ("ADMIN", "SUPERADMIN")
    try:
        async with _internal_client() as client:
            response = await client.get(
                f"{settings.PAYMENT_SERVICE_URL}/payments/transactions/{transaction_id}",
                params={"user_id": user["sub"], "is_admin": str(is_admin).lower()},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/pagos/transactions")
@limiter.limit("5/minute")
async def create_transaction(
    request: Request,
    request_data: CreateTransactionRequest,
    user: dict = Depends(require_client_only),
):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.PAYMENT_SERVICE_URL}/payments/transactions",
                json=request_data.model_dump(),
                params={"user_id": user["sub"]},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/pagos/checkout")
@limiter.limit("10/minute")
async def wompi_checkout(
    request: Request,
    request_data: dict,
    user: dict = Depends(require_client_only),
):
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.PAYMENT_SERVICE_URL}/payments/wompi/checkout",
                json=request_data,
                params={"user_id": user["sub"]},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/marketing/public")
async def get_public_marketing():
    try:
        async with _internal_client() as client:
            response = await client.get(f"{settings.CATALOG_SERVICE_URL}/marketing/public")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.get("/marketing")
async def list_marketing(_user: dict = Depends(require_role("ADMIN", "SUPERADMIN"))):
    try:
        async with _internal_client() as client:
            response = await client.get(f"{settings.CATALOG_SERVICE_URL}/marketing")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/marketing", status_code=201)
async def create_marketing(
    body: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.post(f"{settings.CATALOG_SERVICE_URL}/marketing", json=body)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.put("/marketing/{content_id}")
async def update_marketing(
    content_id: str,
    body: dict,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.CATALOG_SERVICE_URL}/marketing/{content_id}", json=body
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.delete("/marketing/{content_id}", status_code=204)
async def delete_marketing(
    content_id: str,
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    try:
        async with _internal_client() as client:
            response = await client.delete(
                f"{settings.CATALOG_SERVICE_URL}/marketing/{content_id}"
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/marketing/{content_id}/imagen")
async def upload_marketing_image(
    content_id: str,
    file: UploadFile = File(...),
    _user: dict = Depends(require_role("ADMIN", "SUPERADMIN")),
):
    contents = await file.read()
    ext = _validate_image(file, contents)
    path = f"banners/{content_id}.{ext}"
    public_url = await _supabase_upload(
        "marketing", path, contents, file.content_type or "image/jpeg"
    )

    try:
        async with _internal_client() as client:
            response = await client.put(
                f"{settings.CATALOG_SERVICE_URL}/marketing/{content_id}",
                json={"image_url": public_url, "image_path": path},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise _proxy_error(e)
    except httpx.HTTPError as e:
        raise _upstream_error(e)


@router.post("/pagos/webhooks/wompi")
@limiter.limit("30/minute")
async def wompi_webhook(request: Request):
    """
    Proxy para webhooks de Wompi. Sin autenticación JWT — Wompi firma el payload
    con HMAC-SHA256 y el payment-service verifica la firma.
    """
    raw_body = await request.body()
    x_event_checksum = request.headers.get("X-Event-Checksum", "")
    forward_headers = {
        "Content-Type": "application/json",
        "X-Event-Checksum": x_event_checksum,
    }
    if settings.INTERNAL_API_SECRET:
        forward_headers["X-Internal-Auth"] = settings.INTERNAL_API_SECRET
    try:
        async with _internal_client() as client:
            response = await client.post(
                f"{settings.PAYMENT_SERVICE_URL}/payments/webhooks/wompi",
                content=raw_body,
                headers=forward_headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.HTTPError as e:
        raise _upstream_error(e)
