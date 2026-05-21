"""Kimlik doğrulama API rotaları."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends, Body
from pydantic import BaseModel, Field, EmailStr, validator

from app.services.auth import AuthService

# Router oluştur
router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Kimlik Doğrulama"],
    responses={
        401: {"description": "Yetkisiz erişim"},
        422: {"description": "Doğrulama hatası"},
    }
)


# Request/Response Models
class LoginRequest(BaseModel):
    """Giriş isteği modeli."""

    email: EmailStr = Field(..., description="Kullanıcı e-posta adresi")
    password: str = Field(
        ...,
        min_length=8,
        max_length=255,
        description="Kullanıcı şifresi"
    )

    class Config:
        """Model yapılandırması."""
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!"
            }
        }


class RegisterRequest(BaseModel):
    """Kayıt isteği modeli."""

    email: EmailStr = Field(..., description="Kullanıcı e-posta adresi")
    password: str = Field(
        ...,
        min_length=8,
        max_length=255,
        description="Güçlü bir şifre"
    )
    password_confirm: str = Field(
        ...,
        description="Şifre doğrulama"
    )
    first_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Kullanıcının adı"
    )
    last_name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Kullanıcının soyadı"
    )

    @validator('password')
    def validate_password_strength(cls, v: str) -> str:
        """Şifre güvenliğini kontrol et."""
        if not any(char.isupper() for char in v):
            raise ValueError("Şifre en az bir büyük harf içermelidir")
        if not any(char.isdigit() for char in v):
            raise ValueError("Şifre en az bir rakam içermelidir")
        if not any(char in "!@#$%^&*" for char in v):
            raise ValueError("Şifre en az bir özel karakter içermelidir")
        return v

    @validator('password_confirm')
    def passwords_match(cls, v: str, values: Dict[str, Any]) -> str:
        """Şifrelerin eşleşmesini kontrol et."""
        if 'password' in values and v != values['password']:
            raise ValueError("Şifreler eşleşmiyor")
        return v

    class Config:
        """Model yapılandırması."""
        schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "password_confirm": "SecurePassword123!",
                "first_name": "Ahmet",
                "last_name": "Yılmaz"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Token yenileme isteği modeli."""

    refresh_token: str = Field(..., description="Refresh token")

    class Config:
        """Model yapılandırması."""
        schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class TokenResponse(BaseModel):
    """Token yanıtı modeli."""

    access_token: str = Field(..., description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    token_type: str = Field(default="bearer", description="Token tipi")
    expires_in: int = Field(..., description="Token'ın geçerlilik süresi (saniye)")

    class Config:
        """Model yapılandırması."""
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class UserInfo(BaseModel):
    """Kullanıcı bilgileri modeli."""

    id: str = Field(..., description="Kullanıcı ID'si")
    email: EmailStr = Field(..., description="E-posta adresi")
    first_name: str = Field(..., description="Adı")
    last_name: str = Field(..., description="Soyadı")
    is_active: bool = Field(default=True, description="Hesap aktif mi?")
    is_verified: bool = Field(default=False, description="E-posta doğrulanmış mı?")
    created_at: str = Field(..., description="Oluşturulma tarihi")

    class Config:
        """Model yapılandırması."""
        schema_extra = {
            "example": {
                "id": "user123",
                "email": "user@example.com",
                "first_name": "Ahmet",
                "last_name": "Yılmaz",
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-01-01T10:00:00Z"
            }
        }


class LogoutResponse(BaseModel):
    """Çıkış yanıtı modeli."""

    message: str = Field(..., description="Çıkış mesajı")
    success: bool = Field(default=True, description="Başarılı mı?")

    class Config:
        """Model yapılandırması."""
        schema_extra = {
            "example": {
                "message": "Başarıyla çıkış yapıldı",
                "success": True
            }
        }


# Endpoints
@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı Girişi",
    description="E-posta ve şifre ile kullanıcı girişi yapılır."
)
async def login(
    request: LoginRequest = Body(..., embed=False)
) -> TokenResponse:
    """
    Kullanıcı girişini gerçekleştir.

    Kimlik bilgilerini kontrol eder ve başarılı olması halinde access token
    ve refresh token döndürür.

    Args:
        request: Giriş kimlik bilgileri

    Returns:
        TokenResponse: Access token, refresh token ve token tipi

    Raises:
        HTTPException: Geçersiz kimlik bilgileri ise 401 hatası
    """
    # TODO: Veritabanından kullanıcı sorgula
    # user = await db.get_user_by_email(request.email)
    # if not user or not AuthService.verify_password(request.password, user.password_hash):
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Geçersiz e-posta veya şifre",
    #         headers={"WWW-Authenticate": "Bearer"}
    #     )

    # Şimdilik örnek kullanıcı döndür
    tokens = AuthService.create_token_pair(
        user_id="user123",
        additional_claims={
            "email": request.email,
            "name": "Örnek Kullanıcı"
        }
    )

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=1800  # 30 dakika
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yeni Kullanıcı Kaydı",
    description="Yeni kullanıcı hesabı oluşturur."
)
async def register(
    request: RegisterRequest = Body(..., embed=False)
) -> TokenResponse:
    """
    Yeni kullanıcı hesabı oluştur.

    Kullanıcının e-posta adresinin benzersiz olduğunu kontrol eder,
    şifreyi hash'ler ve yeni bir hesap oluşturur.

    Args:
        request: Kayıt bilgileri

    Returns:
        TokenResponse: Yeni kullanıcı için access ve refresh token

    Raises:
        HTTPException: E-posta zaten kullanımda ise 409 hatası
    """
    # TODO: E-posta benzersizliğini kontrol et
    # existing_user = await db.get_user_by_email(request.email)
    # if existing_user:
    #     raise HTTPException(
    #         status_code=status.HTTP_409_CONFLICT,
    #         detail="Bu e-posta zaten kullanımda"
    #     )

    # Şifreyi hash'le
    password_hash = AuthService.hash_password(request.password)

    # TODO: Veritabanına yeni kullanıcı ekle
    # new_user = User(
    #     email=request.email,
    #     password_hash=password_hash,
    #     first_name=request.first_name,
    #     last_name=request.last_name
    # )
    # await db.add_user(new_user)

    # Token çifti oluştur
    tokens = AuthService.create_token_pair(
        user_id="new_user_id",
        additional_claims={
            "email": request.email,
            "name": f"{request.first_name} {request.last_name}"
        }
    )

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=1800
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Token Yenileme",
    description="Refresh token kullanarak yeni access token alır."
)
async def refresh_token(
    request: RefreshTokenRequest = Body(..., embed=False)
) -> TokenResponse:
    """
    Refresh token kullanarak yeni access token al.

    Geçerli bir refresh token ile yeni access token ve refresh token alır.

    Args:
        request: Refresh token

    Returns:
        TokenResponse: Yeni access token ve refresh token

    Raises:
        HTTPException: Refresh token geçersiz ise 401 hatası
    """
    # Refresh token'ı doğrula
    payload = AuthService.verify_token(
        request.refresh_token,
        token_type="refresh"
    )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Yeni token çifti oluştur
    tokens = AuthService.create_token_pair(user_id=user_id)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=1800
    )


