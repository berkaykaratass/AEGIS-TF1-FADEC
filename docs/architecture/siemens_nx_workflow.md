# AEGIS-TJ1 Siemens NX Entegrasyonu ve CFD/FEA Doğrulama Kılavuzu

AEGIS-TJ1 parametrik OpenSCAD modeli, motorun **Kavramsal Tasarım (Conceptual Design)** geometrik şablonunu oluşturur. Bu şablonun, AEGIS Aerospace Team veya havacılık standartlarında **"Savaşta Kullanılacak / Uçuşa Elverişli" (Flight-Ready / Military-Grade)** seviyesine taşınması için **Siemens NX (Simcenter Nastran & STAR-CCM+)** ortamına aktarılarak yüksek sadakatli mukavemet (FEA) ve akışkanlar mekaniği (CFD) analizlerinden geçirilmesi gerekir.

Bu dokümanda, bu entegrasyonun adım adım iş akışı, sınır koşulları ve analiz kılavuzları detaylandırılmıştır.

---

## 1. Geometrik Veri Transferi (Export / Import)

OpenSCAD modelinin Siemens NX ortamına aktarılması için takip edilen veri dönüştürme zinciri şöyledir:

```
  [OpenSCAD (.scad)] 
          │
          ▼  (make export-stl komutuyla)
  [STL Mesh (.stl)] 
          │
          ▼  (FreeCAD veya NX Convergent Modeling yardımıyla)
  [STEP / IGES Solid (.step)]
          │
          ▼
  [Siemens NX (NURBS Surface / Solid CAD)]
```

### 1.1 Otomatik STL Aktarımı
Proje kök dizininde yer alan `make export-stl` komutu, tüm OpenSCAD dosyalarını arka planda derleyerek Siemens NX'in doğrudan okuyabileceği STL formatına dönüştürür:
```bash
make export-stl
```
Bu komut, `modeling/exports/` dizini altında şu dosyaları üretir:
- `engine_assembly.stl` (Tüm motor montajı)
- `compressor.stl` (Eksenel kompresör)
- `combustor.stl` (Yanma odası)
- `turbine.stl` (Türbin kademesi)

---

## 2. Hesaplamalı Akışkanlar Dinamiği (CFD) Analizi (STAR-CCM+ / NX Flow)

Kompresör aerodinamik stall/surge marjları ve türbin verimliliği, Simcenter STAR-CCM+ üzerinde çözülür.

### 2.1 Mesh (Ağ Yapısı) Gereksinimleri
- **Tip**: Prism layer mesh (sınır tabakayı çözmek için) + Polyhedral mesh (akış bölgesinde).
- **Duvar Çözünürlüğü**: Duvar yakınındaki ilk hücre yüksekliği, $y^+ \le 1.0$ olacak şekilde ayarlanmalıdır (Türbin kanatlarındaki sınır tabaka ayrılmalarını ve EHD sınır tabaka kontrol etkisini doğru yakalamak için).

### 2.2 Sınır Koşulları (Boundary Conditions)
CFD çözücüsüne girilecek master seviye termodinamik parametreler (FADEC simülatörümüzün nominal durum çıktılarına göre belirlenmiştir):

| Sınır / Yüzey | Tip | Parametre Değerleri |
|---|---|---|
| **Kompresör Girişi (Inlet)** | Mass Flow Inlet | $\dot{m} = 2.28$ kg/s, $T_{t2} = 288.15$ K |
| **Kompresör Çıkışı (Outlet)** | Pressure Outlet | $P_3 = 5.0$ bar ($500.000$ Pa) |
| **Yanma Odası Girişi (T4)** | Inlet | $T_4 = 1450.0$ K (Turbine Inlet Temperature) |
| **EHD Izgaraları (Active Grid)** | Momentum Source | EHD itki asistanının yarattığı iyon rüzgarı akış kuvveti: $F_{ehd} = 15.0$ N (Hacimsel momentum kaynağı olarak tanımlanır) |
| **Kanat Duvarları (Blades)** | Wall (Rotating) | Kompresör mili dönüş hızı: $\omega = 1570.8$ rad/s (15.000 RPM) |

---

## 3. Sonlu Elemanlar Analizi (FEA) (Simcenter Nastran)

Rotor parçalarının yüksek merkezkaç kuvveti ve termal yükler altındaki yapısal bütünlüğü Simcenter Nastran ile doğrulanır.

### 3.1 Malzeme Atamaları (Military-Grade Alloys)
Askeri jet motorlarında kullanılan ve Nastran malzeme kütüphanesine girilecek mekanik özellikler:

- **Kompresör Disk ve Kanatçıkları**: **Ti-6Al-4V (Titanyum Alaşımı)**
  - Yoğunluk ($\rho$): $4430$ kg/m³
  - Akma Dayanımı ($\sigma_y$): $880$ MPa
  - Elastisite Modülü ($E$): $113.8$ GPa
- **Mil (Rotor Shaft)**: **Maraging Steel 300**
  - Yoğunluk ($\rho$): $8000$ kg/m³
  - Akma Dayanımı ($\sigma_y$): $1900$ MPa
- **Türbin Kanatçıkları ve Diski**: **Inconel 718 / CMSX-4 (Nickel-based Superalloy)**
  - Yoğunluk ($\rho$): $8190$ kg/m³
  - Akma Dayanımı ($\sigma_y$): $1030$ MPa ($1000^\circ\text{C}$ sıcaklıkta)

### 3.2 Yapısal Yükler (Structural Loading)
1. **Merkezkaç Kuvveti (Centrifugal Load)**:
   Disk ve kanatçıkların $\omega = 1570.8$ rad/s (15.000 RPM) dönüş hızındaki gerilme dağılımı. Kanatçık kökünde (Dovetail) oluşan çekme gerilmesi:
   $$\sigma_{tensile} = \frac{m_{blade} \cdot \omega^2 \cdot r_{cg}}{A_{root}}$$
   *Kriter: Oluşan Von Mises gerilmesi, Ti-6Al-4V akma dayanımının %60'ını ($\approx 528$ MPa) aşmamalıdır (Emniyet katsayısı $S_f = 1.6$).*

2. **Termal Gerilmeler (Thermal Stress)**:
   Türbin diski ve kanatçıklarında oluşan sıcaklık gradyanı ($T_4 = 1450$ K gaz sıcaklığından mil yatağındaki $450$ K sıcaklığa geçiş) altındaki genleşme gerilmeleri.
   *Kriter: Termal genleşme sonucunda rulman yataklarındaki eksenel sıkışma boşluğu (thermal clearance) hesaba katılmalıdır.*

---

## 4. İleri Seviye Optimizasyon Döngüsü (FADEC-NX Closed Loop)

Askeri projenin sonraki fazlarında, Python FADEC simülatörümüz ile Siemens NX arasında otomatik bir optimizasyon döngüsü kurulabilir:
1. **Yapay Zeka (MPC)** bir yakıt akış rampası simüle eder.
2. **Siemens NX**, bu rampa esnasında oluşan sıcaklık ($T_4$) ve hız ($\omega$) değişimlerini otomatik olarak Nastran ve CFD dosyalarına besler.
3. Kritik limitlerin aşılıp aşılmadığı (Surge margin limit, Türbin diski Von Mises limiti) otomatik raporlanır ve FADEC güvenlik kuralları (`contract_validator.adb`) bu limitlere göre gerçek zamanlı olarak güncellenir.
