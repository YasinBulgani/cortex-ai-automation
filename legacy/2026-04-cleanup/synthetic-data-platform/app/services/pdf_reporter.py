"""
PDF Rapor Üretim Modülü - reportlab tabanlı profesyonel raporlar

Bu modül, SyntheticBankData platformu için kalite, test ve denetim
raporlarını PDF formatında üretir. reportlab kütüphanesi mevcutsa
zengin görsel raporlar üretilir; değilse düz metin özeti döndürülür.
"""
try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm, inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Wedge, Circle
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics import renderPDF
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

import io
import json
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Renk Sabitleri
# ---------------------------------------------------------------------------

@dataclass
class ReportColors:
    """
    Rapor renk teması sabitleri.

    Tüm raporlarda tutarlı bir görünüm sağlamak için kullanılan
    hex renk kodları burada tanımlanmıştır.
    """
    PRIMARY: str = "#1e3a5f"       # Koyu lacivert – başlıklar ve vurgular
    SECONDARY: str = "#2196F3"     # Mavi – ikincil öğeler
    SUCCESS: str = "#4CAF50"       # Yeşil – başarı durumu
    WARNING: str = "#FF9800"       # Turuncu – uyarı durumu
    ERROR: str = "#F44336"         # Kırmızı – hata durumu
    BACKGROUND: str = "#F5F5F5"    # Açık gri – arka plan
    TEXT: str = "#212121"          # Neredeyse siyah – gövde metni
    LIGHT_GRAY: str = "#E0E0E0"    # Açık gri – kenarlıklar / şerit

    def to_reportlab(self, hex_color: str):
        """Hex rengi reportlab Color nesnesine çevirir."""
        if not HAS_REPORTLAB:
            return hex_color
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return colors.Color(r, g, b)


# Modül düzeyinde renk nesnesi
COLORS = ReportColors()


# ---------------------------------------------------------------------------
# Temel PDF Sınıfı
# ---------------------------------------------------------------------------

