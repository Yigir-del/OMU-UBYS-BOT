# UBYS Bot - Öğrenci Not Takip Sistemi

## 📦 EXE Oluşturma

### 1. Gerekli Paketleri Yükle
```bash
pip install pyinstaller
```

### 2. EXE Oluştur
```bash
cd ubys_bot/ubys_bot
pyinstaller ubys_bot.spec
```

veya tek komutla:
```bash
pyinstaller --onefile --windowed --name="UBYS_Bot" gui.py
```

### 3. EXE Konumu
Oluşturulan exe dosyası şu konumda olacak:
```
ubys_bot/ubys_bot/dist/UBYS_Bot.exe
```

## 🚀 Kullanım

### GUI Üzerinden (Önerilen)
1. `UBYS_Bot.exe` dosyasını çalıştır
2. "Öğrenci Ekle" butonuna tıkla
3. Öğrenci bilgilerini gir:
   - Öğrenci No
   - Şifre
   - SAPID URL
4. "Başlat" butonuna tıkla
5. Bot arka planda çalışmaya başlayacak

### Komut Satırından
```bash
python main.py
```

## 📋 Özellikler

✅ **Öğrenci Yönetimi**
- Öğrenci ekle/sil
- Kullanıcı listesi görüntüleme
- Konfigürasyon dosyasında otomatik kayıt

✅ **Bot Kontrolü**
- Başlat/Durdur butonu
- Gerçek zamanlı durum göstergesi
- Log kayıtları görüntüleme

✅ **Otomatik İzleme**
- Periyodik not kontrolü
- Telegram bildirimi
- Oturum yönetimi

## 📝 Konfigürasyon

Kullanıcı bilgileri `users_config.json` dosyasında saklanır:
```json
[
    {
        "name": "23060487",
        "password": "password",
        "sapid": "https://ubys.omu.edu.tr/AIS/Student/Class/Index?sapid=..."
    }
]
```

## 🔔 Telegram Ayarları

`config.py` dosyasında:
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

## ⚠️ Önemli Notlar

1. **Anket Uyarısı**: Eğer UBYS'de anket varsa, önce manuel olarak çözmelisiniz
2. **Oturum Süresi**: Oturumlar 30 dakika sonra otomatik yenilenir
3. **İstek Aralığı**: Varsayılan 5 saniyede bir kontrol yapar

## 🛠️ Geliştirme

### Proje Yapısı
```
ubys_bot/
├── ubys_bot/
│   ├── gui.py          # GUI uygulaması
│   ├── main.py         # Ana bot mantığı
│   ├── login.py        # Giriş ve oturum yönetimi
│   ├── html1.py        # HTML parsing
│   ├── telegram.py     # Telegram bildirimleri
│   ├── users.py        # Kullanıcı konfigürasyonu
│   ├── config.py       # Genel ayarlar
│   └── ubys_bot.spec   # PyInstaller config
```

## 📄 Lisans

MIT License
