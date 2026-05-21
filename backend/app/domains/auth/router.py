from urllib.parse import quote
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.deps import get_current_user, _user_permissions
from app.core.rate_limit import has_rate_limit as _has_limiter, limiter
from app.domains.auth.schemas import (
    LoginRequest, TokenResponse, UserMeResponse,
    ProfileUpdateRequest, ProfileOut, PasswordChangeRequest,
    ForgotPasswordRequest, RegisterRequest, RefreshRequest, ResetPasswordRequest,
    UserListOut, UserCreateRequest, UserUpdateRequest,
)
from app.domains.auth.service import (
    create_access_token, verify_password, hash_password,
    revoke_token, create_password_reset_token, verify_password_reset_token,
    create_refresh_token, verify_refresh_token, revoke_refresh_token,
    revoke_all_user_tokens,
)
from app.domains.audit.service import log_audit
from app.config import settings
from app.infra.database import get_db
from app.infra.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
ACCESS_TOKEN_COOKIE = "bgts_access_token"
REFRESH_TOKEN_COOKIE = "bgts_refresh_token"


def _limit(rate: str):
    """Rate limit dekoratoru — slowapi yoksa no-op wrapper."""
    if _has_limiter and limiter is not None:
        return limiter.limit(rate)
    def _noop(func):
        return func
    return _noop


def _password_reset_url(token: str) -> str:
    frontend_base = (
        settings.cors_origin_list[0]
        if settings.cors_origin_list
        else "http://127.0.0.1:3000"
    ).rstrip("/")
    return f"{frontend_base}/reset-password?token={quote(token)}"


def _send_password_reset_email(recipient: str, token: str) -> bool:
    from app.domains.notifications.email_service import send_email

    reset_url = _password_reset_url(token)
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #0f172a;">
        <h2>BGTS parola sifirlama</h2>
        <p>Parolanizi yenilemek icin asagidaki baglantiyi kullanin.</p>
        <p>
          <a href="{reset_url}" style="display:inline-block;padding:10px 16px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;">
            Parolayi sifirla
          </a>
        </p>
        <p>Baglanti {settings.password_reset_token_expire_minutes} dakika boyunca gecerlidir.</p>
        <p>Eger bu istegi siz yapmadiysaniz bu e-postayi yok sayabilirsiniz.</p>
      </body>
    </html>
    """
    return send_email(
        recipient,
        "[BGTS] Parola sifirlama talimati",
        html_body,
    )


def _should_use_secure_cookies(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or forwarded_proto == "https"


def _set_auth_cookies(
    response: Response,
    request: Request,
    access_token: str,
    refresh_token: Optional[str],
) -> None:
    secure = _should_use_secure_cookies(request)
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            REFRESH_TOKEN_COOKIE,
            refresh_token,
            max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )


def _clear_auth_cookies(response: Response, request: Request) -> None:
    secure = _should_use_secure_cookies(request)
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/", secure=secure, httponly=True, samesite="lax")
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path="/", secure=secure, httponly=True, samesite="lax")


def _request_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is None:
        return None
    return request.client.host


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Basarili giris",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
                        "expires_in": 1800,
                    }
                }
            },
        },
        401: {"description": "Hatali e-posta veya parola"},
        422: {"description": "Gecersiz istek formati"},
    },
)
@_limit(settings.rate_limit_login)
def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Kullanici girisi yapar ve JWT token doner."""
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya parola hatalı",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hesap devre dışı")

    # "Beni hatırla" seçiliyse daha uzun TTL (default 7 gün) kullan.
    ttl_minutes = (
        settings.access_token_expire_minutes_remember_me
        if body.remember_me
        else settings.access_token_expire_minutes
    )
    access = create_access_token(
        user.id,
        extra_claims={"tenant": getattr(user, "tenant_id", "00000000-0000-0000-0000-000000000001")},
        expires_minutes=ttl_minutes,
    )
    user_agent = request.headers.get("user-agent", "")
    refresh = create_refresh_token(user.id, db, user_agent=user_agent)
    try:
        log_audit(
            db,
            actor_user_id=user.id,
            action="auth.login",
            resource_type="user",
            resource_id=user.id,
            payload={"remember_me": body.remember_me},
            ip=None,
        )
        db.commit()
    except Exception:
        # Audit/commit (şema uyumsuzluğu vb.) başarısızsa oturum açılışını engelleme.
        db.rollback()

    # SECURITY: httpOnly cookie üzerinden auth — XSS'e karşı koruma.
    # Token response body'sinde de döner (geri uyumluluk için, frontend
    # migrasyonu tamamlanınca kaldırılabilir).
    _set_auth_cookies(response, request, access, refresh)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ttl_minutes * 60,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Token'i iptal et (blacklist)."""
    auth_header = request.headers.get("Authorization", "")
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if token:
        revoke_token(token)
    _clear_auth_cookies(response, request)
    log_audit(
        db,
        actor_user_id=user.id,
        action="auth.logout",
        resource_type="user",
        resource_id=user.id,
        payload=None,
        ip=_request_ip(request),
    )
    db.commit()
    return {"ok": True, "message": "Basariyla cikis yapildi"}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: Request,
    response: Response,
    body: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Refresh token ile yeni access + refresh token al (token rotation)."""
    refresh_token_value = body.refresh_token or request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token gerekli",
        )
    try:
        user_id = verify_refresh_token(refresh_token_value, db)
    except ValueError as e:
        logger.warning("Refresh token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from None

    # Eski refresh token'i iptal et (rotation)
    revoke_refresh_token(refresh_token_value, db)

    # Re-fetch user to get current tenant_id for the new token
    from app.infra.models import User as _User
    _user = db.get(_User, user_id)
    _tenant = getattr(_user, "tenant_id", "00000000-0000-0000-0000-000000000001") if _user else "00000000-0000-0000-0000-000000000001"

    # Yeni token cifti oluştur
    new_access = create_access_token(user_id, extra_claims={"tenant": _tenant})
    new_refresh = create_refresh_token(user_id, db)
    db.commit()
    _set_auth_cookies(response, request, new_access, new_refresh)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout-all")
def logout_all(
    request: Request,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Tüm cihazlardan cikis yap — tüm refresh token'lari iptal et."""
    count = revoke_all_user_tokens(user.id, db)
    log_audit(
        db,
        actor_user_id=user.id,
        action="auth.logout_all",
        resource_type="user",
        resource_id=user.id,
        payload={"revoked_tokens": count},
        ip=_request_ip(request),
    )
    _clear_auth_cookies(response, request)
    db.commit()
    return {"ok": True, "message": f"{count} oturum sonlandirildi"}


