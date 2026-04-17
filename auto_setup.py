import os
import sys
import subprocess
import importlib
import time

def check_and_install_packages():
    required_packages = {"playwright", "stockfish", "chess", "requests"}
    missing = []
    
    for pkg in required_packages:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"[!] Eksik kütüphaneler tespit edildi: {', '.join(missing)}")
        print("[*] Otomatik olarak indiriliyor, lütfen bekleyin...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("[✓] Modüller başarıyla yüklendi!")
            
            if "playwright" in missing:
                print("[*] Playwright tarayıcı motorları (Chromium) indiriliyor...")
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                print("[✓] Tarayıcı motoru hazır.")
                
        except Exception as e:
            print(f"[X] Modül yüklemesi başarısız oldu: {e}")
            sys.exit(1)

def check_and_setup_stockfish():
    sf_dir = "stockfish"
    sf_exe = os.path.join("stockfish", "stockfish", "stockfish-windows-x86-64-avx2.exe")
    
    if os.path.exists(sf_exe):
        return
        
    print("[!] Stockfish satranç motoru eksik!")
    print("[*] Otomatik olarak indiriliyor ve çıkartılıyor...")
    
    try:
        import requests
        import zipfile
        import io
        
        url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-windows-x86-64-avx2.zip"
        response = requests.get(url)
        if response.status_code == 200:
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                z.extractall(sf_dir)
            print("[✓] Stockfish başarıyla kuruldu.")
        else:
            print(f"[X] Stockfish indirilemedi! HTTP Hata Kodu: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[X] Stockfish indirme hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("====================================")
    print(" Satranç Botu Başlatıcı & Kontrolcü ")
    print("====================================\n")
    print("Sistem gereksinimleri taranıyor...")
    
    # 1. Python modüllerini kontrol edip yükle
    check_and_install_packages()
    
    # 2. Stockfish motorunu kontrol edip yükle
    check_and_setup_stockfish()
    
    # Her şey tamsa başlatma aşaması
    time.sleep(1)
    print("\n-------------------------")
    print("      IT IS READY        ")
    print("-------------------------\n")
    print("Bot arayüzü başlatılıyor...")
    time.sleep(1)
    
    # Gui Bot'u aç (mevcut konsolu kapatmadan ayrı olarak çalıştırabilir veya doğrudan devralabilir)
    bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py")
    subprocess.Popen([sys.executable, bot_path])
