# 📖 SlicerSynthSeg User Guide

Complete step-by-step guide for using SlicerSynthSeg to segment brain MRI scans.

---

## 🎯 Quick Start (5 Steps)

### Step 1: Install Prerequisites

1. **Download and install Anaconda:**
   - https://www.anaconda.com/download
   - Choose "Just Me" during installation

2. **Download and install 3D Slicer:**
   - https://download.slicer.org/
   - Version 5.0 or newer

---

### Step 2: Set Up Python Environment

Open **Anaconda Prompt** and run these commands one by one:

```bash
# Create environment with Python 3.9
conda create -n synthseg_final python=3.9 -y

# Activate environment
conda activate synthseg_final

# Install TensorFlow and Keras
conda install -c conda-forge tensorflow=2.10 keras=2.10 -y

# Install other packages
pip install nibabel scipy pandas openpyxl

# Fix OpenMP conflict (CRITICAL!)
conda env config vars set KMP_DUPLICATE_LIB_OK=TRUE

# Reactivate
conda deactivate
conda activate synthseg_final

# Verify
python -c "import tensorflow, keras; print('✓ Installation successful!')"
```

**⚠️ If you see errors:** Make sure each command completes before running the next one.

---

### Step 3: Download SynthSeg

**Option A: Using Git** (Recommended)
```bash
cd C:\Users\YourName\Documents
git clone https://github.com/BBillot/SynthSeg.git
```

**Option B: Manual Download**
1. Go to: https://github.com/BBillot/SynthSeg
2. Click **Code** → **Download ZIP**
3. Extract to: `C:\Users\YourName\Documents\SynthSeg`

---

### Step 4: Download Model File

