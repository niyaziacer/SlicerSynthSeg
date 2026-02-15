# SlicerSynthSeg

3D Slicer extension for automated brain MRI segmentation using SynthSeg.

## 📖 **[→ Complete User Guide (Start Here!)](USER_GUIDE.md)** ←

**New users:** Read the [User Guide](USER_GUIDE.md) for step-by-step instructions with screenshots and troubleshooting.

---

## 🌟 Features

- ✅ Automated whole-brain segmentation (50+ structures)
- ✅ Volume quantification with Excel export
- ✅ Support for T1, T2, FLAIR sequences
- ✅ Robust to various contrasts and resolutions
- ✅ Works with clinical and research MRI data

---

## 📋 Prerequisites

**👉 [See detailed installation guide in User Guide](USER_GUIDE.md#step-1-install-prerequisites)**

### 1. Install Anaconda/Miniconda

Download from: https://www.anaconda.com/download

### 2. Create SynthSeg Environment

Open **Anaconda Prompt** and run:

```bash
# Create environment with Python 3.9 (IMPORTANT: Use 3.9, not 3.8!)
conda create -n synthseg_final python=3.9 -y

# Activate environment
conda activate synthseg_final

# Install TensorFlow and Keras from conda-forge
conda install -c conda-forge tensorflow=2.10 keras=2.10 -y

# Install other required packages
pip install nibabel scipy pandas openpyxl

# Fix OpenMP library conflict (CRITICAL!)
conda env config vars set KMP_DUPLICATE_LIB_OK=TRUE

# Reactivate environment to apply variable
conda deactivate
conda activate synthseg_final

# Verify installation
python -c "import tensorflow, keras, nibabel; print('Installation successful!')"
```

**⚠️ Important Notes:**
- **Must use Python 3.9** (not 3.8 or 3.10)
- **Must install via conda-forge** (pip versions won't work)
- **Must set KMP_DUPLICATE_LIB_OK=TRUE** (prevents OpenMP crash)

### 3. Download SynthSeg

```bash
# Clone SynthSeg repository
git clone https://github.com/BBillot/SynthSeg.git

# Note the installation path (e.g., C:\Users\YourName\SynthSeg)
```

**Important:** Remember the path where you cloned SynthSeg - you'll need it in 3D Slicer!

### 4. Download Model File

Download the pre-trained model (~50 MB):

**📥 [Download synthseg_1.0.h5 from Google Drive](https://drive.google.com/file/d/11ZW9ZxaESJk7RkMMVMAjyoGraCXgLwoq/view?usp=sharing)**

**Save to:** `SynthSeg/models/synthseg_1.0.h5`

For example:
- Windows: `C:\Users\YourName\SynthSeg\models\synthseg_1.0.h5`
- Mac/Linux: `/home/yourname/SynthSeg/models/synthseg_1.0.h5`

**Note:** Create the `models` folder if it doesn't exist!

---

## 🔧 Installation in 3D Slicer

### Method 1: Extension Manager (Coming Soon)

1. Open **3D Slicer**
2. Go to **View** → **Extension Manager**
3. Search for **"SynthSeg"**
4. Click **Install**
5. **Restart** Slicer

### Method 2: Manual Installation (Current)

1. Download this repository:
   ```
   git clone https://github.com/niyaziacer/SlicerSynthSeg.git
   ```

2. Open **3D Slicer**

3. Go to **Edit** → **Application Settings** → **Modules**

4. Click **Add** next to "Additional module paths"

5. Select the `SlicerSynthSeg` folder

6. Click **OK** and **Restart** Slicer

---

## 🚀 Usage

**👉 [Complete usage instructions with examples in User Guide](USER_GUIDE.md#-using-slicersynthseg)**

### First-Time Setup

1. Open **3D Slicer**

2. Select **SlicerSynthSeg** from the module dropdown

3. Click **"Configure Environment"**

4. Provide paths:
   - **SynthSeg Path:** `C:\Users\YourName\SynthSeg` (where you cloned SynthSeg)
   - **Python Environment:** `C:\Users\YourName\anaconda3\envs\synthseg_final\python.exe`
   
   **Example paths:**
   - Windows: `C:\Users\LENOVO\anaconda3\envs\synthseg_final\python.exe`
   - Mac/Linux: `/home/username/anaconda3/envs/synthseg_final/bin/python`
   
5. Click **"Save Configuration"**

### Running Segmentation

1. **Load** your T1 MRI image in Slicer

2. Open **SlicerSynthSeg** module

3. **Input Volume:** Select your loaded MRI

4. **Output:**
   - Segmentation name (default: auto-generated)
   - Export volumes to Excel ✅

5. Click **"Run Segmentation"**

6. Wait 3-10 minutes (depending on CPU speed)

7. **Results:**
   - Segmentation overlay appears on image
   - Volume table shows in Slicer
   - Excel file saved to output directory

---

## 📊 Output Files

After segmentation completes:

- **Segmentation file:** `[InputName]_synthseg.nii.gz`
- **Volume CSV:** `[InputName]_volumes.csv`
- **Volume Excel:** `[InputName]_volumes.xlsx`

All files saved in: `Slicer temporary directory` or specified output folder

---

## 🛠️ Troubleshooting

### "OpenMP library conflict" Error

**Error message:**
```
OMP: Error #15: Initializing libomp.dll, but found libiomp5 already initialized.
```

**Solution:**
```bash
conda activate synthseg_final
conda env config vars set KMP_DUPLICATE_LIB_OK=TRUE
conda deactivate
conda activate synthseg_final
```

### "SynthSeg not found" Error

**Solution:** Check paths in Configuration:
- SynthSeg folder must contain `SynthSeg/predict_synthseg.py`
- Python path must point to `synthseg38` environment

### "Module not loaded" Error

**Solution:** 
1. Go to **Edit** → **Application Settings** → **Modules**
2. Verify SlicerSynthSeg path is listed
3. Restart 3D Slicer

### Segmentation Takes Too Long

**Solutions:**
- ✅ Use `--fast` mode (less accurate but 2x faster)
- ✅ Close other applications
- ✅ Use GPU if available (requires CUDA setup)

### "TensorFlow not found" Error

**Solution:** Reinstall packages in Anaconda environment:

```bash
conda activate synthseg38
pip uninstall tensorflow keras
pip install tensorflow==2.10.0 keras==2.10.0
```

---

## 📚 Documentation

### Segmented Structures

SynthSeg segments **50+ brain structures** including:

- Cortical regions (frontal, temporal, parietal, occipital lobes)
- Subcortical structures (hippocampus, amygdala, thalamus, putamen, caudate)
- White matter regions
- Ventricles
- Cerebellum
- Brainstem

### Volume Quantification

Output includes:
- **Volume (mm³)** for each structure
- **Volume (cm³)** conversion
- **Total intracranial volume (ICV)**
- Hemisphere-specific measurements

---

## 🧪 Test Dataset

Sample T1 MRI images for testing: https://nifti.nimh.nih.gov/

---

## 🔗 References

- **SynthSeg Paper:** Billot et al., 2023 - *Robust machine learning segmentation for large-scale analysis of heterogeneous clinical brain MRI datasets*
- **Original Repository:** https://github.com/BBillot/SynthSeg
- **3D Slicer:** https://www.slicer.org

---

## 📝 Citation

If you use SlicerSynthSeg in your research, please cite:

**SynthSeg:**
```
@article{billot2023synthseg,
  title={SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining},
  author={Billot, Benjamin and Greve, Douglas N and Puonti, Oula and Thielscher, Axel and Van Leemput, Koen and Fischl, Bruce and Dalca, Adrian V and Iglesias, Juan Eugenio},
  journal={Medical Image Analysis},
  volume={86},
  pages={102789},
  year={2023},
  publisher={Elsevier}
}
```

**SlicerSynthSeg Extension:**
```
@software{slicersynthseg2026,
  title={SlicerSynthSeg: 3D Slicer Extension for Automated Brain MRI Segmentation},
  author={Acer, Niyazi},
  year={2026},
  url={https://github.com/niyaziacer/SlicerSynthSeg}
}
```

---

## 🤝 Contributing

Contributions welcome! Please open an issue or pull request.

---

## 📄 License

MIT License - see [LICENSE.txt](LICENSE.txt)

---

## 👨‍💻 Author

**Prof. Dr. Niyazi Acer**
- Email: acerniyazi@gmail.com
- Website: https://niyaziacer.github.io

---

## ⚠️ Disclaimer

This software is for **research purposes only**. Not intended for clinical diagnosis. Always verify results with expert analysis.

---

## 🆘 Support

- **Issues:** https://github.com/niyaziacer/SlicerSynthSeg/issues
- **Email:** acerniyazi@gmail.com
- **Documentation:** https://niyaziacer.github.io/SlicerSynthSeg
