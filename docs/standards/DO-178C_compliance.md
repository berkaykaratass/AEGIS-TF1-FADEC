# AEGIS-TJ1 DO-178C Uyum Kılavuzu (DO-178C DAL A Compliance Checklist)

AEGIS-TJ1 FADEC sistemi, havacılık standartlarında en kritik güvenlik seviyesi olan **DO-178C DAL A (Design Assurance Level A - Catastrophic)** gereksinimlerini karşılayacak şekilde tasarlanmıştır. Bu doküman, projenin bu seviyedeki uyumluluğunu doğrulamak için takip edilen metodolojileri, kodlama standartlarını ve doğrulama kontrol listelerini içerir.

---

## 1. Yazılım Tasarım Güvencesi Seviyesi (DAL A)
DAL A seviyesi yazılımlarda oluşabilecek hatalar uçak veya motor kaybına (Catastrophic) yol açabileceğinden, sistemde sıfır tekil hata noktası (No Single Point of Failure) ve %100 test kapsamı (Modified Condition/Decision Coverage - MC/DC) hedeflenmiştir.

---

## 2. DO-178C Uyum Kontrol Listesi (Compliance Checklist)

| Süreç / Gereksinim | Durum | Doğrulama Yöntemi / Dosya Referansı |
|---|---|---|
| **Yazılım Yaşam Döngüsü Planlaması (Planning)** | ✅ Tamamlandı | Yazılım Geliştirme Planı (SDP) ve Konfigürasyon Yönetim Planı (CMP) tanımlandı. |
| **Yazılım Gereksinim Süreci (Requirements)** | ✅ Tamamlandı | Yüksek Seviyeli Gereksinimler (HLR) ve Düşük Seviyeli Gereksinimler (LLR) mimari dokümanlarda eşleştirilmiştir. |
| **Tasarım Süreci (Architecture)** | ✅ Tamamlandı | Çift yedekli emniyet guard mimarisi (MISRA C FADEC + SPARK Ada Emniyet Zarfı) uygulandı. |
| **Kodlama Standartları (Coding Standards)** | ✅ Tamamlandı | C kodları için **MISRA C:2012** zorunlu kuralları, Ada kodları için **SPARK Ada 2012** formal ispat kuralları uygulandı. |
| **Entegrasyon Süreci (Integration)** | ✅ Tamamlandı | C derleme ortamı ve Python AI modelleri izole Docker container'larında doğrulanmış derleme zincirleriyle (compilation toolchain) entegre edilmiştir. |
| **Gereksinim İzlenebilirliği (Requirements Traceability)** | ✅ Tamamlandı | Her kontrol döngüsü ve emniyet koruması ilişkili gereksinim kimliği (ID) ile ilişkilendirilmiştir. |
| **Yazılım Doğrulama (Verification - Testing)** | ✅ Sürmekte | Unit testler, Entegrasyon testleri ve Emniyet Zarfı testleri çalıştırılmaktadır. |
| **Yapısal Analiz Kapsamı (Structural Coverage - MC/DC)** | ✅ Planlandı | DAL A gereği MC/DC %100 kapsama analizi GCOV/LCOV ve Ada gnatprove araçları yardımıyla gerçekleştirilir. |

---

## 3. Kodlama ve Emniyet Pratikleri

### 3.1 MISRA C:2012 Uyumluluğu (FADEC Çekirdek)
Çekirdek kodlarımız (`core/src/`) aşağıdaki temel MISRA kurallarına uygun olarak yazılmıştır:
- **Dinamik Bellek Yönetimi Yasaktır (Rule 21.3)**: `malloc`, `calloc` veya `free` kullanılmamış, tüm değişkenler ve tamponlar statik olarak derleme zamanında ayrılmıştır.
- **Kritik Blok Parantezleri (Rule 15.6)**: Tüm `if`, `else`, `while` ve `for` bloklarında tek satırlık gövdeler olsa bile süslü parantez (`{}`) kullanımı zorunlu tutulmuştur.
- **Güvenli Aritmetik**: Sıfıra bölme, taşma (overflow) ve eksilme (underflow) risklerine karşı tüm matematik işlemlerinden önce girdi denetimleri uygulanmıştır. (Örneğin; `fadec_hal.c` içerisindeki gürültü üretecinin float dönüşüm düzeltmeleri).
- **Tip Güvenliği**: Standart tip tanımları (`stdint.h`) kullanılarak platformdan bağımsız veri boyutu garantilenmiştir.

### 3.2 SPARK Ada 2012 Formal Doğrulama (Güvenlik Katmanı)
`core/ada/` dizinindeki emniyet kritik kontrolör, formal yöntemlerle doğrulanmıştır:
- **Runtime Error Absence**: SPARK kanıtlayıcı (`gnatprove`), kodun çalışma zamanında hiçbir şekilde dizi sınır aşımı (out-of-bounds), sıfıra bölme veya bellek sızıntısı vermeyeceğini matematiksel olarak ispatlar (`pragma SPARK_Mode (On)`).
- **Kontrat Tabanlı Tasarım (Design by Contract)**: Alt programlarda `Pre => ...` (ön koşul) ve `Post => ...` (art koşul) sözdizimleri kullanılarak motorun güvenli çalışma zarfının dışına çıkması engellenmiştir.

---

## 4. Test Kapsamı ve İzlenebilirlik Matrisi

Tüm doğrulamalar `tests/` dizininde otomatik test senaryoları ile yürütülür:
1. **Unit Tests (`tests/unit/`)**:
   - `test_brayton.py`: Brayton çevrim formüllerinin fiziksel tutarlılığını test eder.
   - `test_compressor_map.py`: Moore-Greitzer RK4 çözücüsünün kararlılığını doğrular.
   - `test_surge_predictor.py`: DRL modelinin surge riski tahmin başarısını test eder.
   - `test_anomaly.py`: Wavelet CWT morlet dönüşüm doğruluğunu kontrol eder.
2. **Integration Tests (`tests/integration/`)**:
   - `test_fadec_pipeline.py`: Dijital ikiz telemetri akışının EGT, RPM ve basınç sınırları içerisinde gürültüsüz süzülmesini ve Telemetry Ingester tarafından doğrulanmasını test eder.
   - `test_digital_twin.py`: Extended Kalman Filter (EKF) durum düzeltmelerini test eder.
3. **Safety Tests (`tests/safety/`)**:
   - `test_do178c_coverage.py`: DAL A yapısal kapsama testi ve hata enjeksiyonu (fault injection) senaryolarını içerir.

---

## 5. Konfigürasyon Yönetimi ve CI/CD
DO-178C standartlarına uygun olarak kod tabanındaki her değişiklik:
- GitHub Actions CI pipeline (`.github/workflows/ci-pipeline.yml`) üzerinde test edilir.
- Değişiklik geçmişi ve onaylayan baş mühendis bilgileri Git logları vasıtasıyla kayıt altına alınarak geriye dönük izlenebilirlik sağlanır.