1. **Download synthseg_1.0.h5** (~50 MB):
   - [Click here to download](https://drive.google.com/file/d/11ZW9ZxaESJk7RkMMVMAjyoGraCXgLwoq/view?usp=sharing)

2. **Save to:**
   - `C:\Users\YourName\Documents\SynthSeg\models\synthseg_1.0.h5`
   
3. **Create `models` folder if it doesn't exist**

---

### Step 5: Install SlicerSynthSeg Extension

**Option A: From Extension Manager** (Coming Soon)
1. Open **3D Slicer**
2. **View** → **Extension Manager**
3. Search: **"SynthSeg"**
4. Click **Install**

**Option B: Manual Installation** (Current)
1. Download SlicerSynthSeg:
   ```bash
   cd C:\Users\YourName\Documents
   git clone https://github.com/niyaziacer/SlicerSynthSeg.git
   ```

2. Open **3D Slicer**
3. **Edit** → **Application Settings** → **Modules**
4. Click **Add** next to "Additional module paths"
5. Select: `C:\Users\YourName\Documents\SlicerSynthSeg\SlicerSynthSeg`
6. Click **OK** → **Restart Slicer**

---

## 🚀 Using SlicerSynthSeg

### First-Time Configuration

1. Open **3D Slicer**
2. Select **SlicerSynthSeg** from module dropdown
3. Click **"Configure Environment"**
4. Enter paths:

   **SynthSeg Path:**
   ```
   C:\Users\YourName\Documents\SynthSeg
   ```
   
   **Python Executable:**
   ```
   C:\Users\YourName\anaconda3\envs\synthseg_final\python.exe
   ```
   
   ⚠️ **Replace "YourName" with your actual Windows username!**

5. Click **"Save"**
6. Click **"Test Configuration"** to verify

---

### Running Segmentation

#### Method 1: Through GUI (Coming Soon)

1. **Load your T1 MRI:**
   - **File** → **Add Data**
   - Select your `.nii` or `.nii.gz` file
   - Click **OK**

2. **Select SlicerSynthSeg module**

3. **Choose input volume** from dropdown

4. Click **"Run Segmentation"**

5. **Wait 3-10 minutes** (progress will show in Python Console)

6. **View results:**
   - Segmentation overlay appears on image
   - Volume table shows in Slicer
   - Excel file saved in output directory

---

#### Method 2: Through Python Console (Current Workaround)

1. **Load your T1 MRI:**
   - **File** → **Add Data**
   - Select your `.nii` or `.nii.gz` file
   - Note the volume name (e.g., "T1")

2. **Open Python Console:**
   - **View** → **Python Interactor**

3. **Run this code:**
   ```python
   from SlicerSynthSeg import SlicerSynthSegLogic
   logic = SlicerSynthSegLogic()
   
   # Replace 'T1' with your volume name
   inputVolume = slicer.util.getNode('T1')
   
   # Run segmentation
   logic.process(inputVolume)
   ```

4. **Wait 3-10 minutes**

5. **View results** in scene

---

## 📂 Where Are My Results?

Results are saved in temporary folder:
```
C:\Users\YourName\AppData\Local\Temp\[random_folder]\
```

Files created:
- `segmentation.nii.gz` - Brain segmentation
- `volumes.xlsx` - Volume measurements

**To keep results:**
1. Load segmentation in Slicer
2. **File** → **Save**
3. Choose your destination folder

---

## 🔧 Troubleshooting

### "Not configured" Error

**Solution:** Click "Configure Environment" and enter correct paths.

**Find your Python path:**
```bash
conda activate synthseg_final
where python
```

---

### "OpenMP library conflict" Error

**Solution:** Set environment variable

**Windows:**
1. Search → "Environment Variables"
2. Click "Edit environment variables for your account"
3. Click "New"
4. Variable name: `KMP_DUPLICATE_LIB_OK`
5. Variable value: `TRUE`
6. Click OK
7. **Restart Slicer**

**Mac/Linux:**
```bash
export KMP_DUPLICATE_LIB_OK=TRUE
```

---

### "Input Volume selector not working"

**Temporary workaround:** Use Python Console method (see above)

**Permanent fix:** Coming in next update

---

### Segmentation Takes Too Long

**Normal time:** 3-10 minutes on CPU

**Speed it up:**
- Close other applications
- Use `--fast` mode (slightly less accurate)
- Consider GPU version (requires CUDA setup)

---

### "Model not found" Error

**Solution:** Download model file and place in correct location:
- Download: [synthseg_1.0.h5](https://drive.google.com/file/d/11ZW9ZxaESJk7RkMMVMAjyoGraCXgLwoq/view?usp=sharing)
- Save to: `SynthSeg/models/synthseg_1.0.h5`

---

## 📊 Understanding Results

### Segmentation File
- **Format:** NIfTI (.nii.gz)
- **Content:** Labeled brain regions (50+ structures)
- **Each voxel:** Integer label (0-99+)

### Volume Measurements
- **Hippocampus** - Memory formation
- **Amygdala** - Emotion processing
- **Thalamus** - Sensory relay
- **Caudate** - Motor control
- **Putamen** - Movement regulation
- **Lateral ventricles** - CSF spaces
- **Cortical regions** - Higher cognition
- **White matter** - Neural connections

---

## 🎓 Example Workflow

### Clinical Research Example

**Goal:** Measure hippocampal volumes in Alzheimer's patients

1. **Collect T1 MRI scans** (DICOM or NIfTI)
2. **Load in Slicer** (File → Add DICOM Data)
3. **Run SynthSeg** for each scan
4. **Export volumes** to Excel
5. **Statistical analysis** in SPSS/R/Python

### Longitudinal Study Example

**Goal:** Track brain volume changes over time

1. **Scan patient at multiple timepoints**
2. **Segment each scan** with SynthSeg
3. **Compare volumes** across timepoints
4. **Visualize changes** in Slicer or Excel

---

## 💡 Tips for Best Results

### Image Quality
- ✅ **Use T1-weighted MRI** (best results)
- ✅ Works with T2, FLAIR (good results)
- ✅ Any resolution (auto-resampled)
- ✅ Any field strength (1.5T, 3T, 7T)
- ❌ Avoid heavily motion-corrupted scans

### Processing
- **First run:** Takes longer (model loading)
- **Subsequent runs:** Faster (model cached)
- **Batch processing:** Use Python script

---

## 🆘 Support

**Issues:** https://github.com/niyaziacer/SlicerSynthSeg/issues

**Email:** acerniyazi@gmail.com

**Documentation:** https://niyaziacer.github.io

---

## 📚 Additional Resources

**SynthSeg Paper:**
- Billot et al. (2023) "SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining"
- https://doi.org/10.1016/j.media.2023.102789

**3D Slicer Tutorials:**
- https://www.slicer.org/wiki/Documentation/4.10/Training

**FreeSurfer (Advanced):**
- https://surfer.nmr.mgh.harvard.edu/

---

## ✅ Quick Checklist

Before running segmentation:

- [ ] Anaconda installed
- [ ] Python environment created (`synthseg_final`)
- [ ] TensorFlow/Keras installed
- [ ] KMP_DUPLICATE_LIB_OK set to TRUE
- [ ] SynthSeg downloaded
- [ ] Model file downloaded (synthseg_1.0.h5)
- [ ] 3D Slicer installed
- [ ] SlicerSynthSeg extension added
- [ ] Paths configured in Slicer
- [ ] T1 MRI loaded

**All checked?** You're ready to segment! 🚀

---

*Last updated: February 15, 2026*
