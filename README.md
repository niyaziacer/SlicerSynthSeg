# SlicerSynthSeg

3D Slicer extension for automated brain MRI segmentation using SynthSeg.

> ⚠️ **Bu README gerçek test sonuçlarına dayanmaktadır.** Tüm adımlar Windows 10/11 + Anaconda ortamında test edilmiştir.

---

## 🌟 Özellikler

- ✅ Otomatik tam beyin segmentasyonu (30+ yapı)
- ✅ Hacim ölçümü (mm³) ve CSV çıktısı
- ✅ T1, T2, FLAIR sekansları için destek
- ✅ Farklı kontrast ve çözünürlüklere karşı dayanıklı
- ✅ Klinik ve araştırma MRI verilerinde çalışır

---

## 📋 Gereksinimler

- Windows 10/11 (64-bit)
- Anaconda veya Miniconda
- 3D Slicer 5.x
- En az 8 GB RAM (16 GB önerilir)
- GPU opsiyonel (CPU ile ~2-3 dakika)

---

## ⚙️ Kurulum

### 1. Conda Ortamı Oluşturma

Anaconda Prompt'u açın ve aşağıdaki komutları **sırasıyla** çalıştırın:

```bat
conda create -n synthseg_v1 python=3.8 -y
conda activate synthseg_v1
```

### 2. Gerekli Paketleri Kurma

```bat
pip install tensorflow==2.2.0 keras==2.3.1 h5py==2.10.0 nibabel==5.0.1 numpy==1.23.5 protobuf==3.20.3 scipy==1.4.1 matplotlib==3.6.2
```

> ⚠️ **Kritik:** Paket versiyonları önemlidir. Farklı versiyonlar sessiz çökmelere yol açar.

### 3. OpenMP Çakışmasını Önleme (KRİTİK!)

Bu adımı atlamayın — atlanırsa program sessizce çöker:

```bat
conda env config vars set KMP_DUPLICATE_LIB_OK=TRUE
conda deactivate
conda activate synthseg_v1
```

### 4. SynthSeg Reposunu İndirme

```bat
cd C:\Users\KULLANICI\Desktop
git clone https://github.com/BBillot/SynthSeg.git
```

### 5. Model Dosyasını İndirme

Model dosyası (~53 MB) GitHub'dan indirilir:

```bat
curl -L -o "C:\Users\KULLANICI\Desktop\SynthSeg\models\synthseg_1.0.h5" "https://github.com/BBillot/SynthSeg/raw/master/models/synthseg_1.0.h5"
```

İndirme sonrası boyutun ~53 MB olduğunu doğrulayın:

```bat
dir "C:\Users\KULLANICI\Desktop\SynthSeg\models\synthseg_1.0.h5"
```

> ℹ️ Bu model SynthSeg 1.0 içindir. `--v1` bayrağı ile kullanılır.

---

## 🚀 Kullanım

### Komut Satırından Çalıştırma

```bat
conda activate synthseg_v1

python C:\Users\KULLANICI\Desktop\SynthSeg\scripts\commands\SynthSeg_predict.py ^
  --i "C:\Users\KULLANICI\Desktop\T1.nii.gz" ^
  --o "C:\Users\KULLANICI\Desktop\T1_seg.nii.gz" ^
  --vol "C:\Users\KULLANICI\Desktop\T1_vol.csv" ^
  --cpu --v1
```

**Parametreler:**

| Parametre | Açıklama |
|-----------|----------|
| `--i` | Girdi MRI dosyası (.nii.gz) |
| `--o` | Çıktı segmentasyon dosyası |
| `--vol` | Hacim CSV çıktısı (opsiyonel) |
| `--cpu` | CPU ile çalıştır (GPU yoksa) |
| `--v1` | SynthSeg 1.0 modelini kullan |
| `--crop 160` | Hızlı mod – sadece merkezi kırpar |
| `--threads 4` | CPU thread sayısı |

### 3D Slicer'da Kullanım

