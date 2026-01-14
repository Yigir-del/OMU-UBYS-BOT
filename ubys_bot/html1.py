"""HTML parsing for UBYS course and exam information."""

import logging
import json
import os
from typing import List, Dict, Optional
from datetime import datetime

from bs4 import BeautifulSoup

import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)

# Notları saklamak için dosya (mutlak yol - gui.py ve config.py ile uyumlu)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRADES_FILE = os.path.join(BASE_DIR, "student_grades.json")


class HtmlParser:
    """Parse UBYS HTML content to extract course and exam information."""

    def __init__(self, html: str, student_id: str, check_changes: bool = True):
        """Initialize HTML parser.
        
        Args:
            html: HTML content to parse.
            student_id: Student ID for identification.
            check_changes: Whether to check if data has changed before sending notification.
        """
        self.html_content = html
        self.student_id = student_id
        self.courses: List[Dict[str, str]] = []
        self.check_changes = check_changes
        self.previous_data: Optional[Dict] = None
        self._parse_and_notify()

    def _parse_and_notify(self) -> None:
        """Parse HTML content and send notification."""
        self._parse_courses()
        self._send_telegram_notification()

    def _parse_courses(self) -> None:
        """HTML'den ders bilgisini ayrıştır."""
        if not self.html_content:
            logger.error("Ayrıştırılacak HTML içeriği yok!")
            return

        soup = BeautifulSoup(self.html_content, "html.parser")
        
        # Tablo div'ini bul - birkaç olası sınıf kombinasyonu dene
        table_div = soup.find("div", {"class": "table-responsive"})
        if not table_div:
            table_div = soup.find("div", class_=lambda x: x and "table" in x.lower())
        
        if not table_div:
            logger.warning(f"{self.student_id} için HTML'de ders tablosu bulunamadı! HTML boyutu: {len(self.html_content)}")
            # Debug: HTML'nin ne içerdiğini kontrol et
            if "anketi açmak için" in self.html_content.lower():
                logger.warning(f"{self.student_id} için HALA ANKET VAR! Anket sayfası geri dönmüş olabilir.")
            elif "çıkış" in self.html_content.lower() or "logoff" in self.html_content.lower():
                logger.warning(f"{self.student_id} için OTURUM KAPATILMIŞ! Tekrar giriş gerekli.")
            elif "error" in self.html_content.lower():
                logger.warning(f"{self.student_id} için HTML'de 'error' kelimesi bulundu - sunucu hatası olabilir")
            return

        # Tabloda tbody varsa onu kullan, yoksa direkt table'ı kullan
        table = table_div.find("table")
        if not table:
            logger.warning("Tablo bulunamadı!")
            return

        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
        else:
            rows = table.find_all("tr")
            # Başlık satırlarını atla
            rows = [r for r in rows if not r.find("th")]

        if not rows:
            logger.warning("Ders satırları bulunamadı!")
            return

        i = 0
        while i < len(rows):
            row = rows[i]
            columns = row.find_all("td")
            
            # Ders satırını kontrol et (rowspan="2" ile başlayan)
            if columns and columns[0].get("rowspan") == "2":
                course_info = self._extract_course_info(row, rows, i)
                if course_info:
                    self.courses.append(course_info)
                i += 2  # Ders satırı 2 satır kaplar, sonrakine geç
            else:
                i += 1
        
        logger.info(f"{self.student_id} için {len(self.courses)} ders ayrıştırıldı.")

    def _extract_course_info(self, row, rows=None, index=None) -> Optional[Dict[str, str]]:
        """Extract course information from a table row.
        
        Args:
            row: BeautifulSoup table row element.
            rows: All table rows (for accessing the next row).
            index: Current row index.
            
        Returns:
            Dictionary with course name and exam info, or None if not applicable.
        """
        columns = row.find_all("td")
        if not columns or columns[0].get("rowspan") != "2":
            return None

        course_name = columns[1].text.strip()
        exam_info = []
        
        # Bir sonraki satırdan not bilgilerini çıkar
        if rows and index is not None and index + 1 < len(rows):
            next_row = rows[index + 1]
            next_columns = next_row.find_all("td")
            if next_columns:
                exam_info = self._extract_exam_info(next_columns)
        
        return {
            "name": course_name,
            "exams": exam_info
        }

    def _extract_exam_info(self, columns) -> List[str]:
        """Extract exam information from table columns.
        
        Args:
            columns: List of table column elements.
            
        Returns:
            List of exam information strings.
        """
        exam_info = []
        
        for column in columns:
            nested_table = column.find("table")
            if nested_table:
                for nested_row in nested_table.find_all("tr"):
                    exam_cells = nested_row.find_all("td")
                    if len(exam_cells) == 2:
                        exam_type = exam_cells[0].text.strip()
                        exam_score = exam_cells[1].text.strip()
                        exam_info.append(f"{exam_type}: {exam_score}")
        
        return exam_info

    def _format_message(self) -> str:
        """Format parsed course data into a readable message.
        
        Returns:
            Formatted message string.
        """
        lines = [f"<b>📚 Öğrenci: {self.student_id}</b>\n"]
        
        if not self.courses:
            lines.append("❌ Ders bilgisi bulunamadı.")
            return "\n".join(lines)
        
        for course in self.courses:
            lines.append(f"📖 <b>{course['name']}</b>")
            
            if course["exams"]:
                for exam in course["exams"]:
                    lines.append(f"   • {exam}")
            else:
                lines.append("   • Sınav bilgisi yok")
            
            lines.append("")  # Boş satır
        
        return "\n".join(lines)

    def _has_changes(self) -> bool:
        """Check if course data has changed compared to previous data.
        
        Returns:
            True if data has changed or no previous data exists, False otherwise.
        """
        if not self.check_changes:
            return True
        
        current_data = {"courses": self.courses}
        
        if self.previous_data is None:
            self.previous_data = current_data
            return True
        
        # Verileri karşılaştır
        if self.previous_data != current_data:
            self.previous_data = current_data
            return True
        
        return False

    def _send_telegram_notification(self) -> None:
        """Değişim varsa Telegram'a gönder, HER ZAMAN notları kaydet."""
        # Değişim kontrol et
        if self._has_changes():
            message = self._format_message()
            
            try:
                notifier = telegram.TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                # Timeout'u kısa tut, hata durumunda devam et
                success = notifier.send_message(message)
                if success:
                    logger.info(f"Telegram: {self.student_id}")
            except Exception as e:
                logger.debug(f"Telegram hatası ({self.student_id}): {str(e)[:50]}")
        else:
            logger.debug(f"No changes for {self.student_id}, skipping notification")
        
        # Notları DAIMA dosyaya kaydet (değişim olup olmadığına bakmaksızın)
        self._save_grades_to_file()

    def _save_grades_to_file(self) -> None:
        """Notları dosyaya kaydet."""
        try:
            logger.debug(f"Notlar kaydediliyor: {GRADES_FILE}, {len(self.courses)} ders")
            
            # Mevcut notları yükle
            all_grades = {}
            if os.path.exists(GRADES_FILE):
                with open(GRADES_FILE, 'r', encoding='utf-8') as f:
                    all_grades = json.load(f)
            
            # Bu öğrencinin notlarını güncelle
            all_grades[self.student_id] = {
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "courses": self.courses
            }
            
            # Dosyaya kaydet
            with open(GRADES_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_grades, f, indent=4, ensure_ascii=False)
            
            logger.info(f"{self.student_id} için {len(self.courses)} ders kaydedildi: {GRADES_FILE}")
        except Exception as e:
            logger.error(f"Notlar kaydedilirken hata: {e}", exc_info=True)