@router.get(
    "/me",
    response_model=UserInfo,
    status_code=status.HTTP_200_OK,
    summary="Mevcut Kullanıcı Bilgileri",
    description="Giriş yapmış kullanıcının bilgilerini döndürür."
)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user)
) -> UserInfo:
    """
    Giriş yapmış kullanıcının bilgilerini al.

    Token'dan çıkarılan kullanıcı bilgilerini döndürür.

    Args:
        current_user: Mevcut kullanıcı (token'dan)

    Returns:
        UserInfo: Kullanıcı bilgileri

    Raises:
        HTTPException: Token geçersiz ise 401 hatası
    """
    # TODO: Veritabanından tam kullanıcı verilerini sorgula
    # user = await db.get_user_by_id(current_user["sub"])

    return UserInfo(
        id=current_user.get("sub", ""),
        email=current_user.get("email", ""),
        first_name=current_user.get("first_name", ""),
        last_name=current_user.get("last_name", ""),
        is_active=True,
        is_verified=True,
        created_at="2024-01-01T10:00:00Z"
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı Çıkışı",
    description="Kullanıcıyı oturumdan çıkarır."
)
async def logout(
    current_user: Dict[str, Any] = Depends(AuthService.get_current_user)
) -> LogoutResponse:
    """
    Kullanıcıyı çıkış yap.

    Kullanıcının oturumunu sonlandırır. Token'ı geçersiz kılar.

    Args:
        current_user: Mevcut kullanıcı (token'dan)

    Returns:
        LogoutResponse: Çıkış başarılı mesajı

    Raises:
        HTTPException: Token geçersiz ise 401 hatası
    """
    # TODO: Token'ı blacklist'e ekle veya Redis'e oturum kaydını sil
    # user_id = current_user["sub"]
    # await redis.set(f"blacklist:{token}", "", ex=settings.jwt_expiry_minutes * 60)

    return LogoutResponse(
        message=f"Kullanıcı {current_user.get('email', 'unknown')} başarıyla çıkış yapıldı",
        success=True
    )
