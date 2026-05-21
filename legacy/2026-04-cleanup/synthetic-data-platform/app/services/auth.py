"""Kimlik doğrulama hizmeti - JWT token yönetimi ve şifre işlemleri."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from app.config import settings


class AuthService:
    """
    Kimlik doğrulama hizmetleri.

    JWT token oluşturma/doğrulama, şifre hash işlemleri ve kullanıcı doğrulaması
    sağlayan sınıf.
    """

    security = HTTPBearer()

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Şifreyi bcrypt ile hash'le.

        Args:
            password: Şifrelenecek düz metin şifre

        Returns:
            str: Hash'lenmiş şifre
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Şifreyi hash ile doğrula.

        Args:
            password: Doğrulanacak düz metin şifre
            hashed_password: Veritabanında saklı hash'lenmiş şifre

        Returns:
            bool: Şifre doğru ise True, yanlış ise False
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def create_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        token_type: str = "access"
    ) -> str:
        """
        JWT token oluştur.

        Args:
            data: Token'a kodlanacak veriler
            expires_delta: Token'ın geçerliliği için özel süre (dakika cinsinden)
            token_type: Token tipi - "access" veya "refresh"

        Returns:
            str: Kodlanmış JWT token
        """
        to_encode = data.copy()

        # Token türüne göre varsayılan expiry zamanını ayarla
        if expires_delta is None:
            if token_type == "refresh":
                expire_minutes = settings.refresh_token_expiry_days * 24 * 60
            else:
                expire_minutes = settings.jwt_expiry_minutes
            expires_delta = timedelta(minutes=expire_minutes)

        # Expiry zamanını hesapla
        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        to_encode.update({
            "exp": expire,
            "iat": now,
            "type": token_type
        })

        # JWT'yi encode et
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm
        )

        return encoded_jwt

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        JWT token'ı doğrula ve payload'ını çıkar.

        Args:
            token: Doğrulanacak JWT token
            token_type: Beklenen token tipi - "access" veya "refresh"

        Returns:
            Dict[str, Any]: Token payload'ı

        Raises:
            HTTPException: Token geçersiz, süresi dolmuş veya yanlış tipe sahipse
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm]
            )

            # Token tipini kontrol et
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Geçersiz token tipi. Beklenen: {token_type}",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token'ın süresi dolmuştur",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token",
                headers={"WWW-Authenticate": "Bearer"}
            )

    @staticmethod
    def get_current_user(
        credentials: HTTPAuthCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        Mevcut kullanıcıyı Bearer token'ından çıkar.

        FastAPI dependency olarak kullanılır. Istek başlığında geçerli bir
        JWT token olması gerekir.

        Args:
            credentials: FastAPI tarafından sağlanan HTTP kimlik bilgileri

        Returns:
            Dict[str, Any]: Token payload'ı (kullanıcı verisi)

        Raises:
            HTTPException: Token geçersiz veya süresi dolmuş ise
        """
        token = credentials.credentials
        return AuthService.verify_token(token, token_type="access")

    @staticmethod
    def get_current_user_id(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> str:
        """
        Mevcut kullanıcının kimliğini al.

        Args:
            current_user: Mevcut kullanıcı (verify_token'dan)

        Returns:
            str: Kullanıcı ID'si

        Raises:
            HTTPException: Token'da user_id yoksa
        """
        user_id = current_user.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token'dan kullanıcı kimliği alınamadı",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user_id

    @staticmethod
    def create_token_pair(
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Access ve refresh token çiftini oluştur.

        Args:
            user_id: Kullanıcı ID'si
            additional_claims: Token'a eklenecek ek veriler

        Returns:
            Dict[str, str]: "access_token" ve "refresh_token" içeren sözlük
        """
        claims = {"sub": user_id}
        if additional_claims:
            claims.update(additional_claims)

        access_token = AuthService.create_token(
            data=claims,
            token_type="access"
        )

        refresh_token = AuthService.create_token(
            data={"sub": user_id},
            token_type="refresh"
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
