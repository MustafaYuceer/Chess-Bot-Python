<<<<<<< HEAD
# Chess-Bot-Python
Automatic Setup - Chess bot
=======
# ⚡ Automated Chess Bot

### Yasal Uyarı / Disclaimer
> Lütfen bu programı yalnızca "PVE (Oyuncuya Karşı Bilgisayar)" - yani sitemdeki bot/bilgisayar antrenman modlarında kullanın. Gerçek rakiplere karşı kullanmak adil oyun (fair-play) kurallarına ve platform sözleşmelerine aykırıdır, hesabınızın banlanmasına yol açabilir.

### Nedir?
Bu proje, **Chess.com** üzerinde oynadığınız maçları bilgisayar görmesi (görsel DOM okuma) yardımıyla takip edip, dünyanın en güçlü açık kaynaklı satranç motorlarından biri olan **Stockfish 16.1** altyapısıyla en doğru hamleyi sizin yerinize oynayan otonom bir robottur. Arayüzü sayesinde tarayıcınızı yormadan kolayca kontrol edilebilir.

### Özellikler
* **Tam Otonom Tıklama:** Playwright ile desteklenen arka plan tıklamaları (mouse devralmaz, gizli tıklama yapar) ile sekme arkaplanda kalsa bile oyunu oynamaya devam edebilir.
* **Akıllı Senkron ve Watchdog:** Oyunun ortasından da başlatsanız veya internetiniz anlık kopsa da bot tüm tahtadaki taşları ve saatinizi saniyeler içinde baştan tarayarak koptuğu yerden devam eder ("Otomatik Kurtarma" özelliği içerir).
* **0 Ayar, Direk Başla:** Tıkladığınız anda eksik kütüphanelerinizi ve en güncel Stockfish motorunu bulup kendi içine indirip kurar.

### Kurulum Adımları
1. Bu repoyu bilgisayarınıza indirin (`Download ZIP` butonuna veya `git clone` komutuna tıklayarak).
2. Klasör içindeki **`Run_Bot.bat`** dosyasına çift tıklayın. 
3. Sizin için herhangi bir bağımsız kurulum veya Python pip ayarı yapmanız gerekmez. Bot arkada eksik kütüphaneleri ve satranç motorunu kendisi indirip derleyecektir. Her şey hazır olduğunda `IT IS READY` belirecek ve uygulamanızın arayüzü açılacaktır.

### Kullanım Kılavuzu
İşletim sistemi güvenlik kısıtlamaları yüzünden uygulamanın sıradan bir izole pencereye değil, hata ayıklama köprüsüyle bağlanmış özel izinli bir tarayıcıya bağlanması gerekir.
1. `Run_Bot.bat` dosyasını çalıştırarak bot menüsünü açın.
2. Arayüzdeki **"1. Launch Chrome (Debug Mode)"** butonuna basın. (Bu buton arkada Chrome'u çerezlerinizi bir klasörde (`chess_profile` içine) saklayarak `--remote-debugging-port=9222` argümanıyla başlatır).
3. Açılan Chrome sekmesinde chess.com'a ilk girişinizi yapın ve hazırlık olarak "Bilgisayara Karşı" bir maça başlayın.
4. Bot arayüzüne geri dönüp **"2. Connect & Start Bot"** tuşuna bastığınızda, bot o anki taşı ve sırayı otomatik okuyup saniyedeki hesaplama derinliğine göre sırası geldiğinde en sağlam hamleleri oynamaya başlayacaktır.

İyi antrenmanlar!
>>>>>>> 9eabbe3 (First Version)
