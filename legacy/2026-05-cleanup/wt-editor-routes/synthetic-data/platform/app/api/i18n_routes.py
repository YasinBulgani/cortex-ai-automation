"""
Çoklu Dil Desteği (i18n) API Rotaları.

Bu modül, SyntheticBankData uygulamasının locale yönetimi
ve çeviri hizmeti için FastAPI rotalarını sağlar.
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

# Pydantic models
class TranslationKey(BaseModel):
    """Tek bir çeviri anahtarı için istek modeli."""
    key: str = Field(..., description="Çevirinin anahtarı (örn: 'buttons.save')")
    locale: Optional[str] = Field(None, description="Locale kodu (tr, en vb.). Sunucu varsayılanı kullanılır.")
    params: Optional[Dict[str, Any]] = Field(None, description="String format parametreleri")


class BatchTranslationRequest(BaseModel):
    """Toplu çeviri isteği modeli."""
    keys: List[str] = Field(..., description="Çevirisi istenen anahtarlar")
    locale: Optional[str] = Field(None, description="Locale kodu")


class LocaleUpdate(BaseModel):
    """Locale güncelleme isteği modeli."""
    translations: Dict[str, Any] = Field(..., description="Güncellenecek çeviriler")
    description: Optional[str] = Field(None, description="Güncelleme açıklaması")


class TranslationResponse(BaseModel):
    """Çeviri yanıt modeli."""
    key: str = Field(..., description="Çevirinin anahtarı")
    locale: str = Field(..., description="Kullanılan locale kodu")
    value: str = Field(..., description="Çevirinin değeri")


class LocaleInfo(BaseModel):
    """Locale bilgileri modeli."""
    code: str = Field(..., description="Locale kodu (tr, en vb.)")
    name: str = Field(..., description="Locale'in adı")
    is_default: bool = Field(..., description="Varsayılan locale mi?")
    is_rtl: bool = Field(False, description="Sağdan sola yazılır mı?")


class BatchTranslationResponse(BaseModel):
    """Toplu çeviri yanıt modeli."""
    locale: str = Field(..., description="Kullanılan locale kodu")
    translations: Dict[str, str] = Field(..., description="Anahtarlar ve çeviriler")
    missing_keys: List[str] = Field(..., description="Bulunamayan anahtarlar")


def create_i18n_router(i18n_service) -> APIRouter:
    """
    I18n API rotalarını oluşturur.

    Args:
        i18n_service: I18nService örneği

    Returns:
        FastAPI APIRouter
    """
    router = APIRouter(
        prefix="/api/v1/i18n",
        tags=["Çoklu Dil Desteği"],
        responses={404: {"description": "Bulunamadı"}, 400: {"description": "Geçersiz istek"}}
    )

    @router.get(
        "/locales",
        summary="Kullanılabilir Locale'leri Listele",
        description="Platformda kullanılabilir tüm locale kodlarını döndürür.",
        response_model=List[LocaleInfo]
    )
    async def get_locales():
        """
        Kullanılabilir locale'leri döndürür.

        Returns:
            Kullanılabilir locale'lerin listesi
        """
        locales = i18n_service.get_available_locales()
        result = []

        for locale in locales:
            result.append(
                LocaleInfo(
                    code=locale,
                    name=i18n_service.translate("app_name", locale=locale),
                    is_default=locale == i18n_service.default_locale,
                    is_rtl=locale in ["ar", "he", "fa"]  # Sağdan sola yazılır diller
                )
            )

        return result

    @router.get(
        "/locales/{locale_code}",
        summary="Belirli Locale'i Al",
        description="Belirtilen locale koduna ait tüm çevirileri döndürür.",
        response_model=Dict[str, Any]
    )
    async def get_locale(locale_code: str):
        """
        Belirtilen locale'in tüm çevirilerini döndürür.

        Args:
            locale_code: Locale kodu (tr, en vb.)

        Returns:
            Çevirileri içeren sözlük

        Raises:
            HTTPException: Locale bulunamadı
        """
        if locale_code not in i18n_service.get_available_locales():
            raise HTTPException(
                status_code=404,
                detail=f"Locale bulunamadı: {locale_code}"
            )

        # _locales sözlüğünden locale verilerini al
        try:
            locale_data = i18n_service._locales.get(locale_code, {})
            if not locale_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Locale verileri yüklenemedi: {locale_code}"
                )
            return locale_data
        except Exception as e:
            logger.error(f"Locale yükleme hatası ({locale_code}): {e}")
            raise HTTPException(
                status_code=500,
                detail="Locale verileri yüklenirken hata oluştu"
            )

    @router.put(
        "/locales/{locale_code}",
        summary="Locale'i Güncelle",
        description="Belirtilen locale koduna ait çevirileri günceller.",
        response_model=Dict[str, str]
    )
    async def update_locale(locale_code: str, update: LocaleUpdate):
        """
        Locale'i günceller.

        Args:
            locale_code: Locale kodu
            update: Güncelleme verileri

        Returns:
            Güncellenmiş locale bilgileri

        Raises:
            HTTPException: Locale bulunamadı veya güncelleme başarısız
        """
        if locale_code not in i18n_service.get_available_locales():
            raise HTTPException(
                status_code=404,
                detail=f"Locale bulunamadı: {locale_code}"
            )

        try:
            # Mevcut locale verilerini al
            locale_data = i18n_service._locales.get(locale_code, {})

            # Yeni çevirileri ekle/güncelle (basit güncelleme)
            def merge_translations(target, source):
                """Çevirileri özyinelemeli olarak birleştir."""
                for key, value in source.items():
                    if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                        merge_translations(target[key], value)
                    else:
                        target[key] = value

            merge_translations(locale_data, update.translations)
            i18n_service._locales[locale_code] = locale_data

            logger.info(f"Locale güncellendi: {locale_code}")

            return {
                "status": "success",
                "message": f"Locale başarıyla güncellendi: {locale_code}",
                "updated_keys": len(update.translations)
            }
        except Exception as e:
            logger.error(f"Locale güncellemesi başarısız ({locale_code}): {e}")
            raise HTTPException(
                status_code=500,
                detail="Locale güncellemesi başarısız"
            )

    @router.get(
        "/translate",
        summary="Çeviri Al",
        description="Belirtilen anahtarın çevirisini döndürür.",
        response_model=TranslationResponse
    )
    async def translate(
        key: str = Query(..., description="Çevirinin anahtarı"),
        locale: Optional[str] = Query(None, description="Locale kodu"),
        **params
    ):
        """
        Çeviri döndürür.

        Args:
            key: Çevirinin anahtarı (örn: 'buttons.save')
            locale: Locale kodu (isteğe bağlı)
            **params: Format parametreleri

        Returns:
            Çeviri yanıtı

        Raises:
            HTTPException: Anahtarı geçersiz
        """
        if not key:
            raise HTTPException(
                status_code=400,
                detail="Anahtarı (key) sağlayın"
            )

        try:
            value = i18n_service.translate(key, locale=locale, **params)

            return TranslationResponse(
                key=key,
                locale=locale or i18n_service.current_locale,
                value=value
            )
        except Exception as e:
            logger.error(f"Çeviri hatası ({key}, {locale}): {e}")
            raise HTTPException(
                status_code=500,
                detail="Çeviri işlemi başarısız"
            )

    @router.post(
        "/translate/batch",
        summary="Toplu Çeviri Al",
        description="Birden fazla anahtarın çevirilerini toplu olarak döndürür.",
        response_model=BatchTranslationResponse
    )
    async def batch_translate(request: BatchTranslationRequest):
        """
        Toplu çeviri döndürür.

        Args:
            request: Toplu çeviri isteği

        Returns:
            Çeviriler ve eksik anahtarlar

        Raises:
            HTTPException: İstek geçersiz
        """
        if not request.keys:
            raise HTTPException(
                status_code=400,
                detail="En az bir anahtar sağlayın"
            )

        if len(request.keys) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Maksimum 1000 anahtar bir seferde çeviriye alınabilir"
            )

        try:
            locale = request.locale or i18n_service.current_locale
            translations = {}
            missing_keys = []

            for key in request.keys:
                value = i18n_service.translate(key, locale=locale)
                if value == key:  # Anahtarı bulunamamışsa
                    missing_keys.append(key)
                else:
                    translations[key] = value

            return BatchTranslationResponse(
                locale=locale,
                translations=translations,
                missing_keys=missing_keys
            )
        except Exception as e:
            logger.error(f"Toplu çeviri hatası: {e}")
            raise HTTPException(
                status_code=500,
                detail="Toplu çeviri işlemi başarısız"
            )

    @router.post(
        "/locale/set",
        summary="Varsayılan Locale'i Ayarla",
        description="Platformun varsayılan locale kodunu ayarlar.",
        response_model=Dict[str, str]
    )
    async def set_default_locale(locale_code: str = Query(..., description="Locale kodu")):
        """
        Varsayılan locale'i ayarlar.

        Args:
            locale_code: Yeni varsayılan locale kodu

        Returns:
            Sonuç mesajı

        Raises:
            HTTPException: Locale bulunamadı
        """
        if not i18n_service.set_default_locale(locale_code):
            raise HTTPException(
                status_code=404,
                detail=f"Locale bulunamadı: {locale_code}"
            )

        return {
            "status": "success",
            "message": f"Varsayılan locale ayarlandı: {locale_code}"
        }

    @router.post(
        "/locale/current",
        summary="Geçerli Locale'i Ayarla",
        description="Geçerli çalışma locale kodunu ayarlar.",
        response_model=Dict[str, str]
    )
    async def set_current_locale(locale_code: str = Query(..., description="Locale kodu")):
        """
        Geçerli locale'i ayarlar.

        Args:
            locale_code: Yeni geçerli locale kodu

        Returns:
            Sonuç mesajı

        Raises:
            HTTPException: Locale bulunamadı
        """
        if not i18n_service.set_current_locale(locale_code):
            raise HTTPException(
                status_code=404,
                detail=f"Locale bulunamadı: {locale_code}"
            )

        return {
            "status": "success",
            "message": f"Geçerli locale ayarlandı: {locale_code}"
        }

    @router.get(
        "/health",
        summary="Sağlık Kontrolü",
        description="I18n hizmetinin durumunu kontrol eder.",
        response_model=Dict[str, Any]
    )
    async def health_check():
        """
        I18n hizmetinin sağlığını kontrol eder.

        Returns:
            Sağlık durumu bilgileri
        """
        locales = i18n_service.get_available_locales()
        return {
            "status": "healthy",
            "service": "i18n",
            "available_locales": locales,
            "default_locale": i18n_service.default_locale,
            "current_locale": i18n_service.current_locale,
            "locale_count": len(locales)
        }

    return router