1. 3D Slicer'ı açın
2. `Edit → Application Settings → Modules → Additional module paths` kısmına `SlicerSynthSeg` klasörünü ekleyin
3. Slicer'ı yeniden başlatın
4. Modüller listesinden **SlicerSynthSeg**'i seçin
5. Ayarlar:
   - **SynthSeg Path:** `C:\Users\KULLANICI\Desktop\SynthSeg`
   - **Python Path:** `C:\Users\KULLANICI\anaconda3\envs\synthseg_v1\python.exe`
6. Girdi MRI'ı yükleyin ve **Run Segmentation**'a tıklayın

---

## 🧠 Segmente Edilen Yapılar

### Subkortikal Yapılar

| Label | Yapı | Label | Yapı |
|-------|------|-------|------|
| 2 | Sol Serebral Beyaz Madde | 41 | Sağ Serebral Beyaz Madde |
| 3 | Sol Serebral Korteks | 42 | Sağ Serebral Korteks |
| 4 | Sol Lateral Ventrikül | 43 | Sağ Lateral Ventrikül |
| 5 | Sol İnf. Lateral Ventrikül | 44 | Sağ İnf. Lateral Ventrikül |
| 7 | Sol Serebellum Beyaz Madde | 46 | Sağ Serebellum Beyaz Madde |
| 8 | Sol Serebellum Korteksi | 47 | Sağ Serebellum Korteksi |
| 10 | Sol Talamus | 49 | Sağ Talamus |
| 11 | Sol Kaudat | 50 | Sağ Kaudat |
| 12 | Sol Putamen | 51 | Sağ Putamen |
| 13 | Sol Pallidum | 52 | Sağ Pallidum |
| 17 | Sol Hipokampus | 53 | Sağ Hipokampus |
| 18 | Sol Amigdala | 54 | Sağ Amigdala |
| 26 | Sol Akkumbens | 58 | Sağ Akkumbens |
| 28 | Sol Ventral DC | 60 | Sağ Ventral DC |

### Orta Hat / Diğer

| Label | Yapı |
|-------|------|
| 14 | 3. Ventrikül |
| 15 | 4. Ventrikül |
| 16 | Beyin Sapı |
| 24 | BOS (yalnızca SynthSeg 2.0) |

---

## 🛠️ Sorun Giderme

### Program `predicting 1/1` Sonrası Sessizce Kapanıyor

**Neden:** `KMP_DUPLICATE_LIB_OK=TRUE` ayarlanmamış.

**Çözüm:**
```bat
conda activate synthseg_v1
conda env config vars set KMP_DUPLICATE_LIB_OK=TRUE
conda deactivate
conda activate synthseg_v1
```

### `AssertionError: The provided model path does not exist`

**Neden:** Model dosyası yanlış konumda.

**Çözüm:** Dosyanın şu konumda olduğunu doğrulayın:
```
SynthSeg\models\synthseg_1.0.h5
```

### `OSError: Unable to open file (file signature not found)`

**Neden:** Model dosyası Git LFS pointer'ı — gerçek model değil.

**Çözüm:** Model dosyasını `curl` ile indirin (Kurulum → Adım 5).

### `TypeError: predict() got an unexpected keyword argument`

**Neden:** Yanlış parametre ismi veya yanlış ortam.

**Çözüm:** `synthseg_v1` ortamını aktif ettiğinizden emin olun:
```bat
conda activate synthseg_v1
```

### Çıktı Dosyası Oluşmadı Ama Hata da Yok

**Neden:** `--` (çift tire) yerine `–` (uzun tire) kullanılmış — kopyala-yapıştırda oluşan yaygın hata.

**Çözüm:** `--cpu`, `--v1` gibi parametreleri **elle yazın**, kopyalamayın.

---

## 📊 Çıktı Dosyaları

| Dosya | Açıklama |
|-------|----------|
| `*_seg.nii.gz` | Segmentasyon maskesi |
| `*_vol.csv` | Her yapı için hacim (mm³) |

---

## 📚 Atıf

Bu araç kullanılıyorsa lütfen şu makaleyi atıf olarak gösterin:

> SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining  
> B. Billot, D.N. Greve, O. Puonti, A. Thielscher, K. Van Leemput, B. Fischl, A.V. Dalca, J.E. Iglesias  
> Medical Image Analysis (2023)

---

## 📄 Lisans

MIT License — Ayrıntılar için `LICENSE.txt` dosyasına bakın.
