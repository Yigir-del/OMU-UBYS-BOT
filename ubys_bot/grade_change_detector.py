"""Ders not değişikliğini tespit et ve bildirim oluştur."""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GradeChangeDetector:
    """Ders notlarındaki değişiklikleri tespit et."""

    CHANGES_FILE = "grade_changes.json"
    
    def __init__(self, grades_file: str = "student_grades.json"):
        """Initialize the grade change detector.
        
        Args:
            grades_file: Path to the student grades JSON file.
        """
        self.grades_file = grades_file
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.changes_file = os.path.join(self.base_dir, self.CHANGES_FILE)

    def _load_grades(self, filepath: str) -> Optional[Dict]:
        """Notları dosyadan yükle.
        
        Args:
            filepath: Notlar dosyasının yolu
            
        Returns:
            Notlar sözlüğü veya None
        """
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Notlar yüklenirken hata: {e}")
        return None

    def _save_changes(self, changes: Dict) -> None:
        """Değişiklikleri dosyaya kaydet.
        
        Args:
            changes: Kaydedilecek değişiklikler
        """
        try:
            with open(self.changes_file, 'w', encoding='utf-8') as f:
                json.dump(changes, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Değişiklikler kaydedilirken hata: {e}")

    def _load_previous_changes(self) -> Dict:
        """Önceki değişiklikleri yükle.
        
        Returns:
            Değişiklikler sözlüğü
        """
        try:
            if os.path.exists(self.changes_file):
                with open(self.changes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Önceki değişiklikler yüklenirken hata: {e}")
        return {}

    def has_previous_data(self) -> bool:
        """Önceki veri kaydı var mı kontrol et.
        
        Returns:
            True: Önceki veri var, False: İlk yükleme
        """
        try:
            if os.path.exists(self.changes_file):
                with open(self.changes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return bool(data)  # Eğer veri varsa True döndür
        except Exception:
            pass
        return False

    def _compare_courses(self, old_courses: List[Dict], new_courses: List[Dict]) -> Dict:
        """Ders listesini karşılaştır ve değişiklikleri döndür.
        
        Args:
            old_courses: Eski ders listesi
            new_courses: Yeni ders listesi
            
        Returns:
            Değişiklikleri içeren sözlük
        """
        changes = {
            "new": [],
            "updated": [],
            "removed": [],
            "no_change": []
        }

        # Dict'e dönüştür - ders adı anahtarı olarak
        old_dict = {course.get("name", ""): course for course in old_courses}
        new_dict = {course.get("name", ""): course for course in new_courses}

        # Yeni ve güncellenen dersler
        for course_name, new_course in new_dict.items():
            if course_name not in old_dict:
                changes["new"].append({
                    "name": course_name,
                    "exams": new_course.get("exams", [])
                })
            else:
                old_course = old_dict[course_name]
                old_exams = old_course.get("exams", [])
                new_exams = new_course.get("exams", [])

                if old_exams != new_exams:
                    changes["updated"].append({
                        "name": course_name,
                        "old_exams": old_exams,
                        "new_exams": new_exams,
                        "changes": self._compare_exams(old_exams, new_exams)
                    })
                else:
                    changes["no_change"].append(course_name)

        # Silinen dersler
        for course_name in old_dict:
            if course_name not in new_dict:
                changes["removed"].append(course_name)

        return changes

    def _compare_exams(self, old_exams: List[str], new_exams: List[str]) -> List[str]:
        """Sınav notlarını karşılaştır ve farkları göster.
        
        Args:
            old_exams: Eski sınav notları
            new_exams: Yeni sınav notları
            
        Returns:
            Değişiklik açıklamaları
        """
        changes = []
        
        # Her yeni sınav kaydını kontrol et
        for new_exam in new_exams:
            if new_exam not in old_exams:
                changes.append(f"Yeni: {new_exam}")
            elif new_exam:
                # Not girildikten önce ve sonra karşılaştır
                exam_name = new_exam.split("::")[0].strip() if "::" in new_exam else new_exam
                old_exam = next((e for e in old_exams if e.startswith(exam_name)), None)
                if old_exam and old_exam != new_exam:
                    changes.append(f"Güncellendi: {exam_name} ({old_exam.split('::')[1].strip() if '::' in old_exam else 'Yok'} → {new_exam.split('::')[1].strip() if '::' in new_exam else 'Yok'})")

        return changes

    def detect_changes(self) -> Dict[str, Dict]:
        """Ders notlarındaki değişiklikleri tespit et.
        
        Returns:
            Öğrenci ID başına değişiklikleri içeren sözlük
        """
        current_grades = self._load_grades(self.grades_file)
        if not current_grades:
            logger.warning("Güncel notlar yüklenemedi")
            return {}

        # Önceki durumu yükle (changes.json'dan öğrenci başına last_data saklayalım)
        previous_state = self._load_previous_changes()
        
        all_changes = {}

        for student_id, student_data in current_grades.items():
            current_courses = student_data.get("courses", [])
            current_timestamp = student_data.get("last_updated", "")
            
            # Önceki durumu al
            previous_data = previous_state.get(student_id, {})
            previous_courses = previous_data.get("courses", [])
            previous_timestamp = previous_data.get("last_updated", "")

            # Kurslarda değişiklik var mı?
            if previous_courses != current_courses:
                course_changes = self._compare_courses(previous_courses, current_courses)
                all_changes[student_id] = {
                    "timestamp": current_timestamp,
                    "changes": course_changes,
                    "courses": current_courses
                }

        # Güncel durumu kaydet
        if all_changes or current_grades:
            self._save_changes(current_grades)

        return all_changes

    def get_notifications(self) -> List[Dict]:
        """Kullanıcıya gösterilecek bildirimleri oluştur.
        
        Returns:
            Bildirim listesi
        """
        changes = self.detect_changes()
        notifications = []

        for student_id, change_data in changes.items():
            changes_detail = change_data.get("changes", {})
            
            # Yeni dersler
            if changes_detail.get("new"):
                for course in changes_detail["new"]:
                    notifications.append({
                        "type": "new_course",
                        "student_id": student_id,
                        "title": f"Yeni ders eklendi: {course['name']}",
                        "message": f"{course['name']} dersine yeni not girişleri başladı. Lütfen kontrol edin.",
                        "severity": "info"
                    })

            # Güncellenmiş dersler
            if changes_detail.get("updated"):
                for course in changes_detail["updated"]:
                    exam_changes = course.get("changes", [])
                    course_name = course.get("name", "")
                    
                    if exam_changes:
                        for change in exam_changes:
                            notifications.append({
                                "type": "grade_update",
                                "student_id": student_id,
                                "title": f"{course_name} - {change}",
                                "message": f"{course_name} dersinde not güncellendi: {change}",
                                "severity": "warning"
                            })
                    else:
                        # Genelleştirilmiş mesaj
                        notifications.append({
                            "type": "grade_update",
                            "student_id": student_id,
                            "title": f"✏️ {course_name} - Güncelleme geldi!",
                            "message": f"{course_name} dersinin notunda güncelleme vardır.",
                            "severity": "warning"
                        })

            # Silinen dersler
            if changes_detail.get("removed"):
                for course_name in changes_detail["removed"]:
                    notifications.append({
                        "type": "course_removed",
                        "student_id": student_id,
                        "title": f"Ders silindi: {course_name}",
                        "message": f"{course_name} dersi artık listelerde gözükmüyor.",
                        "severity": "info"
                    })

        return notifications

    def get_survey_notification(self, student_id: str) -> Optional[Dict]:
        """Anket çözmesi gereken bildirim oluştur.
        
        Args:
            student_id: Öğrenci ID'si
            
        Returns:
            Bildirim sözlüğü veya None
        """
        return {
            "type": "survey",
            "student_id": student_id,
            "title": "📋 Anket Gerekli!",
            "message": "Ders hakkında anket uyarısı geldi. Lütfen anketi çözmek için sisteme giriş yapın.",
            "severity": "critical",
            "action_url": "https://ubys.omu.edu.tr"
        }

    def get_fetch_error_notification(self, student_id: str, error_msg: str = "") -> Dict:
        """Veri çekme hatasında bildirim oluştur.
        
        Args:
            student_id: Öğrenci ID'si
            error_msg: Hata mesajı
            
        Returns:
            Bildirim sözlüğü
        """
        return {
            "type": "fetch_error",
            "student_id": student_id,
            "title": "⚠️ Veri Çekme Hatası!",
            "message": f"Öğrenci verileri çekilemedi. Lütfen giriş bilgilerinizi kontrol edin veya anketiniz olup olmadığını kontrol edin. ({error_msg})",
            "severity": "error"
        }