@router.get("/me", response_model=UserMeResponse)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserMeResponse:
    """Oturumdaki kullanici bilgilerini getirir."""
    return UserMeResponse(
        id=user.id,
        email=user.email,
        full_name=getattr(user, "full_name", None),
        roles=[r.name for r in user.roles],
        permissions=sorted(_user_permissions(user)),
        tenant_id=getattr(user, "tenant_id", None),
    )


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: Annotated[User, Depends(get_current_user)]):
    """Kullanici profil bilgilerini getirir."""
    return ProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        department=user.department,
        roles=[r.name for r in user.roles],
        created_at=str(user.created_at) if user.created_at else None,
    )


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    body: ProfileUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Kullanici profil bilgilerini gunceller."""
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.phone is not None:
        user.phone = body.phone
    if body.department is not None:
        user.department = body.department
    db.commit()
    db.refresh(user)
    return ProfileOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        department=user.department,
        roles=[r.name for r in user.roles],
        created_at=str(user.created_at) if user.created_at else None,
    )


@router.put("/password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Kullanici parolasini degistirir."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mevcut şifre hatalı")
    user.password_hash = hash_password(body.new_password)
    log_audit(
        db,
        actor_user_id=user.id,
        action="auth.change_password",
        resource_type="user",
        resource_id=user.id,
        payload=None,
        ip=_request_ip(request),
    )
    db.commit()
    return {"ok": True, "message": "Şifre başarıyla değiştirildi"}


@router.post("/forgot-password")
@_limit(settings.rate_limit_register)
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Annotated[Session, Depends(get_db)]):
    """Şifre sıfırlama — token üret, e-posta ile kullanıcıya gönder.

    Güvenlik: Kullanıcı mevcut olsa da olmasa da aynı yanıt döner
    (enumeration koruması). Gerçek e-posta yalnızca kullanıcı varsa
    EMAIL_BACKEND üzerinden yollanır.
    """
    from app.services.email_service import (
        build_password_reset_email,
        send_email,
    )

    user = db.scalar(select(User).where(User.email == body.email))
    if user:
        reset_token = create_password_reset_token(user.id)
        base = settings.app_public_url.rstrip("/")
        reset_url = f"{base}/reset-password?token={reset_token}"
        send_email(
            build_password_reset_email(
                to=user.email,
                reset_url=reset_url,
                full_name=getattr(user, "full_name", None),
            )
        )
        log_audit(
            db,
            actor_user_id=user.id,
            action="auth.forgot_password",
            resource_type="user",
            resource_id=user.id,
            payload=None,
            ip=None,
        )
        db.commit()
    # Güvenlik: Kullanıcı var ya da yok, aynı yanıt
    return {"ok": True, "message": "Şifre sıfırlama bağlantısı gönderildi"}


@router.post("/reset-password")
@_limit(settings.rate_limit_register)
def reset_password(request: Request, body: ResetPasswordRequest, db: Annotated[Session, Depends(get_db)]):
    """Token ile şifre sifirlama."""
    user_id = verify_password_reset_token(body.token)
    if not user_id:
        raise HTTPException(400, "Geçersiz veya süresi dolmus token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Kullanıcı bulunamadi")
    user.password_hash = hash_password(body.new_password)
    revoke_all_user_tokens(user.id, db)
    log_audit(
        db,
        actor_user_id=user.id,
        action="auth.reset_password",
        resource_type="user",
        resource_id=user.id,
        payload=None,
        ip=_request_ip(request),
    )
    db.commit()
    return {"ok": True, "message": "Şifre basariyla degistirildi"}


@router.post("/register", response_model=TokenResponse, status_code=201)
@_limit(settings.rate_limit_register)
def register(request: Request, body: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    """Yeni kullanici kaydeder."""
    if not settings.allow_self_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Açık kayit devre disi. Yoneticiyle iletisime gecin.",
        )
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayıtlı")
    from app.infra.models import Role, sd_user_roles
    default_role = db.scalar(select(Role).where(Role.name == "operator"))
    if default_role is None:
        default_role = db.scalar(select(Role).where(Role.name == "viewer"))
    new_user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
    )
    db.add(new_user)
    db.flush()
    if default_role:
        db.execute(sd_user_roles.insert().values(user_id=new_user.id, role_id=default_role.id))
    log_audit(
        db,
        actor_user_id=new_user.id,
        action="auth.register",
        resource_type="user",
        resource_id=new_user.id,
        payload=None,
        ip=_request_ip(request),
    )
    db.commit()
    token = create_access_token(new_user.id)

    # Welcome email — best-effort. Never block the response on email.
    try:
        from app.domains.billing.notifier import notify_welcome
        notify_welcome(to=new_user.email, full_name=new_user.full_name or "")
    except Exception:
        logger.warning("welcome email failed for user %s", new_user.email, exc_info=True)

    return TokenResponse(access_token=token)


# ── Admin User Management ──────────────────────────────────────────

@router.get("/users", response_model=list[UserListOut])
def list_users(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Kullanicilari listeler."""
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli")
    users = list(db.scalars(
        select(User).options(joinedload(User.roles)).order_by(User.created_at.desc())
    ))
    return [
        UserListOut(
            id=u.id, email=u.email, full_name=u.full_name,
            department=u.department, is_active=u.is_active,
            roles=[r.name for r in u.roles],
            created_at=str(u.created_at) if u.created_at else None,
        )
        for u in users
    ]


