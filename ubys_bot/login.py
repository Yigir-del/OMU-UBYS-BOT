"""OMU UBYS login and session management."""

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

import html1
from config import UBYS_BASE_URL, UBYS_LOGIN_URL, AUTO_SURVEY

logger = logging.getLogger(__name__)


class OMULogin:
    """Handle OMU UBYS authentication and session management."""

    def __init__(self, username: str, password: str):
        """Initialize UBYS login handler.
        
        Args:
            username: Student ID or username.
            password: Account password.
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._setup_session_headers()

    def _setup_session_headers(self) -> None:
        """Oturum için varsayılan başlıkları ayarla."""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_login_token(self) -> Optional[str]:
        """Giriş sayfasından CSRF tokenini al.
        
        Returns:
            CSRF token bulunduysa döner, yoksa None.
        """
        try:
            response = self.session.get(UBYS_BASE_URL, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            token_input = soup.find("input", {"name": "__RequestVerificationToken"})
            
            if token_input and "value" in token_input.attrs:
                logger.debug("CSRF token başarıyla alındı.")
                return token_input["value"]
            
            logger.error("Giriş sayfasında CSRF token bulunamadı!")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Login token alınırken hata oluştu: {e}")
            return None

    def login(self) -> Optional[requests.Session]:
        """UBYS'ye giriş yap.
        
        Returns:
            Başarılıysa aktif oturum, yoksa None.
        """
        csrf_token = self.get_login_token()
        if not csrf_token:
            logger.error("Giriş yapılamıyor - CSRF token alınamadı!")
            return None

        payload = {
            "username": self.username,
            "password": self.password,
            "__RequestVerificationToken": csrf_token,
            "xmlhttp": "XMLHttpRequest",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = self.session.post(
                UBYS_LOGIN_URL,
                data=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"{self.username} için giriş başarılı.")
            return self.session
            
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.username} için giriş başarısız: {e}")
            return None

    def check_and_complete_survey(self, class_detail_url: str) -> bool:
        """Ders detay sayfasını kontrol et ve varsa anketi çöz.
        
        Args:
            class_detail_url: Ders detay sayfasının URL'si
            
        Returns:
            True: Anket yoksa veya çözüldüyse, False: Hata oluştuysa
        """
        if not class_detail_url:
            logger.debug(f"{self.username} için classId URL sağlanmadı, anket kontrol atlanıyor.")
            return True

        try:
            logger.debug(f"{self.username} için anket sayfasına bağlanılıyor: {class_detail_url}")
            response = self.session.get(class_detail_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Anket uyarısını kontrol et - "anketi açmak için" yazısı olan butonu ara
            survey_buttons = soup.find_all("a", {"class": "btn"})
            survey_button = None
            
            for button in survey_buttons:
                button_text = button.get_text().strip().lower()
                if "anket" in button_text and "açmak" in button_text:
                    survey_button = button
                    break
            
            if not survey_button:
                logger.info(f"{self.username} için anket bulunamadı, devam ediliyor.")
                return True
            
            logger.warning(f"{self.username} için anket bulundu, çözmeye çalışılıyor...")
            
            # Anket linkini bul
            survey_link = survey_button.get("href")
            
            if survey_link:
                # Anket sayfasına git
                survey_url = survey_link if survey_link.startswith("http") else f"{UBYS_BASE_URL}{survey_link}"
                logger.info(f"{self.username} için anket çözüm sayfasına gidiliyor: {survey_url}")
                
                survey_response = self.session.get(survey_url, timeout=10)
                survey_response.raise_for_status()
                
                # Anket formunu bul ve otomatik olarak cevapla
                survey_soup = BeautifulSoup(survey_response.text, "html.parser")
                
                # En basit çözüm: tüm radio button'ları veya checkbox'ları seç
                form = survey_soup.find("form")
                if form:
                    # Form verilerini hazırla
                    form_data = {}
                    
                    # Tüm input'ları seç
                    for input_field in form.find_all("input"):
                        input_name = input_field.get("name")
                        input_value = input_field.get("value")
                        input_type = input_field.get("type", "").lower()
                        
                        if input_name and input_value:
                            if input_type in ["radio", "checkbox"]:
                                # İlk seçeneği seç
                                form_data[input_name] = input_value
                            elif input_type not in ["submit", "button"]:
                                form_data[input_name] = input_value
                    
                    # Formu gönder
                    form_action = form.get("action")
                    if form_action:
                        submit_url = form_action if form_action.startswith("http") else f"{UBYS_BASE_URL}{form_action}"
                        submit_response = self.session.post(submit_url, data=form_data, timeout=10)
                        submit_response.raise_for_status()
                        
                        logger.info(f"{self.username} için anket başarıyla çözüldü.")
                        return True
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"{self.username} için anket kontrol sırasında hata oluştu: {e}")
            return True  # Hata olsa bile devam et

    def get_page_content(self, page_url: str) -> bool:
        """Sayfa içeriğini çek ve işle.
        
        Args:
            page_url: Çekilecek sayfanın URL'si.
            
        Returns:
            True: Başarılı, False: Başarısız
        """
        try:
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()
            
            html_content = response.text
            if html_content:
                # Anket kontrolü
                if "SURVEY LAYOUT" in html_content or "anketi açmak için" in html_content.lower():
                    logger.warning(f"{self.username} için anket algılandı!")
                    if AUTO_SURVEY:
                        logger.info(f"{self.username} için anket otomatik çözülüyor...")
                        if self.check_and_complete_survey(page_url):
                            # Anketi çözdükten sonra sayfayı tekrar çek
                            response = self.session.get(page_url, timeout=10)
                            html_content = response.text
                        else:
                            logger.error(f"{self.username} için anket çözülemedi!")
                    else:
                        logger.warning(f"{self.username} için anket çözme devre dışı. Lütfen manuel çözün.")

                # HTML'i parse et
                html1.HtmlParser(html_content, self.username)
                logger.info(f"{self.username} için sayfa içeriği alındı.")
                return True
            else:
                logger.warning("Boş HTML içeriği alındı!")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Sayfa içeriği alınırken hata oluştu: {e}")
            return False

    def close(self) -> None:
        """Oturumu kapat."""
        self.session.close()
        logger.debug(f"{self.username} için oturum kapatıldı.")