class PDFBase:
    """
    Tüm rapor sınıflarının miras aldığı temel PDF yardımcı sınıfı.

    reportlab SimpleDocTemplate üzerine inşa edilmiş olup sayfa başlığı,
    altbilgi, ortak tablo ve grafik oluşturma yöntemlerini barındırır.
    """

    def __init__(
        self,
        title: str,
        author: str = "SyntheticBankData",
        logo_path: Optional[str] = None
    ):
        """
        Temel PDF nesnesi başlatıcı.

        Parametreler
        ------------
        title : str
            Raporun başlığı; sayfa başlığında ve kapak sayfasında görünür.
        author : str
            PDF meta verisindeki yazar adı. Varsayılan: "SyntheticBankData".
        logo_path : str, optional
            Varsa başlık alanına eklenen logo dosyasının yolu.
        """
        self.title = title
        self.author = author
        self.logo_path = logo_path
        self.colors = COLORS
        self.styles = self._create_styles() if HAS_REPORTLAB else {}
        self.page_width, self.page_height = A4 if HAS_REPORTLAB else (595, 842)
        self.margin = 2 * cm if HAS_REPORTLAB else 0
        self._generation_time = datetime.now()

    # ------------------------------------------------------------------
    # Stil oluşturma
    # ------------------------------------------------------------------

    def _create_styles(self) -> dict:
        """
        Raporda kullanılan tüm ParagraphStyle nesnelerini oluşturur.

        Döndürür
        --------
        dict
            Anahtar: stil adı, Değer: ParagraphStyle nesnesi.
        """
        if not HAS_REPORTLAB:
            return {}

        base = getSampleStyleSheet()
        primary_rgb = self.colors.to_reportlab(self.colors.PRIMARY)
        text_rgb = self.colors.to_reportlab(self.colors.TEXT)

        styles = {}

        # Kapak başlık stili
        styles["cover_title"] = ParagraphStyle(
            "cover_title",
            parent=base["Title"],
            fontSize=28,
            textColor=primary_rgb,
            spaceAfter=20,
            spaceBefore=40,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        # Ana başlık (H1)
        styles["title"] = ParagraphStyle(
            "report_title",
            parent=base["Heading1"],
            fontSize=20,
            textColor=primary_rgb,
            spaceAfter=12,
            spaceBefore=18,
            fontName="Helvetica-Bold",
            borderPad=4,
        )

        # Alt başlık (H2)
        styles["heading"] = ParagraphStyle(
            "report_heading",
            parent=base["Heading2"],
            fontSize=14,
            textColor=primary_rgb,
            spaceAfter=8,
            spaceBefore=14,
            fontName="Helvetica-Bold",
        )

        # Üçüncü düzey başlık (H3)
        styles["subheading"] = ParagraphStyle(
            "report_subheading",
            parent=base["Heading3"],
            fontSize=12,
            textColor=self.colors.to_reportlab(self.colors.SECONDARY),
            spaceAfter=6,
            spaceBefore=10,
            fontName="Helvetica-Bold",
        )

        # Normal gövde metni
        styles["body"] = ParagraphStyle(
            "report_body",
            parent=base["Normal"],
            fontSize=10,
            textColor=text_rgb,
            spaceAfter=6,
            spaceBefore=4,
            fontName="Helvetica",
            leading=14,
            alignment=TA_JUSTIFY,
        )

        # Altyazı / küçük metin
        styles["caption"] = ParagraphStyle(
            "report_caption",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.grey,
            spaceAfter=4,
            spaceBefore=2,
            fontName="Helvetica-Oblique",
            alignment=TA_CENTER,
        )

        # Kod stili (monospace)
        styles["code"] = ParagraphStyle(
            "report_code",
            parent=base["Code"],
            fontSize=9,
            fontName="Courier",
            backColor=self.colors.to_reportlab(self.colors.BACKGROUND),
            borderColor=self.colors.to_reportlab(self.colors.LIGHT_GRAY),
            borderWidth=0.5,
            borderPad=4,
            spaceAfter=6,
            spaceBefore=6,
            leading=12,
        )

        # Tablo başlık hücresi
        styles["table_header"] = ParagraphStyle(
            "report_table_header",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )

        # Tablo veri hücresi
        styles["table_cell"] = ParagraphStyle(
            "report_table_cell",
            parent=base["Normal"],
            fontSize=9,
            textColor=text_rgb,
            fontName="Helvetica",
            alignment=TA_LEFT,
        )

        # Vurgu / önemli bilgi
        styles["highlight"] = ParagraphStyle(
            "report_highlight",
            parent=base["Normal"],
            fontSize=11,
            textColor=primary_rgb,
            fontName="Helvetica-Bold",
            spaceAfter=8,
            spaceBefore=8,
        )

        return styles

    # ------------------------------------------------------------------
    # Sayfa başlığı ve altbilgi
    # ------------------------------------------------------------------

    def _add_header(self, canvas, doc):
        """
        Her sayfanın üst kısmına başlık çizer.

        Parametreler
        ------------
        canvas : reportlab.canvas.Canvas
            Çizim yüzeyi.
        doc : SimpleDocTemplate
            Belge nesnesi.
        """
        if not HAS_REPORTLAB:
            return

        canvas.saveState()
        page_width = doc.pagesize[0]

        # Üst çizgi
        primary_color = self.colors.to_reportlab(self.colors.PRIMARY)
        canvas.setStrokeColor(primary_color)
        canvas.setLineWidth(2)
        canvas.line(doc.leftMargin, doc.pagesize[1] - 1.2 * cm,
                    page_width - doc.rightMargin, doc.pagesize[1] - 1.2 * cm)

        # Rapor adı
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(primary_color)
        canvas.drawString(doc.leftMargin, doc.pagesize[1] - 1.0 * cm, self.title)

        # Sayfa numarası
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        page_text = f"Sayfa {doc.page}"
        canvas.drawRightString(
            page_width - doc.rightMargin,
            doc.pagesize[1] - 1.0 * cm,
            page_text,
        )

        canvas.restoreState()

    def _add_footer(self, canvas, doc):
        """
        Her sayfanın alt kısmına altbilgi çizer.

        Parametreler
        ------------
        canvas : reportlab.canvas.Canvas
            Çizim yüzeyi.
        doc : SimpleDocTemplate
            Belge nesnesi.
        """
        if not HAS_REPORTLAB:
            return

        canvas.saveState()
        page_width = doc.pagesize[0]

        # Alt çizgi
        canvas.setStrokeColor(self.colors.to_reportlab(self.colors.LIGHT_GRAY))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 1.5 * cm,
                    page_width - doc.rightMargin, 1.5 * cm)

        # Tarih
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        date_str = self._generation_time.strftime("%d.%m.%Y %H:%M")
        canvas.drawString(doc.leftMargin, 1.0 * cm, f"Oluşturulma: {date_str}")

        # Şirket adı
        canvas.drawRightString(
            page_width - doc.rightMargin,
            1.0 * cm,
            f"© {self.author}",
        )

        canvas.restoreState()

    def _header_footer(self, canvas, doc):
        """Hem başlık hem altbilgi çizen birleşik yardımcı."""
        self._add_header(canvas, doc)
        self._add_footer(canvas, doc)

    # ------------------------------------------------------------------
    # Tablo oluşturma
    # ------------------------------------------------------------------

    def _create_table(
        self,
        data: List[List],
        col_widths=None,
        style=None,
    ) -> "Table":
        """
        Verilen veriden reportlab Table nesnesi oluşturur.

        Parametreler
        ------------
        data : List[List]
            İlk satır başlık; geri kalanlar veri.
        col_widths : list, optional
            Her sütun için piksel cinsinden genişlik listesi.
        style : list, optional
            Ek TableStyle komutları listesi.

        Döndürür
        --------
        Table
            Stillendirilmiş reportlab tablo nesnesi.
        """
        if not HAS_REPORTLAB:
            return None

        primary = self.colors.to_reportlab(self.colors.PRIMARY)
        light_gray = self.colors.to_reportlab(self.colors.LIGHT_GRAY)
        bg = self.colors.to_reportlab(self.colors.BACKGROUND)
        text_color = self.colors.to_reportlab(self.colors.TEXT)

        default_style = [
            # Başlık satırı arka planı
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            # Veri satırları
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), text_color),
            ("ALIGN", (0, 1), (-1, -1), "LEFT"),
            # Zebra şeritleme
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg]),
            # Kenarlıklar
            ("GRID", (0, 0), (-1, -1), 0.25, light_gray),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, primary),
            # İç dolgu
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]

        if style:
            default_style.extend(style)

        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle(default_style))
        return table

    # ------------------------------------------------------------------
    # Grafik oluşturma
    # ------------------------------------------------------------------

    def _create_bar_chart(
        self,
        data: dict,
        title: str,
        width: int = 400,
        height: int = 200,
    ) -> "Drawing":
        """
        Dikey çubuk grafik içeren bir Drawing nesnesi döndürür.

        Parametreler
        ------------
        data : dict
            {etiket: değer} biçiminde veri sözlüğü.
        title : str
            Grafiğin üstünde gösterilecek başlık.
        width : int
            Grafik genişliği (piksel).
        height : int
            Grafik yüksekliği (piksel).

        Döndürür
        --------
        Drawing
            reportlab Drawing nesnesi.
        """
        if not HAS_REPORTLAB:
            return None

        drawing = Drawing(width, height)

        # Arka plan dikdörtgeni
        bg = Rect(0, 0, width, height, fillColor=colors.white, strokeColor=None)
        drawing.add(bg)

        # Başlık metni
        title_str = String(
            width / 2, height - 12,
            title,
            fontName="Helvetica-Bold",
            fontSize=10,
            fillColor=self.colors.to_reportlab(self.colors.PRIMARY),
            textAnchor="middle",
        )
        drawing.add(title_str)

        if not data:
            no_data = String(
                width / 2, height / 2,
                "Veri yok",
                fontName="Helvetica",
                fontSize=9,
                fillColor=colors.grey,
                textAnchor="middle",
            )
            drawing.add(no_data)
            return drawing

        labels = list(data.keys())
        values = [float(v) for v in data.values()]

        chart = VerticalBarChart()
        chart.x = 40
        chart.y = 30
        chart.width = width - 60
        chart.height = height - 55

        chart.data = [values]
        chart.categoryAxis.categoryNames = [str(lb) for lb in labels]
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fontSize = 7
        chart.categoryAxis.labels.angle = 30
        chart.categoryAxis.labels.dy = -6

        chart.valueAxis.labelTextFormat = "%.1f"
        chart.valueAxis.labels.fontName = "Helvetica"
        chart.valueAxis.labels.fontSize = 7

        secondary = self.colors.to_reportlab(self.colors.SECONDARY)
        chart.bars[0].fillColor = secondary
        chart.bars[0].strokeColor = None

        drawing.add(chart)
        return drawing

    def _create_pie_chart(
        self,
        data: dict,
        title: str,
        width: int = 300,
        height: int = 200,
    ) -> "Drawing":
        """
        Pasta grafik içeren bir Drawing nesnesi döndürür.

        Parametreler
        ------------
        data : dict
            {etiket: değer} biçiminde veri sözlüğü.
        title : str
            Grafiğin üstünde gösterilecek başlık.
        width : int
            Grafik genişliği (piksel).
        height : int
            Grafik yüksekliği (piksel).

        Döndürür
        --------
        Drawing
            reportlab Drawing nesnesi.
        """
        if not HAS_REPORTLAB:
            return None

        drawing = Drawing(width, height)

        bg = Rect(0, 0, width, height, fillColor=colors.white, strokeColor=None)
        drawing.add(bg)

        title_str = String(
            width / 2, height - 12,
            title,
            fontName="Helvetica-Bold",
            fontSize=10,
            fillColor=self.colors.to_reportlab(self.colors.PRIMARY),
            textAnchor="middle",
        )
        drawing.add(title_str)

        if not data:
            drawing.add(String(
                width / 2, height / 2,
                "Veri yok",
                fontName="Helvetica",
                fontSize=9,
                fillColor=colors.grey,
                textAnchor="middle",
            ))
            return drawing

        palette = [
            self.colors.to_reportlab(self.colors.PRIMARY),
            self.colors.to_reportlab(self.colors.SECONDARY),
            self.colors.to_reportlab(self.colors.SUCCESS),
            self.colors.to_reportlab(self.colors.WARNING),
            self.colors.to_reportlab(self.colors.ERROR),
            colors.purple,
            colors.cyan,
            colors.orange,
        ]

        pie = Pie()
        pie.x = 30
        pie.y = 20
        pie.width = min(width - 80, height - 40)
        pie.height = pie.width
        pie.data = [float(v) for v in data.values()]
        pie.labels = list(data.keys())

        for i in range(len(pie.data)):
            pie.slices[i].fillColor = palette[i % len(palette)]
            pie.slices[i].strokeColor = colors.white
            pie.slices[i].strokeWidth = 0.5
            pie.slices[i].labelRadius = 1.2
            pie.slices[i].fontSize = 7

        drawing.add(pie)
        return drawing

    # ------------------------------------------------------------------
    # Yedek metin raporu (reportlab yoksa)
    # ------------------------------------------------------------------

    def _fallback_text_report(self, content: dict) -> str:
        """
        reportlab mevcut değilken kullanılan düz metin rapor üretici.

        Parametreler
        ------------
        content : dict
            Rapor verisi sözlüğü.

        Döndürür
        --------
        str
            İnsan okunabilir düz metin rapor.
        """
        lines = []
        separator = "=" * 70
        lines.append(separator)
        lines.append(f"  {self.title}")
        lines.append(f"  Yazar: {self.author}")
        lines.append(f"  Oluşturulma: {self._generation_time.strftime('%d.%m.%Y %H:%M:%S')}")
        lines.append(separator)
        lines.append("")

        def _dump(obj, indent=0):
            prefix = "  " * indent
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}{k}:")
                        _dump(v, indent + 1)
                    else:
                        lines.append(f"{prefix}{k}: {v}")
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict):
                        _dump(item, indent)
                        lines.append(f"{prefix}---")
                    else:
                        lines.append(f"{prefix}- {item}")
            else:
                lines.append(f"{prefix}{obj}")

        _dump(content)
        lines.append("")
        lines.append(separator)
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Ortak sayfa elemanları
    # ------------------------------------------------------------------

    def _build_cover_elements(
        self,
        report_title: str,
        subtitle: str = "",
        meta_lines: List[str] = None,
    ) -> list:
        """
        Kapak sayfası içerik listesi döndürür.

        Parametreler
        ------------
        report_title : str
            Kapakta büyük yazılacak başlık.
        subtitle : str
            Alt başlık metni.
        meta_lines : List[str]
            Kapakta gösterilecek ek bilgi satırları.

        Döndürür
        --------
        list
            reportlab Flowable listesi.
        """
        if not HAS_REPORTLAB:
            return []

        elems = []
        elems.append(Spacer(1, 3 * cm))

        # Şirket logosu veya renkli blok
        logo_drawing = Drawing(400, 60)
        logo_rect = Rect(
            0, 0, 400, 60,
            fillColor=self.colors.to_reportlab(self.colors.PRIMARY),
            strokeColor=None,
            rx=8, ry=8,
        )
        logo_drawing.add(logo_rect)
        logo_text = String(
            200, 22,
            self.author,
            fontName="Helvetica-Bold",
            fontSize=20,
            fillColor=colors.white,
            textAnchor="middle",
        )
        logo_drawing.add(logo_text)
        elems.append(logo_drawing)
        elems.append(Spacer(1, 1.5 * cm))

        # Rapor başlığı
        elems.append(Paragraph(report_title, self.styles["cover_title"]))

        if subtitle:
            sub_style = ParagraphStyle(
                "cover_sub",
                parent=self.styles["body"],
                fontSize=13,
                textColor=self.colors.to_reportlab(self.colors.SECONDARY),
                alignment=TA_CENTER,
                spaceAfter=10,
            )
            elems.append(Paragraph(subtitle, sub_style))

        elems.append(Spacer(1, 1 * cm))
        elems.append(HRFlowable(
            width="80%",
            thickness=2,
            color=self.colors.to_reportlab(self.colors.LIGHT_GRAY),
            hAlign="CENTER",
        ))
        elems.append(Spacer(1, 0.5 * cm))

        # Meta bilgiler
        if meta_lines:
            meta_style = ParagraphStyle(
                "cover_meta",
                parent=self.styles["body"],
                fontSize=10,
                textColor=colors.grey,
                alignment=TA_CENTER,
                spaceAfter=5,
            )
            for line in meta_lines:
                elems.append(Paragraph(line, meta_style))

        elems.append(PageBreak())
        return elems

    def _section_header(self, text: str) -> list:
        """Bölüm başlığı ve yatay çizgi döndürür."""
        if not HAS_REPORTLAB:
            return []
        elems = [
            Spacer(1, 0.3 * cm),
            Paragraph(text, self.styles["title"]),
            HRFlowable(
                width="100%",
                thickness=1,
                color=self.colors.to_reportlab(self.colors.PRIMARY),
            ),
            Spacer(1, 0.2 * cm),
        ]
        return elems