@router.post("/users", response_model=UserListOut, status_code=201)
def create_user(
    body: UserCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Yoneticinin yeni kullanici olusturmasini saglar."""
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli")
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bu e-posta zaten kayıtlı")

    # Plan-gate: enforce team_size limit for the admin's tenant.
    from app.domains.billing.gating import enforce_capacity
    enforce_capacity(db, user.tenant_id, "team_size")

    from app.infra.models import Role, sd_user_roles
    new_user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
        tenant_id=user.tenant_id,  # invitees join the inviter's tenant
    )
    db.add(new_user)
    db.flush()
    target_role = db.scalar(select(Role).where(Role.name == body.role))
    if target_role:
        db.execute(sd_user_roles.insert().values(user_id=new_user.id, role_id=target_role.id))
    db.commit()
    db.refresh(new_user)
    return UserListOut(
        id=new_user.id, email=new_user.email, full_name=new_user.full_name,
        department=new_user.department, is_active=new_user.is_active,
        roles=[r.name for r in new_user.roles],
        created_at=str(new_user.created_at) if new_user.created_at else None,
    )


@router.put("/users/{user_id}", response_model=UserListOut)
def update_user(
    user_id: str,
    body: UserUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Kullanici bilgilerini ve rolunu gunceller."""
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı")
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.department is not None:
        target.department = body.department
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.role is not None:
        from app.infra.models import Role, sd_user_roles
        db.execute(sd_user_roles.delete().where(sd_user_roles.c.user_id == user_id))
        new_role = db.scalar(select(Role).where(Role.name == body.role))
        if new_role:
            db.execute(sd_user_roles.insert().values(user_id=user_id, role_id=new_role.id))
    db.commit()
    db.refresh(target)
    return UserListOut(
        id=target.id, email=target.email, full_name=target.full_name,
        department=target.department, is_active=target.is_active,
        roles=[r.name for r in target.roles],
        created_at=str(target.created_at) if target.created_at else None,
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Kullaniciyi pasif duruma alir."""
    perms = _user_permissions(user)
    if "admin.*" not in perms:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin yetkisi gerekli")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kullanıcı bulunamadı")
    target.is_active = False
    db.commit()
