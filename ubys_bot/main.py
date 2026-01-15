"""Main application for UBYS Bot - monitors and reports student grades."""

import logging
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Dict, Optional

import login
import users
import config
import grade_change_detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ubys_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Configure stdout encoding for Windows
if sys.platform == 'win32' and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Global flag to control bot execution
_bot_running = True


class SessionManager:
    """Manage user sessions with automatic renewal."""

    def __init__(self, username: str, password: str, sapid: str):
        """Initialize session manager.
        
        Args:
            username: Student ID.
            password: Account password.
            sapid: SAP ID URL for data retrieval.
        """
        self.username = username
        self.password = password
        self.sapid = sapid
        self.login_handler: Optional[login.OMULogin] = None
        self.session_start_time: float = 0

    @contextmanager
    def _get_login_handler(self):
        """Context manager for login handler lifecycle."""
        handler = login.OMULogin(self.username, self.password)
        try:
            yield handler
        finally:
            handler.close()

    def _is_session_expired(self) -> bool:
        """Check if current session has expired.
        
        Returns:
            True if session expired, False otherwise.
        """
        return time.time() - self.session_start_time >= config.SESSION_TIMEOUT

    def _renew_session(self) -> bool:
        """Oturum süresi dolduysa yenile.
        
        Returns:
            True: Başarılı, False: Başarısız
        """
        if self._is_session_expired() and self.login_handler:
            logger.info(f"{self.username} için oturum süresi doldu, yenileniyor...")
            session = self.login_handler.login()
            if session:
                self.session_start_time = time.time()
                logger.info(f"{self.username} için oturum başarıyla yenilendi.")
                return True
            else:
                logger.error(f"{self.username} için oturum yenileme başarısız!")
                return False
        return True

    def fetch_student_data(self) -> bool:
        """Öğrenci verisini çek ve işle.
        
        Returns:
            True: Başarılı, False: Başarısız
        """
        with self._get_login_handler() as handler:
            self.login_handler = handler
            
            # Giriş yapmayı dene
            session = handler.login()
            if not session:
                logger.error(f"{self.username} için giriş başarısız!")
                return False

            logger.info(f"{self.username} için oturum açıldı.")
            self.session_start_time = time.time()

            # Gerekirse oturumu yenile
            if not self._renew_session():
                return False
            
            # Sayfa içeriğini çek
            success = handler.get_page_content(self.sapid)
            if success:
                logger.info(f"{self.username} için veriler başarıyla çekildi.")
            else:
                logger.error(f"{self.username} için veri çekme başarısız!")
            
            return success


def process_user(user_config: Dict[str, str]) -> None:
    """Tek bir kullanıcının verisini işle (delay olmadan).
    
    Args:
        user_config: Kullanıcı bilgileri ve SAP ID içeren sözlük.
    """
    if not _bot_running:
        return
        
    username = user_config.get("name", "")
    password = user_config.get("password", "")
    sapid = user_config.get("sapid", "")

    if not all([username, password, sapid]):
        logger.warning(f"Eksik kullanıcı konfigürasyonu: {user_config}")
        return

    logger.info(f"{username} öğrencisinin verisi işleniyor...")
    
    try:
        manager = SessionManager(username, password, sapid)
        success = manager.fetch_student_data()
        
        # Veri çekme başarısız ise (anket veya hata)
        if not success:
            logger.warning(f"{username} için veri çekme başarısız - muhtemelen anket var veya hata oluştu")
    except Exception as e:
        logger.error(f"{username} için işlem sırasında hata oluştu: {e}", exc_info=True)


def run_monitoring_loop() -> None:
    """Ana izleme döngüsünü başlat (paralel işleme ile).

    Öğrencileri ThreadPoolExecutor ile paralel işler.
    """
    global _bot_running
    _bot_running = True
    
    logger.info("UBYS Bot başlatıldı.")
    
    # Kullanıcıları konfigürasyondan yükle
    user_list = config.load_users_from_env() or users.user_list
    
    if not user_list:
        logger.error("Hiçbir kullanıcı tanımlı değil. Lütfen GUI üzerinden ekleyin!")
        return

    logger.info(f"{len(user_list)} öğrenci izleniyor.")

    # Max 3 öğrenciyi paralel işle
    max_workers = min(3, len(user_list))
    
    try:
        iteration = 0
        while _bot_running:
            iteration += 1
            
            # Her iterasyonda config'i yeniden yükle (GUI ayarları anlık etkinleşsin)
            config.load_settings()
            
            logger.info(f"İzleme döngüsü #{iteration} başlatılıyor... (İstek Aralığı: {config.REQUEST_DELAY}s)")
            
            # Öğrencileri paralel işle
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_user, user) for user in user_list]
                
                # Tüm işlemlerin tamamlanmasını bekle (interruptible)
                for future in futures:
                    if not _bot_running:
                        break
                    try:
                        future.result(timeout=30)
                    except Exception as e:
                        logger.error(f"Kullanıcı işleme hatası: {e}")
            
            if not _bot_running:
                break
            
            # Her döngüde güncel delay değerini oku
            current_delay = config.REQUEST_DELAY
            logger.info(f"Döngü #{iteration} tamamlandı. Kullanılan istek aralığı: {current_delay}s")
            
            # Sleep with interruption check (0.5 saniye arayla kontrol - daha hızlı tepki)
            check_interval = 0.5
            elapsed = 0
            while elapsed < current_delay and _bot_running:
                time.sleep(check_interval)
                elapsed += check_interval
            
    except KeyboardInterrupt:
        logger.info("Bot kullanıcı tarafından durduruldu.")
    except Exception as e:
        logger.critical(f"Ana izleme döngüsünde kritik hata: {e}", exc_info=True)
    finally:
        _bot_running = False
        logger.info("Bot durduruldu.")


def stop_bot():
    """Botu durdur."""
    global _bot_running
    _bot_running = False
    logger.info("Bot durdurma talebi alındı...")


if __name__ == "__main__":
    run_monitoring_loop()