# ---------------------------------------------------------------------------
# Kalite Raporu
# ---------------------------------------------------------------------------

class QualityReport(PDFBase):
    """
    Veri kalite analizi PDF raporunu üreten sınıf.

    Sütun bazlı kalite metrikleri, anomali özeti ve önerileri
    içeren kapsamlı bir rapor oluşturur.
    """

    def __init__(self, logo_path: Optional[str] = None):
        """
        Kalite raporu başlatıcı.

        Parametreler
        ------------
        logo_path : str, optional
            Kapak sayfasında kullanılacak logo dosya yolu.
        """
        super().__init__(
            title="Veri Kalite Raporu",
            author="SyntheticBankData",
            logo_path=logo_path,
        )

    # ------------------------------------------------------------------

    def generate(self, output_path: str, report_data: dict) -> str:
        """
        Kalite raporunu belirtilen yola PDF olarak yazar.

        Beklenen report_data yapısı
        ---------------------------
        {
          "title": str,
          "generated_at": str (ISO format),
          "overall_score": float (0-100),
          "total_rows": int,
          "total_columns": int,
          "columns": [
            {
              "name": str,
              "type": str,
              "null_ratio": float,
              "unique_count": int,
              "mean": float | None,
              "std": float | None,
              "quality_score": float
            }
          ],
          "anomalies": [
            {"type": str, "severity": str, "count": int}
          ],
          "recommendations": [str]
        }

        Parametreler
        ------------
        output_path : str
            Çıktı PDF dosyasının tam yolu.
        report_data : dict
            Yukarıdaki yapıya uygun rapor verisi.

        Döndürür
        --------
        str
            Oluşturulan dosyanın yolu veya reportlab yoksa metin özeti.
        """
        if not HAS_REPORTLAB:
            logger.warning("reportlab bulunamadı; metin raporu oluşturuluyor.")
            return self._fallback_text_report(report_data)

        self.title = report_data.get("title", "Veri Kalite Raporu")
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
            title=self.title,
            author=self.author,
        )

        story = []

        # ---- Kapak sayfası ------------------------------------------------
        generated_at = report_data.get("generated_at", self._generation_time.isoformat())
        score = report_data.get("overall_score", 0)
        story += self._build_cover_elements(
            self.title,
            subtitle="Yapay Banka Verisi Kalite Analizi",
            meta_lines=[
                f"Oluşturulma: {generated_at}",
                f"Genel Kalite Skoru: {score:.1f} / 100",
                f"Toplam Satır: {report_data.get('total_rows', 0):,}  |  "
                f"Toplam Sütun: {report_data.get('total_columns', 0)}",
            ],
        )

        # ---- Yönetici Özeti -----------------------------------------------
        story += self._section_header("Yönetici Özeti")

        score_color = (
            self.colors.SUCCESS if score >= 80
            else self.colors.WARNING if score >= 60
            else self.colors.ERROR
        )
        score_drawing = self._build_score_gauge(score, "Genel Kalite Skoru", score_color)
        if score_drawing:
            story.append(score_drawing)
            story.append(Spacer(1, 0.4 * cm))

        exec_data = [
            ["Metrik", "Değer"],
            ["Genel Kalite Skoru", f"{score:.1f} / 100"],
            ["Toplam Satır", f"{report_data.get('total_rows', 0):,}"],
            ["Toplam Sütun", f"{report_data.get('total_columns', 0)}"],
            ["Anomali Sayısı", str(sum(a.get("count", 0) for a in report_data.get("anomalies", [])))],
            ["Öneri Sayısı", str(len(report_data.get("recommendations", [])))],
        ]
        exec_table = self._create_table(exec_data, col_widths=[8 * cm, 8 * cm])
        if exec_table:
            story.append(exec_table)
        story.append(Spacer(1, 0.5 * cm))

        # ---- Sütun Kalite Analizi -----------------------------------------
        story += self._section_header("Sütun Kalite Analizi")

        columns = report_data.get("columns", [])
        if columns:
            col_header = ["Sütun Adı", "Tür", "Null %", "Tekil", "Ortalama", "Std", "Kalite Skoru"]
            col_rows = [col_header]
            for col in columns:
                null_pct = f"{col.get('null_ratio', 0) * 100:.1f}%"
                mean_val = f"{col.get('mean', ''):.3f}" if col.get("mean") is not None else "—"
                std_val = f"{col.get('std', ''):.3f}" if col.get("std") is not None else "—"
                qs = col.get("quality_score", 0)
                col_rows.append([
                    str(col.get("name", "")),
                    str(col.get("type", "")),
                    null_pct,
                    str(col.get("unique_count", "")),
                    mean_val,
                    std_val,
                    f"{qs:.1f}",
                ])

            extra_style = []
            for i, col in enumerate(columns, start=1):
                qs = col.get("quality_score", 100)
                if qs < 60:
                    bg_color = self.colors.to_reportlab(self.colors.ERROR)
                    extra_style.append(("BACKGROUND", (6, i), (6, i), bg_color))
                    extra_style.append(("TEXTCOLOR", (6, i), (6, i), colors.white))
                elif qs < 80:
                    bg_color = self.colors.to_reportlab(self.colors.WARNING)
                    extra_style.append(("BACKGROUND", (6, i), (6, i), bg_color))
                else:
                    bg_color = self.colors.to_reportlab(self.colors.SUCCESS)
                    extra_style.append(("BACKGROUND", (6, i), (6, i), bg_color))
                    extra_style.append(("TEXTCOLOR", (6, i), (6, i), colors.white))

            widths = [4 * cm, 2.5 * cm, 2 * cm, 2 * cm, 2.5 * cm, 2 * cm, 3 * cm]
            col_table = self._create_table(col_rows, col_widths=widths, style=extra_style)
            if col_table:
                story.append(col_table)
        else:
            story.append(Paragraph("Sütun verisi bulunamadı.", self.styles["body"]))

        story.append(Spacer(1, 0.5 * cm))

        # ---- Dağılım Analizi ----------------------------------------------
        story += self._section_header("Dağılım Analizi")

        if columns:
            score_map = {col["name"]: col.get("quality_score", 0) for col in columns}
            bar_drawing = self._create_bar_chart(
                score_map,
                "Sütun Kalite Skorları",
                width=480,
                height=220,
            )
            if bar_drawing:
                story.append(bar_drawing)
                story.append(Paragraph("Şekil 1: Sütun bazında kalite skoru dağılımı", self.styles["caption"]))

        story.append(Spacer(1, 0.5 * cm))

        # ---- Anomali Özeti ------------------------------------------------
        story += self._section_header("Anomali Özeti")

        anomalies = report_data.get("anomalies", [])
        if anomalies:
            anom_header = ["Anomali Türü", "Önem Derecesi", "Sayı"]
            anom_rows = [anom_header]
            severity_style = []
            for i, anom in enumerate(anomalies, start=1):
                sev = anom.get("severity", "low")
                anom_rows.append([
                    str(anom.get("type", "")),
                    str(sev).upper(),
                    str(anom.get("count", 0)),
                ])
                color_map = {
                    "high": self.colors.ERROR,
                    "medium": self.colors.WARNING,
                    "low": self.colors.SUCCESS,
                }
                bg = self.colors.to_reportlab(color_map.get(sev.lower(), self.colors.LIGHT_GRAY))
                severity_style.append(("BACKGROUND", (1, i), (1, i), bg))
                severity_style.append(("TEXTCOLOR", (1, i), (1, i), colors.white))

            anom_table = self._create_table(
                anom_rows,
                col_widths=[8 * cm, 5 * cm, 4 * cm],
                style=severity_style,
            )
            if anom_table:
                story.append(anom_table)
            story.append(Spacer(1, 0.3 * cm))

            # Anomali pasta grafik
            severity_counts: Dict[str, int] = {}
            for anom in anomalies:
                sev = anom.get("severity", "low").capitalize()
                severity_counts[sev] = severity_counts.get(sev, 0) + anom.get("count", 0)

            if severity_counts:
                pie_drawing = self._create_pie_chart(
                    severity_counts,
                    "Önem Derecesine Göre Anomaliler",
                    width=300,
                    height=220,
                )
                if pie_drawing:
                    story.append(pie_drawing)
                    story.append(Paragraph("Şekil 2: Anomali önem dağılımı", self.styles["caption"]))
        else:
            story.append(Paragraph("Anomali tespit edilmedi.", self.styles["body"]))

        story.append(Spacer(1, 0.5 * cm))

        # ---- Öneriler -------------------------------------------------------
        story += self._section_header("Öneriler")

        recommendations = report_data.get("recommendations", [])
        if recommendations:
            for idx, rec in enumerate(recommendations, start=1):
                story.append(Paragraph(f"{idx}. {rec}", self.styles["body"]))
                story.append(Spacer(1, 0.1 * cm))
        else:
            story.append(Paragraph("Öneri bulunmamaktadır.", self.styles["body"]))

        # ---- Oluştur --------------------------------------------------------
        try:
            doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
            logger.info("Kalite raporu oluşturuldu: %s", output_path)
            return output_path
        except Exception as exc:
            logger.error("PDF oluşturma hatası: %s", exc)
            raise

    # ------------------------------------------------------------------

    def _build_score_gauge(self, score: float, label: str, color_hex: str) -> Optional["Drawing"]:
        """
        Skor göstergesi (basit yatay çubuk) çizer.

        Parametreler
        ------------
        score : float
            0-100 arasında skor değeri.
        label : str
            Göstergenin altındaki etiket.
        color_hex : str
            Doldurma rengi.

        Döndürür
        --------
        Drawing veya None
        """
        if not HAS_REPORTLAB:
            return None

        width, height = 400, 50
        drawing = Drawing(width, height)

        # Arka plan çubuk
        bg_rect = Rect(
            20, 20, 360, 20,
            fillColor=self.colors.to_reportlab(self.colors.LIGHT_GRAY),
            strokeColor=None,
            rx=4, ry=4,
        )
        drawing.add(bg_rect)

        # Dolgu çubuk
        fill_width = max(0, min(360, 360 * score / 100))
        fill_rect = Rect(
            20, 20, fill_width, 20,
            fillColor=self.colors.to_reportlab(color_hex),
            strokeColor=None,
            rx=4, ry=4,
        )
        drawing.add(fill_rect)

        # Skor metni
        score_text = String(
            200, 26,
            f"{score:.1f}%",
            fontName="Helvetica-Bold",
            fontSize=10,
            fillColor=colors.white if fill_width > 180 else self.colors.to_reportlab(self.colors.TEXT),
            textAnchor="middle",
        )
        drawing.add(score_text)

        # Etiket
        label_text = String(
            200, 5,
            label,
            fontName="Helvetica",
            fontSize=8,
            fillColor=self.colors.to_reportlab(self.colors.TEXT),
            textAnchor="middle",
        )
        drawing.add(label_text)

        return drawing


