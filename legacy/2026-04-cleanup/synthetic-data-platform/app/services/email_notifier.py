"""
E-posta Bildirim Hizmeti — SyntheticBankData

Bu modül smtplib ve email kütüphanesi kullanarak bildirim e-postaları gönderer.

Bildirim türleri:
  - Üretim Tamamlandı: Veri üretim işlemi başarıyla tamamlandığında
  - Kalite Uyarısı: Kalite metrikleri eşik değerlerin altına düştüğünde
  - Günlük Özet: Günlük operasyon özeti
  - Hata Bildirimi: Sistem hatası oluştuğunda

Özellikler:
  - HTML e-posta şablonları
  - Türkçe başlık ve içerik
  - Parametrik içerik ve dinamik veri
  - SMTP yapılandırması

Kullanım:
    from app.services.email_notifier import EmailNotifier

    notifier = EmailNotifier(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        sender_email="notifier@syntheticbank.com",
        sender_password="password"
    )

    notifier.send_generation_complete(
        recipient_email="admin@company.com",
        title="Müşteri Veritabanı",
        total_records=100000,
        success_rate=99.5
    )
"""

import logging
import smtplib
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# E-posta Bildirim Hizmeti
# ═══════════════════════════════════════════════════════════════════════════════


class EmailNotifier:
    """
    Sistem olaylarından e-posta bildirimler gönderer.

    Desteklenen bildirim türleri:
    - Üretim tamamlandı
    - Kalite uyarısı
    - Günlük özet
    - Hata bildirimi

    Özellikler:
    - HTML e-posta şablonları
    - Türkçe içerik
    - SMTP yapılandırması
    - Hata işleme ve loglama
    """

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        sender_email: str = "notifier@syntheticbank.com",
        sender_password: str = "",
        use_tls: bool = True,
        timeout: int = 10,
    ):
        """
        E-posta Bildirim Hizmeti'ni başlat.

        Args:
            smtp_host: SMTP sunucusu adresi
            smtp_port: SMTP sunucusu port numarası
            sender_email: Gönderici e-posta adresi
            sender_password: SMTP kimlik doğrulama şifresi
            use_tls: TLS şifreleme kullan
            timeout: Bağlantı zaman aşımı (saniye)
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.use_tls = use_tls
        self.timeout = timeout

    def _send_email(
        self,
        recipient_email: str,
        subject: str,
        html_content: str,
        cc_list: Optional[List[str]] = None,
    ) -> bool:
        """
        E-posta göndер.

        Args:
            recipient_email: Alıcı e-posta adresi
            subject: E-posta konusu
            html_content: E-posta HTML içeriği
            cc_list: CC alıcıları listesi

        Returns:
            Başarı durumu
        """
        try:
            # MIME mesajı oluştur
            message = MIMEMultipart("alternative")
            message["From"] = Header(self.sender_email, "utf-8")
            message["To"] = Header(recipient_email, "utf-8")
            message["Subject"] = Header(subject, "utf-8")

            if cc_list:
                message["Cc"] = ", ".join(cc_list)

            # HTML kısmını ekle
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)

            # SMTP bağlantısı kur ve gönder
            recipients = [recipient_email]
            if cc_list:
                recipients.extend(cc_list)

            with smtplib.SMTP(
                self.smtp_host,
                self.smtp_port,
                timeout=self.timeout,
            ) as server:
                if self.use_tls:
                    server.starttls()

                if self.sender_password:
                    server.login(self.sender_email, self.sender_password)

                server.sendmail(
                    self.sender_email,
                    recipients,
                    message.as_string(),
                )

            logger.info(
                f"E-posta gönderildi: {subject} → {recipient_email}"
            )
            return True

        except smtplib.SMTPException as exc:
            logger.error(f"SMTP hatası: {exc}")
            return False
        except Exception as exc:
            logger.error(f"E-posta gönderme hatası: {exc}")
            return False

    def _get_html_template(
        self,
        template_name: str,
        **kwargs: Any,
    ) -> str:
        """
        E-posta HTML şablonunu oluştur.

        Args:
            template_name: Şablon adı
            **kwargs: Şablonda kullanılacak parametreler

        Returns:
            HTML içeriği
        """
        templates = {
            "generation_complete": self._template_generation_complete,
            "quality_alert": self._template_quality_alert,
            "daily_summary": self._template_daily_summary,
            "error_notification": self._template_error_notification,
        }

        template_func = templates.get(template_name)
        if not template_func:
            logger.warning(f"Bilinmeyen şablon: {template_name}")
            return ""

        return template_func(**kwargs)

    # ───────────────────────────────────────────────────────────────────────────
    # Bildirim Metotları
    # ───────────────────────────────────────────────────────────────────────────

    def send_generation_complete(
        self,
        recipient_email: str,
        title: str,
        total_records: int,
        success_count: int,
        failure_count: int,
        generation_time: float,
        success_rate: float,
        cc_list: Optional[List[str]] = None,
    ) -> bool:
        """
        Veri üretim tamamlandı e-postası gönder.

        Args:
            recipient_email: Alıcı e-posta adresi
            title: Proje başlığı
            total_records: Toplam oluşturulan kayıt sayısı
            success_count: Başarılı kayıt sayısı
            failure_count: Başarısız kayıt sayısı
            generation_time: Üretim süresi (saniye)
            success_rate: Başarı oranı (yüzde)
            cc_list: CC alıcıları listesi

        Returns:
            Başarı durumu
        """
        subject = f"SyntheticBankData — {title} Üretim Tamamlandı"

        html_content = self._get_html_template(
            "generation_complete",
            title=title,
            total_records=total_records,
            success_count=success_count,
            failure_count=failure_count,
            generation_time=generation_time,
            success_rate=success_rate,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return self._send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            cc_list=cc_list,
        )

    def send_quality_alert(
        self,
        recipient_email: str,
        data_type: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        recommendation: str = "",
        cc_list: Optional[List[str]] = None,
    ) -> bool:
        """
        Kalite uyarısı e-postası gönder.

        Args:
            recipient_email: Alıcı e-posta adresi
            data_type: Veri türü (customer, transaction, vb.)
            metric_name: Kalite metriği adı
            current_value: Güncel değer
            threshold: Eşik değeri
            recommendation: Önerilen işlem
            cc_list: CC alıcıları listesi

        Returns:
            Başarı durumu
        """
        subject = f"⚠️ SyntheticBankData — Kalite Uyarısı: {metric_name}"

        html_content = self._get_html_template(
            "quality_alert",
            data_type=data_type,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            recommendation=recommendation,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return self._send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            cc_list=cc_list,
        )

    def send_daily_summary(
        self,
        recipient_email: str,
        summary_date: str,
        stats: Dict[str, Any],
        cc_list: Optional[List[str]] = None,
    ) -> bool:
        """
        Günlük özet e-postası gönder.

        Args:
            recipient_email: Alıcı e-posta adresi
            summary_date: Özet tarihi
            stats: İstatistik verisi
            cc_list: CC alıcıları listesi

        Returns:
            Başarı durumu
        """
        subject = f"SyntheticBankData — Günlük Özet ({summary_date})"

        html_content = self._get_html_template(
            "daily_summary",
            summary_date=summary_date,
            stats=stats,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return self._send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            cc_list=cc_list,
        )

    def send_error_notification(
        self,
        recipient_email: str,
        error_type: str,
        error_message: str,
        error_context: str = "",
        suggested_action: str = "",
        cc_list: Optional[List[str]] = None,
    ) -> bool:
        """
        Hata bildirimi e-postası gönder.

        Args:
            recipient_email: Alıcı e-posta adresi
            error_type: Hata türü
            error_message: Hata mesajı
            error_context: Hata bağlamı
            suggested_action: Önerilen işlem
            cc_list: CC alıcıları listesi

        Returns:
            Başarı durumu
        """
        subject = f"🚨 SyntheticBankData — Sistem Hatası: {error_type}"

        html_content = self._get_html_template(
            "error_notification",
            error_type=error_type,
            error_message=error_message,
            error_context=error_context,
            suggested_action=suggested_action,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        return self._send_email(
            recipient_email=recipient_email,
            subject=subject,
            html_content=html_content,
            cc_list=cc_list,
        )

    # ───────────────────────────────────────────────────────────────────────────
    # HTML E-posta Şablonları
    # ───────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _template_generation_complete(
        title: str,
        total_records: int,
        success_count: int,
        failure_count: int,
        generation_time: float,
        success_rate: float,
        timestamp: str,
    ) -> str:
        """Üretim tamamlandı şablonu."""
        return f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #1F4788; color: white; padding: 20px; text-align: center; }}
                    .content {{ background-color: #f5f5f5; padding: 20px; margin: 20px 0; }}
                    .stats-table {{ width: 100%; border-collapse: collapse; }}
                    .stats-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                    .stats-table tr:first-child {{ background-color: #1F4788; color: white; }}
                    .success {{ color: #28a745; font-weight: bold; }}
                    .failure {{ color: #dc3545; font-weight: bold; }}
                    .footer {{ text-align: center; font-size: 12px; color: #999; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Veri Üretim Tamamlandı ✓</h2>
                    </div>

                    <div class="content">
                        <p>Merhaba,</p>
                        <p><strong>{title}</strong> veri üretim işlemi başarıyla tamamlanmıştır.</p>

                        <table class="stats-table">
                            <tr>
                                <td><strong>Metrik</strong></td>
                                <td><strong>Değer</strong></td>
                            </tr>
                            <tr>
                                <td>Toplam Kayıt</td>
                                <td><strong>{total_records:,}</strong></td>
                            </tr>
                            <tr>
                                <td>Başarılı</td>
                                <td><span class="success">{success_count:,}</span></td>
                            </tr>
                            <tr>
                                <td>Başarısız</td>
                                <td><span class="failure">{failure_count:,}</span></td>
                            </tr>
                            <tr>
                                <td>Başarı Oranı</td>
                                <td><strong>{success_rate:.2f}%</strong></td>
                            </tr>
                            <tr>
                                <td>Üretim Süresi</td>
                                <td><strong>{generation_time:.2f} saniye</strong></td>
                            </tr>
                        </table>

                        <p style="margin-top: 20px;">
                            Rapor detayları için lütfen yönetim panelini ziyaret edin.
                        </p>
                    </div>

                    <div class="footer">
                        <p>Bu e-posta otomatik olarak gönderilmiştir.<br/>
                        Gönderim Zamanı: {timestamp}</p>
                    </div>
                </div>
            </body>
        </html>
        """

    @staticmethod
    def _template_quality_alert(
        data_type: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        recommendation: str,
        timestamp: str,
    ) -> str:
        """Kalite uyarısı şablonu."""
        return f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #ff9800; color: white; padding: 20px; text-align: center; }}
                    .alert {{ background-color: #fff3cd; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0; }}
                    .footer {{ text-align: center; font-size: 12px; color: #999; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Kalite Uyarısı ⚠️</h2>
                    </div>

                    <div class="alert">
                        <p><strong>{data_type}</strong> veri türü için <strong>{metric_name}</strong> metriği
                        eşik değerinin altına düşmüştür.</p>

                        <p style="margin: 15px 0;">
                            <strong>Güncel Değer:</strong> {current_value:.2f}%<br/>
                            <strong>Eşik Değeri:</strong> {threshold:.2f}%
                        </p>

                        <p><strong>Önerilen İşlem:</strong><br/>
                        {recommendation}</p>
                    </div>

                    <div class="footer">
                        <p>Bu e-posta otomatik olarak gönderilmiştir.<br/>
                        Gönderim Zamanı: {timestamp}</p>
                    </div>
                </div>
            </body>
        </html>
        """

    @staticmethod
    def _template_daily_summary(
        summary_date: str,
        stats: Dict[str, Any],
        timestamp: str,
    ) -> str:
        """Günlük özet şablonu."""
        stats_html = ""
        for key, value in stats.items():
            stats_html += f"<tr><td>{key}</td><td>{value}</td></tr>"

        return f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #1F4788; color: white; padding: 20px; text-align: center; }}
                    .content {{ background-color: #f5f5f5; padding: 20px; margin: 20px 0; }}
                    .stats-table {{ width: 100%; border-collapse: collapse; }}
                    .stats-table td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
                    .stats-table tr:first-child {{ background-color: #1F4788; color: white; }}
                    .footer {{ text-align: center; font-size: 12px; color: #999; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Günlük Özet Raporu</h2>
                        <p>{summary_date}</p>
                    </div>

                    <div class="content">
                        <p>Merhaba,</p>
                        <p>Aşağıda {summary_date} tarihinin özet istatistikleri yer almaktadır:</p>

                        <table class="stats-table">
                            <tr>
                                <td><strong>Metrik</strong></td>
                                <td><strong>Değer</strong></td>
                            </tr>
                            {stats_html}
                        </table>
                    </div>

                    <div class="footer">
                        <p>Bu e-posta otomatik olarak gönderilmiştir.<br/>
                        Gönderim Zamanı: {timestamp}</p>
                    </div>
                </div>
            </body>
        </html>
        """

    @staticmethod
    def _template_error_notification(
        error_type: str,
        error_message: str,
        error_context: str,
        suggested_action: str,
        timestamp: str,
    ) -> str:
        """Hata bildirimi şablonu."""
        return f"""
        <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                    .error-box {{ background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; }}
                    .error-code {{ background-color: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; margin: 10px 0; }}
                    .footer {{ text-align: center; font-size: 12px; color: #999; margin-top: 30px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Sistem Hatası 🚨</h2>
                    </div>

                    <div class="error-box">
                        <p><strong>Hata Türü:</strong> {error_type}</p>

                        <p><strong>Hata Mesajı:</strong></p>
                        <div class="error-code">{error_message}</div>

                        {f'<p><strong>Bağlam:</strong><br/>{error_context}</p>' if error_context else ''}

                        {f'<p><strong>Önerilen İşlem:</strong><br/>{suggested_action}</p>' if suggested_action else ''}

                        <p style="margin-top: 15px; color: #666;">
                            Lütfen sistem yöneticisine iletişim kurun.
                        </p>
                    </div>

                    <div class="footer">
                        <p>Bu e-posta otomatik olarak gönderilmiştir.<br/>
                        Gönderim Zamanı: {timestamp}</p>
                    </div>
                </div>
            </body>
        </html>
        """
