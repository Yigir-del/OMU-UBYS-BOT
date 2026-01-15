"""Hata ve anket durumlarını izle."""

import json
import os
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorTracker:
    """Hata ve anket durumlarını izle."""

    ERROR_TRACKING_FILE = "error_tracking.json"
    
    def __init__(self, base_dir: str = "."):
        """Initialize error tracker.
        
        Args:
            base_dir: Base directory for error tracking file
        """
        self.base_dir = base_dir
        self.tracking_file = os.path.join(base_dir, self.ERROR_TRACKING_FILE)
    
    def _load_tracking(self) -> Dict:
        """Takip verilerini yükle.
        
        Returns:
            Takip sözlüğü
        """
        try:
            if os.path.exists(self.tracking_file):
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Takip verileri yüklenirken hata: {e}")
        return {}
    
    def _save_tracking(self, data: Dict) -> None:
        """Takip verilerini kaydet.
        
        Args:
            data: Kaydedilecek takip verileri
        """
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Takip verileri kaydedilirken hata: {e}")
    
    def record_survey_found(self, student_id: str) -> None:
        """Anket bulunduğunu kaydet.
        
        Args:
            student_id: Öğrenci ID'si
        """
        tracking = self._load_tracking()
        
        if "surveys" not in tracking:
            tracking["surveys"] = {}
        
        tracking["surveys"][student_id] = {
            "found": True,
            "timestamp": datetime.now().isoformat(),
            "message": "Anketi çözmek için UBYS'ye giriş yapın"
        }
        
        self._save_tracking(tracking)
        logger.warning(f"{student_id} için anket bulundu")
    
    def record_fetch_error(self, student_id: str, error_msg: str = "") -> None:
        """Veri çekme hatasını kaydet.
        
        Args:
            student_id: Öğrenci ID'si
            error_msg: Hata mesajı
        """
        tracking = self._load_tracking()
        
        if "fetch_errors" not in tracking:
            tracking["fetch_errors"] = {}
        
        tracking["fetch_errors"][student_id] = {
            "error": error_msg or "Veri çekilemedi",
            "timestamp": datetime.now().isoformat(),
            "message": "Giriş bilgilerinizi kontrol edin veya anketiniz olup olmadığını kontrol edin"
        }
        
        self._save_tracking(tracking)
        logger.error(f"{student_id} için veri çekme hatası: {error_msg}")
    
    def get_survey_alerts(self) -> Dict[str, Dict]:
        """Anket uyarılarını al.
        
        Returns:
            Anket uyarıları sözlüğü
        """
        tracking = self._load_tracking()
        return tracking.get("surveys", {})
    
    def get_error_alerts(self) -> Dict[str, Dict]:
        """Hata uyarılarını al.
        
        Returns:
            Hata uyarıları sözlüğü
        """
        tracking = self._load_tracking()
        return tracking.get("fetch_errors", {})
    
    def clear_survey_alert(self, student_id: str) -> None:
        """Anket uyarısını temizle.
        
        Args:
            student_id: Öğrenci ID'si
        """
        tracking = self._load_tracking()
        
        if "surveys" in tracking and student_id in tracking["surveys"]:
            del tracking["surveys"][student_id]
            self._save_tracking(tracking)
    
    def clear_error_alert(self, student_id: str) -> None:
        """Hata uyarısını temizle.
        
        Args:
            student_id: Öğrenci ID'si
        """
        tracking = self._load_tracking()
        
        if "fetch_errors" in tracking and student_id in tracking["fetch_errors"]:
            del tracking["fetch_errors"][student_id]
            self._save_tracking(tracking)