# ---------------------------------------------------------------------------
# Test Raporu
# ---------------------------------------------------------------------------

class TestReport(PDFBase):
    """
    Otomatik test sonuçlarını içeren PDF raporunu üreten sınıf.

    Birim testleri, görsel regresyon testleri ve erişilebilirlik
    test sonuçlarını kapsamlı bir PDF belgesinde sunar.
    """

    def __init__(self, logo_path: Optional[str] = None):
        """
        Test raporu başlatıcı.

        Parametreler
        ------------
        logo_path : str, optional
            Kapak sayfasında kullanılacak logo dosya yolu.
        """
        super().__init__(
            title="Test Sonuç Raporu",
            author="SyntheticBankData",
            logo_path=logo_path,
        )

    # ------------------------------------------------------------------

    def generate(self, output_path: str, report_data: dict) -> str:
        """
        Test raporunu belirtilen yola PDF olarak yazar.

        Beklenen report_data yapısı
        ---------------------------
        {
          "title": str,
          "test_suite": str,
          "total": int,
          "passed": int,
          "failed": int,
          "skipped": int,
          "duration": float (saniye),
          "tests": [
            {"name": str, "status": str, "duration": float, "error_msg": str | None}
          ],
          "visual_tests": [
            {"name": str, "ssim_score": float, "passed": bool}
          ],
          "a11y_tests": [
            {"url": str, "score": float, "violations_count": int}
          ]
        }

        Parametreler
        ------------
        output_path : str
            Çıktı PDF dosyasının tam yolu.
        report_data : dict
            Yukarıdaki yapıya uygun rapor verisi.

        Döndürür
        --------
        str
            Oluşturulan dosyanın yolu veya reportlab yoksa metin özeti.
        """
        if not HAS_REPORTLAB:
            logger.warning("reportlab bulunamadı; metin raporu oluşturuluyor.")
            return self._fallback_text_report(report_data)

        self.title = report_data.get("title", "Test Sonuç Raporu")
        total = report_data.get("total", 0)
        passed = report_data.get("passed", 0)
        failed = report_data.get("failed", 0)
        skipped = report_data.get("skipped", 0)
        pass_rate = (passed / total * 100) if total else 0
        duration = report_data.get("duration", 0)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
            title=self.title,
            author=self.author,
        )

        story = []

        # ---- Kapak sayfası ------------------------------------------------
        story += self._build_cover_elements(
            self.title,
            subtitle=f"Test Paketi: {report_data.get('test_suite', '')}",
            meta_lines=[
                f"Oluşturulma: {self._generation_time.strftime('%d.%m.%Y %H:%M')}",
                f"Toplam Test: {total}  |  Geçti: {passed}  |  Başarısız: {failed}  |  Atlandı: {skipped}",
                f"Başarı Oranı: {pass_rate:.1f}%  |  Süre: {duration:.2f} sn",
            ],
        )

        # ---- Test Özeti ---------------------------------------------------
        story += self._section_header("Test Özeti")

        gauge_color = (
            self.colors.SUCCESS if pass_rate >= 90
            else self.colors.WARNING if pass_rate >= 70
            else self.colors.ERROR
        )
        gauge = self._build_score_gauge(pass_rate, "Test Başarı Oranı", gauge_color)
        if gauge:
            story.append(gauge)
            story.append(Spacer(1, 0.4 * cm))

        summary_data = [
            ["Metrik", "Değer"],
            ["Toplam Test", str(total)],
            ["Geçti", str(passed)],
            ["Başarısız", str(failed)],
            ["Atlandı", str(skipped)],
            ["Başarı Oranı", f"{pass_rate:.1f}%"],
            ["Toplam Süre", f"{duration:.2f} sn"],
        ]

        extra_style = []
        if failed > 0:
            extra_style.append(("BACKGROUND", (1, 3), (1, 3), self.colors.to_reportlab(self.colors.ERROR)))
            extra_style.append(("TEXTCOLOR", (1, 3), (1, 3), colors.white))
        if passed > 0:
            extra_style.append(("BACKGROUND", (1, 2), (1, 2), self.colors.to_reportlab(self.colors.SUCCESS)))
            extra_style.append(("TEXTCOLOR", (1, 2), (1, 2), colors.white))

        summary_table = self._create_table(summary_data, col_widths=[8 * cm, 8 * cm], style=extra_style)
        if summary_table:
            story.append(summary_table)
        story.append(Spacer(1, 0.5 * cm))

        # Durum dağılımı pasta grafik
        status_dist = {}
        if passed:
            status_dist["Geçti"] = passed
        if failed:
            status_dist["Başarısız"] = failed
        if skipped:
            status_dist["Atlandı"] = skipped
        if status_dist:
            pie = self._create_pie_chart(status_dist, "Test Durumu Dağılımı", 280, 200)
            if pie:
                story.append(pie)
                story.append(Paragraph("Şekil 1: Test durumu dağılımı", self.styles["caption"]))
                story.append(Spacer(1, 0.3 * cm))

        # ---- Test Sonuçları Tablosu ----------------------------------------
        story += self._section_header("Test Sonuçları")

        tests = report_data.get("tests", [])
        if tests:
            test_header = ["Test Adı", "Durum", "Süre (sn)", "Hata Mesajı"]
            test_rows = [test_header]
            row_styles = []
            for i, test in enumerate(tests, start=1):
                status = str(test.get("status", "unknown")).upper()
                error_msg = str(test.get("error_msg", "") or "")
                # Uzun mesajları kırp
                if len(error_msg) > 60:
                    error_msg = error_msg[:57] + "..."
                test_rows.append([
                    str(test.get("name", "")),
                    status,
                    f"{test.get('duration', 0):.3f}",
                    error_msg,
                ])
                if status == "PASSED":
                    bg = self.colors.to_reportlab(self.colors.SUCCESS)
                    row_styles.append(("BACKGROUND", (1, i), (1, i), bg))
                    row_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))
                elif status == "FAILED":
                    bg = self.colors.to_reportlab(self.colors.ERROR)
                    row_styles.append(("BACKGROUND", (1, i), (1, i), bg))
                    row_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))
                elif status == "SKIPPED":
                    bg = self.colors.to_reportlab(self.colors.WARNING)
                    row_styles.append(("BACKGROUND", (1, i), (1, i), bg))

            test_table = self._create_table(
                test_rows,
                col_widths=[6 * cm, 2.5 * cm, 2.5 * cm, 7 * cm],
                style=row_styles,
            )
            if test_table:
                story.append(test_table)
        else:
            story.append(Paragraph("Test verisi bulunamadı.", self.styles["body"]))
        story.append(Spacer(1, 0.5 * cm))

        # ---- Görsel Regresyon Testleri -------------------------------------
        visual_tests = report_data.get("visual_tests", [])
        if visual_tests:
            story += self._section_header("Görsel Regresyon Sonuçları")

            vis_header = ["Test Adı", "SSIM Skoru", "Durum"]
            vis_rows = [vis_header]
            vis_styles = []
            for i, vt in enumerate(visual_tests, start=1):
                passed_vt = vt.get("passed", False)
                vis_rows.append([
                    str(vt.get("name", "")),
                    f"{vt.get('ssim_score', 0):.4f}",
                    "Geçti" if passed_vt else "Başarısız",
                ])
                if passed_vt:
                    vis_styles.append(("BACKGROUND", (2, i), (2, i), self.colors.to_reportlab(self.colors.SUCCESS)))
                    vis_styles.append(("TEXTCOLOR", (2, i), (2, i), colors.white))
                else:
                    vis_styles.append(("BACKGROUND", (2, i), (2, i), self.colors.to_reportlab(self.colors.ERROR)))
                    vis_styles.append(("TEXTCOLOR", (2, i), (2, i), colors.white))

            vis_table = self._create_table(
                vis_rows,
                col_widths=[9 * cm, 4 * cm, 4 * cm],
                style=vis_styles,
            )
            if vis_table:
                story.append(vis_table)
                story.append(Spacer(1, 0.3 * cm))

            # SSIM skoru çubuk grafiği
            ssim_data = {vt["name"]: vt.get("ssim_score", 0) for vt in visual_tests}
            if ssim_data:
                bar = self._create_bar_chart(ssim_data, "SSIM Skorları", 460, 200)
                if bar:
                    story.append(bar)
                    story.append(Paragraph("Şekil 2: Görsel regresyon SSIM skorları", self.styles["caption"]))

            story.append(Spacer(1, 0.5 * cm))

        # ---- Erişilebilirlik Testleri --------------------------------------
        a11y_tests = report_data.get("a11y_tests", [])
        if a11y_tests:
            story += self._section_header("Erişilebilirlik (a11y) Sonuçları")

            a11y_header = ["URL", "Skor", "İhlal Sayısı"]
            a11y_rows = [a11y_header]
            a11y_styles = []
            for i, at in enumerate(a11y_tests, start=1):
                score_a11y = at.get("score", 0)
                violations = at.get("violations_count", 0)
                a11y_rows.append([
                    str(at.get("url", "")),
                    f"{score_a11y:.1f}",
                    str(violations),
                ])
                if score_a11y >= 90:
                    a11y_styles.append(("BACKGROUND", (1, i), (1, i), self.colors.to_reportlab(self.colors.SUCCESS)))
                    a11y_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))
                elif score_a11y >= 70:
                    a11y_styles.append(("BACKGROUND", (1, i), (1, i), self.colors.to_reportlab(self.colors.WARNING)))
                else:
                    a11y_styles.append(("BACKGROUND", (1, i), (1, i), self.colors.to_reportlab(self.colors.ERROR)))
                    a11y_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))

            a11y_table = self._create_table(
                a11y_rows,
                col_widths=[10 * cm, 3 * cm, 4 * cm],
                style=a11y_styles,
            )
            if a11y_table:
                story.append(a11y_table)
            story.append(Spacer(1, 0.3 * cm))

        # ---- Oluştur --------------------------------------------------------
        try:
            doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
            logger.info("Test raporu oluşturuldu: %s", output_path)
            return output_path
        except Exception as exc:
            logger.error("PDF oluşturma hatası: %s", exc)
            raise

    # ------------------------------------------------------------------

    def _build_score_gauge(self, score: float, label: str, color_hex: str) -> Optional["Drawing"]:
        """
        Skor göstergesi (yatay çubuk) çizer.

        Parametreler
        ------------
        score : float
            0-100 arasında skor değeri.
        label : str
            Gösterge etiketi.
        color_hex : str
            Doldurma rengi.

        Döndürür
        --------
        Drawing veya None
        """
        if not HAS_REPORTLAB:
            return None

        width, height = 400, 50
        drawing = Drawing(width, height)

        bg_rect = Rect(20, 20, 360, 20,
                       fillColor=self.colors.to_reportlab(self.colors.LIGHT_GRAY),
                       strokeColor=None, rx=4, ry=4)
        drawing.add(bg_rect)

        fill_width = max(0, min(360, 360 * score / 100))
        fill_rect = Rect(20, 20, fill_width, 20,
                         fillColor=self.colors.to_reportlab(color_hex),
                         strokeColor=None, rx=4, ry=4)
        drawing.add(fill_rect)

        drawing.add(String(200, 26, f"{score:.1f}%",
                           fontName="Helvetica-Bold", fontSize=10,
                           fillColor=colors.white if fill_width > 180
                           else self.colors.to_reportlab(self.colors.TEXT),
                           textAnchor="middle"))
        drawing.add(String(200, 5, label,
                           fontName="Helvetica", fontSize=8,
                           fillColor=self.colors.to_reportlab(self.colors.TEXT),
                           textAnchor="middle"))
        return drawing


# ---------------------------------------------------------------------------
# Denetim Raporu
# ---------------------------------------------------------------------------

class AuditReport(PDFBase):
    """
    Uyumluluk durumu, denetim izi ve risk değerlendirmesini içeren
    PDF denetim raporunu üreten sınıf.
    """

    def __init__(self, logo_path: Optional[str] = None):
        """
        Denetim raporu başlatıcı.

        Parametreler
        ------------
        logo_path : str, optional
            Kapak sayfasında kullanılacak logo dosya yolu.
        """
        super().__init__(
            title="Denetim ve Uyumluluk Raporu",
            author="SyntheticBankData",
            logo_path=logo_path,
        )

    # ------------------------------------------------------------------

    def generate(self, output_path: str, report_data: dict) -> str:
        """
        Denetim raporunu belirtilen yola PDF olarak yazar.

        Beklenen report_data yapısı
        ---------------------------
        {
          "title": str,
          "audit_period": str,
          "compliance_items": [
            {"regulation": str, "status": str, "details": str}
          ],
          "audit_trail": [
            {
              "timestamp": str,
              "user": str,
              "action": str,
              "resource": str,
              "result": str
            }
          ],
          "risk_items": [
            {"risk": str, "level": str, "mitigation": str}
          ]
        }

        Parametreler
        ------------
        output_path : str
            Çıktı PDF dosyasının tam yolu.
        report_data : dict
            Yukarıdaki yapıya uygun rapor verisi.

        Döndürür
        --------
        str
            Oluşturulan dosyanın yolu veya reportlab yoksa metin özeti.
        """
        if not HAS_REPORTLAB:
            logger.warning("reportlab bulunamadı; metin raporu oluşturuluyor.")
            return self._fallback_text_report(report_data)

        self.title = report_data.get("title", "Denetim ve Uyumluluk Raporu")
        audit_period = report_data.get("audit_period", "—")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
            title=self.title,
            author=self.author,
        )

        story = []

        # ---- Kapak sayfası ------------------------------------------------
        compliance_items = report_data.get("compliance_items", [])
        compliant_count = sum(
            1 for c in compliance_items if c.get("status", "").lower() == "compliant"
        )
        total_compliance = len(compliance_items)
        comp_rate = (compliant_count / total_compliance * 100) if total_compliance else 0

        story += self._build_cover_elements(
            self.title,
            subtitle=f"Denetim Dönemi: {audit_period}",
            meta_lines=[
                f"Oluşturulma: {self._generation_time.strftime('%d.%m.%Y %H:%M')}",
                f"Uyumluluk Oranı: {comp_rate:.1f}%  ({compliant_count}/{total_compliance})",
                f"Denetim Kaydı Sayısı: {len(report_data.get('audit_trail', []))}",
                f"Risk Öğesi Sayısı: {len(report_data.get('risk_items', []))}",
            ],
        )

        # ---- Uyumluluk Durumu ---------------------------------------------
        story += self._section_header("Uyumluluk Durumu")

        # Özet gösterge
        gauge_color = (
            self.colors.SUCCESS if comp_rate >= 90
            else self.colors.WARNING if comp_rate >= 70
            else self.colors.ERROR
        )
        gauge = self._build_compliance_gauge(comp_rate, "Genel Uyumluluk Oranı", gauge_color)
        if gauge:
            story.append(gauge)
            story.append(Spacer(1, 0.4 * cm))

        if compliance_items:
            comp_header = ["Düzenleme", "Durum", "Detaylar"]
            comp_rows = [comp_header]
            comp_styles = []
            for i, item in enumerate(compliance_items, start=1):
                status = str(item.get("status", "")).lower()
                details = str(item.get("details", ""))
                if len(details) > 80:
                    details = details[:77] + "..."
                comp_rows.append([
                    str(item.get("regulation", "")),
                    str(item.get("status", "")).upper(),
                    details,
                ])
                if status == "compliant":
                    bg = self.colors.to_reportlab(self.colors.SUCCESS)
                    comp_styles.append(("BACKGROUND", (1, i), (1, i), bg))
                    comp_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))
                elif status in ("non-compliant", "noncompliant"):
                    bg = self.colors.to_reportlab(self.colors.ERROR)
                    comp_styles.append(("BACKGROUND", (1, i), (1, i), bg))
                    comp_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))
                else:
                    bg = self.colors.to_reportlab(self.colors.WARNING)
                    comp_styles.append(("BACKGROUND", (1, i), (1, i), bg))

            comp_table = self._create_table(
                comp_rows,
                col_widths=[5 * cm, 3.5 * cm, 9.5 * cm],
                style=comp_styles,
            )
            if comp_table:
                story.append(comp_table)
        else:
            story.append(Paragraph("Uyumluluk verisi bulunamadı.", self.styles["body"]))

        story.append(Spacer(1, 0.5 * cm))

        # Uyumluluk durumu dağılımı pasta grafik
        status_counts: Dict[str, int] = {}
        for item in compliance_items:
            s = str(item.get("status", "Bilinmiyor")).capitalize()
            status_counts[s] = status_counts.get(s, 0) + 1
        if status_counts:
            pie = self._create_pie_chart(status_counts, "Uyumluluk Dağılımı", 280, 200)
            if pie:
                story.append(pie)
                story.append(Paragraph("Şekil 1: Uyumluluk durumu dağılımı", self.styles["caption"]))
                story.append(Spacer(1, 0.4 * cm))

        # ---- Denetim İzi --------------------------------------------------
        story += self._section_header("Denetim İzi")

        audit_trail = report_data.get("audit_trail", [])
        if audit_trail:
            trail_header = ["Zaman Damgası", "Kullanıcı", "İşlem", "Kaynak", "Sonuç"]
            trail_rows = [trail_header]
            trail_styles = []
            for i, entry in enumerate(audit_trail, start=1):
                result = str(entry.get("result", "")).lower()
                ts = str(entry.get("timestamp", ""))
                # ISO tarihini daha okunaklı yap
                try:
                    dt = datetime.fromisoformat(ts)
                    ts = dt.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    pass
                trail_rows.append([
                    ts,
                    str(entry.get("user", "")),
                    str(entry.get("action", "")),
                    str(entry.get("resource", "")),
                    str(entry.get("result", "")).upper(),
                ])
                if result in ("success", "ok", "başarılı"):
                    trail_styles.append(("BACKGROUND", (4, i), (4, i), self.colors.to_reportlab(self.colors.SUCCESS)))
                    trail_styles.append(("TEXTCOLOR", (4, i), (4, i), colors.white))
                elif result in ("failure", "error", "failed", "başarısız"):
                    trail_styles.append(("BACKGROUND", (4, i), (4, i), self.colors.to_reportlab(self.colors.ERROR)))
                    trail_styles.append(("TEXTCOLOR", (4, i), (4, i), colors.white))

            trail_table = self._create_table(
                trail_rows,
                col_widths=[3.8 * cm, 3 * cm, 3 * cm, 4.2 * cm, 2.5 * cm],
                style=trail_styles,
            )
            if trail_table:
                story.append(trail_table)
        else:
            story.append(Paragraph("Denetim kaydı bulunamadı.", self.styles["body"]))

        story.append(Spacer(1, 0.5 * cm))

        # ---- Veri Kökeni Özeti --------------------------------------------
        story += self._section_header("Veri Kökeni Özeti")

        # Denetim izinden kaynak/işlem istatistikleri çıkar
        action_counts: Dict[str, int] = {}
        resource_counts: Dict[str, int] = {}
        for entry in audit_trail:
            action = entry.get("action", "unknown")
            resource = entry.get("resource", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1
            resource_counts[resource] = resource_counts.get(resource, 0) + 1

        if action_counts:
            lineage_data = [
                ["İşlem Türü", "Sayı"],
            ] + [[k, str(v)] for k, v in sorted(action_counts.items(), key=lambda x: -x[1])[:10]]
            lin_table = self._create_table(lineage_data, col_widths=[10 * cm, 6 * cm])
            if lin_table:
                story.append(Paragraph("En Sık Gerçekleştirilen İşlemler:", self.styles["subheading"]))
                story.append(lin_table)
                story.append(Spacer(1, 0.3 * cm))

        if action_counts:
            bar = self._create_bar_chart(action_counts, "İşlem Türü Dağılımı", 460, 200)
            if bar:
                story.append(bar)
                story.append(Paragraph("Şekil 2: İşlem türü dağılımı", self.styles["caption"]))
                story.append(Spacer(1, 0.4 * cm))

        # ---- Risk Değerlendirmesi -----------------------------------------
        story += self._section_header("Risk Değerlendirmesi")

        risk_items = report_data.get("risk_items", [])
        if risk_items:
            risk_header = ["Risk", "Seviye", "Azaltma Yöntemi"]
            risk_rows = [risk_header]
            risk_styles = []
            for i, risk in enumerate(risk_items, start=1):
                level = str(risk.get("level", "")).lower()
                mitigation = str(risk.get("mitigation", ""))
                if len(mitigation) > 80:
                    mitigation = mitigation[:77] + "..."
                risk_rows.append([
                    str(risk.get("risk", "")),
                    str(risk.get("level", "")).upper(),
                    mitigation,
                ])
                level_colors = {
                    "high": self.colors.ERROR,
                    "medium": self.colors.WARNING,
                    "low": self.colors.SUCCESS,
                    "critical": self.colors.ERROR,
                }
                bg_color = level_colors.get(level, self.colors.LIGHT_GRAY)
                risk_styles.append(("BACKGROUND", (1, i), (1, i), self.colors.to_reportlab(bg_color)))
                if level in ("high", "critical"):
                    risk_styles.append(("TEXTCOLOR", (1, i), (1, i), colors.white))

            risk_table = self._create_table(
                risk_rows,
                col_widths=[5 * cm, 3 * cm, 10 * cm],
                style=risk_styles,
            )
            if risk_table:
                story.append(risk_table)
        else:
            story.append(Paragraph("Risk öğesi bulunamadı.", self.styles["body"]))

        story.append(Spacer(1, 0.5 * cm))

        # ---- Oluştur --------------------------------------------------------
        try:
            doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
            logger.info("Denetim raporu oluşturuldu: %s", output_path)
            return output_path
        except Exception as exc:
            logger.error("PDF oluşturma hatası: %s", exc)
            raise

    # ------------------------------------------------------------------

    def _build_compliance_gauge(
        self,
        score: float,
        label: str,
        color_hex: str,
    ) -> Optional["Drawing"]:
        """
        Uyumluluk oranı göstergesi çizer.

        Parametreler
        ------------
        score : float
            0-100 arasında uyumluluk yüzdesi.
        label : str
            Gösterge etiketi.
        color_hex : str
            Doldurma rengi.

        Döndürür
        --------
        Drawing veya None
        """
        if not HAS_REPORTLAB:
            return None

        width, height = 400, 50
        drawing = Drawing(width, height)

        bg_rect = Rect(20, 20, 360, 20,
                       fillColor=self.colors.to_reportlab(self.colors.LIGHT_GRAY),
                       strokeColor=None, rx=4, ry=4)
        drawing.add(bg_rect)

        fill_width = max(0, min(360, 360 * score / 100))
        fill_rect = Rect(20, 20, fill_width, 20,
                         fillColor=self.colors.to_reportlab(color_hex),
                         strokeColor=None, rx=4, ry=4)
        drawing.add(fill_rect)

        drawing.add(String(200, 26, f"{score:.1f}%",
                           fontName="Helvetica-Bold", fontSize=10,
                           fillColor=colors.white if fill_width > 180
                           else self.colors.to_reportlab(self.colors.TEXT),
                           textAnchor="middle"))
        drawing.add(String(200, 5, label,
                           fontName="Helvetica", fontSize=8,
                           fillColor=self.colors.to_reportlab(self.colors.TEXT),
                           textAnchor="middle"))
        return drawing


# ---------------------------------------------------------------------------
# Kolaylık fonksiyonları
# ---------------------------------------------------------------------------

def generate_quality_report(output_path: str, report_data: dict) -> str:
    """
    QualityReport sınıfını kullanarak kalite raporu üreten yardımcı fonksiyon.

    Parametreler
    ------------
    output_path : str
        PDF çıktı yolu.
    report_data : dict
        Rapor verisi.

    Döndürür
    --------
    str
        Oluşturulan dosyanın yolu.
    """
    reporter = QualityReport()
    return reporter.generate(output_path, report_data)


def generate_test_report(output_path: str, report_data: dict) -> str:
    """
    TestReport sınıfını kullanarak test raporu üreten yardımcı fonksiyon.

    Parametreler
    ------------
    output_path : str
        PDF çıktı yolu.
    report_data : dict
        Rapor verisi.

    Döndürür
    --------
    str
        Oluşturulan dosyanın yolu.
    """
    reporter = TestReport()
    return reporter.generate(output_path, report_data)


def generate_audit_report(output_path: str, report_data: dict) -> str:
    """
    AuditReport sınıfını kullanarak denetim raporu üreten yardımcı fonksiyon.

    Parametreler
    ------------
    output_path : str
        PDF çıktı yolu.
    report_data : dict
        Rapor verisi.

    Döndürür
    --------
    str
        Oluşturulan dosyanın yolu.
    """
    reporter = AuditReport()
    return reporter.generate(output_path, report_data)


# ---------------------------------------------------------------------------
# Örnek veri şablonları
# ---------------------------------------------------------------------------

def get_sample_quality_data() -> dict:
    """
    Kalite raporu için örnek veri şablonu döndürür.

    Döndürür
    --------
    dict
        Örnek report_data sözlüğü.
    """
    return {
        "title": "Ocak 2026 Veri Kalite Raporu",
        "generated_at": datetime.now().isoformat(),
        "overall_score": 82.5,
        "total_rows": 150000,
        "total_columns": 12,
        "columns": [
            {
                "name": "musteri_id",
                "type": "integer",
                "null_ratio": 0.0,
                "unique_count": 150000,
                "mean": None,
                "std": None,
                "quality_score": 100.0,
            },
            {
                "name": "isim",
                "type": "string",
                "null_ratio": 0.002,
                "unique_count": 148500,
                "mean": None,
                "std": None,
                "quality_score": 95.0,
            },
            {
                "name": "yas",
                "type": "integer",
                "null_ratio": 0.01,
                "unique_count": 72,
                "mean": 38.4,
                "std": 12.1,
                "quality_score": 88.0,
            },
            {
                "name": "bakiye",
                "type": "float",
                "null_ratio": 0.0,
                "unique_count": 149900,
                "mean": 15230.5,
                "std": 8420.3,
                "quality_score": 92.0,
            },
            {
                "name": "kredi_skoru",
                "type": "integer",
                "null_ratio": 0.05,
                "unique_count": 550,
                "mean": 682.0,
                "std": 94.5,
                "quality_score": 75.0,
            },
            {
                "name": "sehir",
                "type": "string",
                "null_ratio": 0.08,
                "unique_count": 81,
                "mean": None,
                "std": None,
                "quality_score": 62.0,
            },
        ],
        "anomalies": [
            {"type": "Aykırı Değer", "severity": "medium", "count": 342},
            {"type": "Eksik Veri", "severity": "low", "count": 1820},
            {"type": "Format Hatası", "severity": "high", "count": 87},
            {"type": "Tekrarlı Kayıt", "severity": "low", "count": 23},
        ],
        "recommendations": [
            "kredi_skoru sütunundaki %5 eksik veri için imputation stratejisi belirleyin.",
            "sehir sütunundaki tutarsız değerlerin standartlaştırılması önerilir.",
            "Format hataları acil inceleme gerektirir; kayıt öncesi doğrulama ekleyin.",
            "Bakiye sütunundaki aykırı değerler iş kurallarıyla doğrulanmalıdır.",
        ],
    }


def get_sample_test_data() -> dict:
    """
    Test raporu için örnek veri şablonu döndürür.

    Döndürür
    --------
    dict
        Örnek report_data sözlüğü.
    """
    return {
        "title": "Otomatik Test Raporu - v2.4.1",
        "test_suite": "SyntheticBankData Test Paketi",
        "total": 148,
        "passed": 135,
        "failed": 9,
        "skipped": 4,
        "duration": 127.4,
        "tests": [
            {"name": "test_schema_analyzer_basic", "status": "passed", "duration": 0.234, "error_msg": None},
            {"name": "test_anomaly_detector_isolation_forest", "status": "passed", "duration": 1.872, "error_msg": None},
            {"name": "test_synthetic_generator_gaussian", "status": "failed", "duration": 3.501, "error_msg": "AssertionError: distribution mismatch"},
            {"name": "test_pii_detector_turkish_names", "status": "passed", "duration": 0.456, "error_msg": None},
            {"name": "test_rule_engine_compliance", "status": "failed", "duration": 0.102, "error_msg": "ValueError: rule config missing"},
            {"name": "test_export_csv", "status": "passed", "duration": 0.788, "error_msg": None},
            {"name": "test_export_parquet", "status": "skipped", "duration": 0.0, "error_msg": None},
            {"name": "test_quality_dashboard_render", "status": "passed", "duration": 2.134, "error_msg": None},
        ],
        "visual_tests": [
            {"name": "dashboard_main", "ssim_score": 0.987, "passed": True},
            {"name": "quality_report_page", "ssim_score": 0.923, "passed": True},
            {"name": "anomaly_chart", "ssim_score": 0.754, "passed": False},
        ],
        "a11y_tests": [
            {"url": "/dashboard", "score": 94.0, "violations_count": 2},
            {"url": "/reports/quality", "score": 87.5, "violations_count": 5},
            {"url": "/settings", "score": 98.0, "violations_count": 0},
        ],
    }


def get_sample_audit_data() -> dict:
    """
    Denetim raporu için örnek veri şablonu döndürür.

    Döndürür
    --------
    dict
        Örnek report_data sözlüğü.
    """
    return {
        "title": "Q1 2026 Denetim ve Uyumluluk Raporu",
        "audit_period": "01.01.2026 – 31.03.2026",
        "compliance_items": [
            {"regulation": "KVKK", "status": "Compliant", "details": "Kişisel veri işleme politikaları güncel"},
            {"regulation": "GDPR", "status": "Compliant", "details": "Veri saklama ve silme prosedürleri uyumlu"},
            {"regulation": "PCI-DSS", "status": "Non-Compliant", "details": "Kart verisi şifreleme eksiklikleri mevcut"},
            {"regulation": "ISO 27001", "status": "Partial", "details": "Erişim kontrol politikası güncelleme gerekiyor"},
            {"regulation": "BDDK", "status": "Compliant", "details": "Bankacılık düzenleme gereklilikleri karşılanıyor"},
        ],
        "audit_trail": [
            {"timestamp": "2026-01-15T09:23:11", "user": "admin", "action": "EXPORT", "resource": "musteri_veritabani", "result": "Success"},
            {"timestamp": "2026-01-20T14:45:00", "user": "analyst1", "action": "READ", "resource": "kredi_kayitlari", "result": "Success"},
            {"timestamp": "2026-02-03T11:12:33", "user": "etl_bot", "action": "WRITE", "resource": "sentetik_veri", "result": "Success"},
            {"timestamp": "2026-02-14T16:30:22", "user": "admin", "action": "DELETE", "resource": "eski_yedek", "result": "Success"},
            {"timestamp": "2026-03-01T08:55:47", "user": "analyst2", "action": "READ", "resource": "musteri_veritabani", "result": "Failure"},
            {"timestamp": "2026-03-10T13:20:05", "user": "report_svc", "action": "EXPORT", "resource": "kalite_raporu", "result": "Success"},
        ],
        "risk_items": [
            {"risk": "Şifrelenmemiş kart verisi aktarımı", "level": "High", "mitigation": "TLS 1.3 zorunlu kılınacak"},
            {"risk": "Erişim kontrol günlüğü eksikliği", "level": "Medium", "mitigation": "Merkezi log yönetimi kurulacak"},
            {"risk": "Yazılım bağımlılığı güvenlik açıkları", "level": "Low", "mitigation": "Haftalık bağımlılık taraması planlandı"},
            {"risk": "İçeriden tehdit riski", "level": "Medium", "mitigation": "Kullanıcı davranış analizi (UBA) uygulanacak"},
        ],
    }
