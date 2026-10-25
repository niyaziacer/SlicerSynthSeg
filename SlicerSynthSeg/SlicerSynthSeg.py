import os
import time
import logging
import subprocess
import tempfile
import shutil
import importlib.util
import csv
import hashlib
import urllib.request
import colorsys
from pathlib import Path

import qt, ctk, slicer
from slicer.ScriptedLoadableModule import *

#
# Anatomical names for the fixed SynthSeg v1.0 segmentation label set.
# Verified against SynthSeg/data/labels_classes_priors segmentation_labels.npy /
# segmentation_names.npy (BBillot/SynthSeg); matches standard FreeSurferColorLUT naming.
#
SYNTHSEG_V1_LABELS = {
    2: "Left-Cerebral-White-Matter",
    3: "Left-Cerebral-Cortex",
    4: "Left-Lateral-Ventricle",
    5: "Left-Inf-Lat-Vent",
    7: "Left-Cerebellum-White-Matter",
    8: "Left-Cerebellum-Cortex",
    10: "Left-Thalamus",
    11: "Left-Caudate",
    12: "Left-Putamen",
    13: "Left-Pallidum",
    14: "3rd-Ventricle",
    15: "4th-Ventricle",
    16: "Brain-Stem",
    17: "Left-Hippocampus",
    18: "Left-Amygdala",
    26: "Left-Accumbens-area",
    28: "Left-VentralDC",
    41: "Right-Cerebral-White-Matter",
    42: "Right-Cerebral-Cortex",
    43: "Right-Lateral-Ventricle",
    44: "Right-Inf-Lat-Vent",
    46: "Right-Cerebellum-White-Matter",
    47: "Right-Cerebellum-Cortex",
    49: "Right-Thalamus",
    50: "Right-Caudate",
    51: "Right-Putamen",
    52: "Right-Pallidum",
    53: "Right-Hippocampus",
    54: "Right-Amygdala",
    58: "Right-Accumbens-area",
    60: "Right-VentralDC",
}

# TensorFlow installed into Slicer's own Python for the default engine. Pinned to the version that was
# verified against the original TF 2.4.1 environment (see SlicerSynthSegLib/run_synthseg_tfkeras.py).
SLICER_TF_REQUIREMENTS = ["tensorflow==2.21.*", "tf-keras==2.21.*"]
ENGINE_LABELS = {
    "slicer": "Slicer's Python (recommended, no conda needed)",
    "custom": "Custom Python / conda environment",
}

# Fixed CLI invocation parameters for the proven-working Windows method
SYNTHSEG_TIMEOUT_SECONDS = 1800  # 30 minutes
SYNTHSEG_THREADS = "4"

# Google Drive file id for the bundled v1.0 model (set by the maintainer before release)
SYNTHSEG_V1_MODEL_DRIVE_ID = "11ZW9ZxaESJk7RkMMVMAjyoGraCXgLwoq"
SYNTHSEG_V1_MODEL_DRIVE_VIEW_URL = f"https://drive.google.com/file/d/{SYNTHSEG_V1_MODEL_DRIVE_ID}/view?usp=sharing"

# Official download location of the SynthSeg 2.0 models (from the SynthSeg README, BBillot/SynthSeg).
# The 2.0 models are not redistributed by this extension: they are taken from the user's FreeSurfer
# installation ($FREESURFER_HOME/models) or downloaded by the user from this link.
SYNTHSEG_OFFICIAL_MODELS_URL = (
    "https://liveuclac-my.sharepoint.com/:f:/g/personal/rmappmb_ucl_ac_uk/"
    "EtlNnulBSUtAvOP6S99KcAIBYzze7jTPsmFk2_iHqKDjEw?e=rBP0RO"
)

# Automatic model download. The SynthSeg authors (B. Billot, J.E. Iglesias) allowed this extension to
# redistribute the models (e-mail, 23 Oct 2026). Sources are tried in order and every file must match
# its SHA-256 before it is used, so a partial download or a Google Drive warning page is never accepted.
MODEL_RELEASE_URL = "https://github.com/niyaziacer/SlicerSynthSeg/releases/download/models-v1"
MODEL_RELEASE_PAGE = "https://github.com/niyaziacer/SlicerSynthSeg/releases/tag/models-v1"
MODEL_SHA256 = {
    "synthseg_1.0.h5": "7d2e32d298fe38dc51ea38e6a8e8fc5c665d56b63cddb409e8b199535f8b5298",
    "synthseg_2.0.h5": "f190bfd742f450ef3ca2c9df9ed4d2e0232b3a74471da5e51b7770bacdf80c3e",
    "synthseg_parc_2.0.h5": "83bb1de76fb6f173c6dacacd433f81209fc6abb1dbc179a930ec06ecabbeb684",
}
# Google Drive mirror (file ids); None = no mirror for that file yet.
MODEL_DRIVE_IDS = {
    "synthseg_1.0.h5": SYNTHSEG_V1_MODEL_DRIVE_ID,
    "synthseg_2.0.h5": None,
    "synthseg_parc_2.0.h5": None,
}

# Citation written into every exported volume table (requested by the SynthSeg authors)
CITATION_MEDIA = "Billot B et al., SynthSeg, Medical Image Analysis 2023"
CITATION_PNAS = "Billot B et al., SynthSeg 2.0, PNAS 2023"
SYNTHSEG_CITATIONS = {
    "v1": CITATION_MEDIA,
    "v2": CITATION_MEDIA + "; " + CITATION_PNAS,
    "v2parc": CITATION_MEDIA + "; " + CITATION_PNAS,
}

# Model choices: (label shown in the panel, CLI flags, model files needed in SynthSeg/models)
SYNTHSEG_MODES = {
    "v1": ("SynthSeg 1.0", ["--v1"], ["synthseg_1.0.h5"]),
    "v2": ("SynthSeg 2.0", [], ["synthseg_2.0.h5"]),
    "v2parc": ("SynthSeg 2.0 + cortical parcellation", ["--parc"], ["synthseg_2.0.h5", "synthseg_parc_2.0.h5"]),
}
ALL_MODEL_FILES = ["synthseg_1.0.h5", "synthseg_2.0.h5", "synthseg_parc_2.0.h5"]


class DownloadCancelled(Exception):
    pass


def fileSha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def modelSources(name):
    """(source label, URL) pairs for one model file, in the order they are tried."""
    sources = [("GitHub", f"{MODEL_RELEASE_URL}/{name}")]
    driveId = MODEL_DRIVE_IDS.get(name)
    if driveId:
        sources.append(("Google Drive",
                        f"https://drive.usercontent.google.com/download?id={driveId}&export=download&confirm=t"))
    return sources


def downloadModelFile(name, dest, progress=None):
    """Download one model into dest, trying every source until one gives a file with the expected
    SHA-256. progress(sourceLabel, bytesDone, bytesTotal) may return False to cancel.
    Returns (ok, message)."""
    dest = Path(dest)
    part = dest.with_name(dest.name + ".part")
    expected = MODEL_SHA256[name]
    errors = []
    for label, url in modelSources(name):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SlicerSynthSeg"})
            h, done = hashlib.sha256(), 0
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    done += len(chunk)
                    if progress and progress(label, done, total) is False:
                        raise DownloadCancelled()
            if h.hexdigest() != expected:
                errors.append(f"{label}: file did not match the expected SHA-256 ({done / 2**20:.1f} MB received)")
                continue
            os.replace(part, dest)
            return True, f"downloaded from {label}"
        except DownloadCancelled:
            raise
        except Exception as e:
            errors.append(f"{label}: {e}")
        finally:
            if part.exists():
                part.unlink()
    return False, "; ".join(errors)


MODULE_DIR = Path(__file__).resolve().parent


def bundledSynthSegPath():
    """The SynthSeg source shipped with this extension: next to the module (installed extension) or one level
    up (source checkout). Returns None if not found."""
    for candidate in (MODULE_DIR / "SynthSeg", MODULE_DIR.parent / "SynthSeg"):
        if (candidate / "scripts" / "commands" / "SynthSeg_predict.py").exists():
            return candidate
    return None


def pythonSlicerPath():
    """PythonSlicer: Slicer's Python interpreter as a separate process (TensorFlow then never loads into the
    Slicer application itself)."""
    found = shutil.which("PythonSlicer")
    if found:
        return found
    exe = "PythonSlicer.exe" if os.name == "nt" else "PythonSlicer"
    candidate = Path(slicer.app.slicerHome) / "bin" / exe
    return str(candidate) if candidate.exists() else None


def slicerTensorFlowInstalled():
    """True if TensorFlow and tf-keras are installed in Slicer's Python (checked without importing them)."""
    return all(importlib.util.find_spec(m) is not None for m in ("tensorflow", "tf_keras"))


def installSlicerTensorFlow():
    """pip-install TensorFlow + tf-keras into Slicer's Python without letting pip change numpy (other extensions
    and Slicer itself depend on it). Returns (ok, message)."""
    import numpy
    numpyBefore = numpy.__version__
    constraints = Path(tempfile.gettempdir()) / "SlicerSynthSeg_constraints.txt"
    constraints.write_text(f"numpy=={numpyBefore}\n")
    try:
        slicer.util.pip_install(SLICER_TF_REQUIREMENTS + ["-c", str(constraints)])
    except Exception as e:
        return False, f"pip could not install {' '.join(SLICER_TF_REQUIREMENTS)} next to numpy {numpyBefore}:\n{e}"
    finally:
        constraints.unlink(missing_ok=True)
    importlib.invalidate_caches()
    if not slicerTensorFlowInstalled():
        return False, "pip finished but TensorFlow / tf-keras cannot be found in Slicer's Python."
    return True, f"Installed {' and '.join(SLICER_TF_REQUIREMENTS)} (numpy kept at {numpyBefore})."


def downloadModelsWithProgress(parent, models_dir, names):
    """Download the given model files into models_dir with a progress dialog. Returns (done, failed), lists of
    "name: message" strings; raises DownloadCancelled if the user cancels."""
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    progress = qt.QProgressDialog("", "Cancel", 0, 100, parent)
    progress.setWindowTitle("Downloading SynthSeg models")
    progress.setWindowModality(qt.Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.show()
    done, failed = [], []
    try:
        for i, name in enumerate(names, 1):
            def cb(source, got, total, name=name, i=i):
                progress.setLabelText(f"{name} ({i}/{len(names)}) from {source}\n"
                                      f"{got / 2**20:.1f}" + (f" / {total / 2**20:.1f}" if total else "") + " MB")
                if total:
                    progress.setValue(int(got * 100 / total))
                slicer.app.processEvents()
                return not progress.wasCanceled
            ok, msg = downloadModelFile(name, models_dir / name, cb)
            (done if ok else failed).append(f"{name}: {msg}")
    finally:
        progress.close()
    return done, failed


def blockedDownloadHelp():
    return ("If your network blocks these sites (common on university/hospital networks):\n"
            f"1. On another connection, download the .h5 files from\n   {MODEL_RELEASE_PAGE}\n"
            "2. In 'Configure Environment', click 'Import models from folder' and choose the folder with the files.")


def findModelFolders():
    """Folders that may already hold SynthSeg models: $FREESURFER_HOME/models and, on Windows, a FreeSurfer
    installed inside WSL (wsl.localhost/DISTRO/home/USER/freesurfer/models)."""
    import glob
    found = []
    fs = os.environ.get("FREESURFER_HOME")
    if fs:
        found.append(Path(fs) / "models")
    if os.name == "nt":
        for root in (r"\\wsl.localhost", r"\\wsl$"):
            try:
                found += [Path(p) for p in glob.glob(root + r"\*\home\*\freesurfer\models")]
            except Exception:
                pass
    return [p for p in found if p.is_dir() and any((p / f).exists() for f in ALL_MODEL_FILES)]


#
# SlicerSynthSeg
#

class SlicerSynthSeg(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class"""

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SynthSeg"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Prof. Dr. Niyazi Acer (Erciyes University)"]
        self.parent.helpText = """
Automated brain MRI segmentation using SynthSeg.
<br><br>
<b>First run:</b> select a volume and click 'Run Segmentation'. The extension offers to install TensorFlow
into Slicer's Python (about 600 MB, once) and downloads the SynthSeg models (about 50 MB each, checked with
SHA-256). No conda environment is needed.<br>
<br>
<b>Advanced:</b> 'Configure Environment' lets you use your own Python / conda environment instead, or import
the models from a folder (for networks that block the download).<br>
<br>
<b>Models:</b> by B. Billot, J.E. Iglesias et al., redistributed with their permission.
"""
        self.parent.acknowledgementText = """
Based on SynthSeg by Benjamin Billot et al. Please cite Billot et al., Medical Image Analysis 2023;
if you use SynthSeg 2.0 cortical parcellation, also cite Billot et al., PNAS 2023.<br>
Implementation: Prof. Dr. Niyazi Acer
"""


#
# SlicerSynthSegWidget
#

class SlicerSynthSegWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class"""

    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SlicerSynthSeg.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        uiWidget.setMRMLScene(slicer.mrmlScene)
        self.ui.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)

        self.logic = SlicerSynthSegLogic()

        self.ui.configureButton.connect('clicked(bool)', self.onConfigureButton)
        self.ui.testConfigButton.connect('clicked(bool)', self.onTestConfiguration)
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.ui.inputVolumeSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateApplyButtonState)

        # model selector (added in code so the .ui file stays unchanged)
        self.modelCombo = qt.QComboBox()
        for key, (label, _, _) in SYNTHSEG_MODES.items():
            self.modelCombo.addItem(label, key)
        saved = qt.QSettings().value("SlicerSynthSeg/mode", "v1")
        idx = self.modelCombo.findData(saved)
        self.modelCombo.setCurrentIndex(idx if idx >= 0 else 0)
        self.modelCombo.setToolTip("SynthSeg 2.0 + cortical parcellation gives the labels needed by "
                                   "SlicerCisternaVolumetry (extra-ventricular CSF, parahippocampal and "
                                   "entorhinal cortex).")
        self.modelCombo.connect('currentIndexChanged(int)', self.onModelChanged)
        self.ui.parametersCollapsibleButton.layout().insertRow(1, "Model:", self.modelCombo)

        self.updateConfigurationStatus()

    def cleanup(self):
        pass

    def enter(self):
        self.updateApplyButtonState()

    def exit(self):
        pass

    def currentMode(self):
        return self.modelCombo.itemData(self.modelCombo.currentIndex) or "v1"

    def onModelChanged(self, index):
        qt.QSettings().setValue("SlicerSynthSeg/mode", self.currentMode())

    def updateApplyButtonState(self, node=None):
        self.ui.applyButton.enabled = bool(self.ui.inputVolumeSelector.currentNode()) and self.logic.isConfigured()

    def updateConfigurationStatus(self):
        if self.logic.isConfigured():
            config = self.logic.getConfiguration()
            python = ("Slicer's own Python" + ("" if slicerTensorFlowInstalled() else " (TensorFlow is installed on first run)")
                      if config['engine'] == "slicer" else config.get('python_path', 'N/A'))
            self.ui.configStatusLabel.text = f"✓ Configured\nSynthSeg: {config.get('synthseg_path', 'N/A')}\nPython: {python}"
            self.ui.configStatusLabel.styleSheet = "color: green;"
        else:
            self.ui.configStatusLabel.text = "⚠ Not configured\nClick 'Configure Environment' to set paths"
            self.ui.configStatusLabel.styleSheet = "color: red;"
        self.updateApplyButtonState()

    def onConfigureButton(self):
        dialog = ConfigurationDialog(self.logic)
        if dialog.exec_():
            self.updateConfigurationStatus()
            slicer.util.infoDisplay("Configuration saved successfully!")

    def onTestConfiguration(self):
        if not self.logic.isConfigured():
            slicer.util.errorDisplay("Please configure environment first!")
            return

        result, message = self.logic.testConfiguration()
        if result:
            slicer.util.infoDisplay(f"✓ Configuration valid!\n\n{message}")
        else:
            slicer.util.errorDisplay(f"✗ Configuration error:\n\n{message}")

    def onApplyButton(self):
        try:
            inputVolume = self.ui.inputVolumeSelector.currentNode()
            if not inputVolume:
                raise ValueError("Please select an input volume")

            if not self.logic.isConfigured():
                raise ValueError("Please configure environment first!\nClick 'Configure Environment' button.")

            if self.logic.needsTensorFlowInstall():
                if not slicer.util.confirmOkCancelDisplay(
                        "SynthSeg needs TensorFlow, which is not installed in Slicer's Python yet.\n\n"
                        f"Install {' and '.join(SLICER_TF_REQUIREMENTS)} now? This downloads about 600 MB and "
                        "takes a few minutes; it is done only once. numpy is kept at its current version so "
                        "other extensions are not affected.",
                        windowTitle="Install TensorFlow"):
                    return
                with slicer.util.WaitCursor():
                    ok, msg = installSlicerTensorFlow()
                if not ok:
                    raise RuntimeError(msg)
                self.updateConfigurationStatus()
                slicer.util.infoDisplay(msg + "\n\nSegmentation will start now.")

            models_dir, missing = self.logic.missingModels(self.currentMode())
            if missing:
                if not slicer.util.confirmOkCancelDisplay(
                        f"{SYNTHSEG_MODES[self.currentMode()][0]} needs these model files, which are not downloaded yet:\n  "
                        + "\n  ".join(missing) + "\n\nDownload them now (about 50 MB each, checked with SHA-256)?\n\n"
                        "The models are by B. Billot, J.E. Iglesias et al. and are redistributed with their permission.",
                        windowTitle="Download SynthSeg models"):
                    return
                try:
                    done, failed = downloadModelsWithProgress(slicer.util.mainWindow(), models_dir, missing)
                except DownloadCancelled:
                    return
                if failed:
                    raise RuntimeError("Could not download:\n  " + "\n  ".join(failed) + "\n\n" + blockedDownloadHelp())

            self.ui.applyButton.enabled = False
            self.ui.applyButton.text = "Processing..."
            slicer.app.processEvents()

            segmentationNode, tableNode = self.logic.process(inputVolume, self.currentMode())

            self.ui.volumeTableView.setMRMLTableNode(tableNode)
            self.ui.resultsCollapsibleButton.collapsed = False

            slicer.util.infoDisplay("Segmentation completed successfully!")

        except Exception as e:
            slicer.util.errorDisplay(f"Failed to compute results: {str(e)}\n\nPlease check:\n1. Configuration is correct\n2. Input image is valid\n3. SynthSeg models are installed")
            import traceback
            traceback.print_exc()
        finally:
            self.ui.applyButton.enabled = True
            self.ui.applyButton.text = "Run Segmentation"
            self.updateApplyButtonState()


#
# Configuration Dialog
#

class ConfigurationDialog(qt.QDialog):
    """Configuration dialog for SynthSeg paths"""

    def __init__(self, logic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.setWindowTitle("Configure SynthSeg Environment")
        self.setMinimumWidth(600)
        self.setup()
        self.loadCurrentConfig()

    def setup(self):
        layout = qt.QFormLayout(self)

        instructions = qt.QLabel(
            "<b>Setup Instructions:</b><br>"
            "1. Default: SynthSeg runs in Slicer's own Python. TensorFlow is installed on the first run; "
            "nothing else to set up.<br>"
            "2. Advanced: choose 'Custom Python / conda environment' and give a Python that has TensorFlow, "
            "Keras and nibabel (for example an existing conda environment)<br>"
            "3. Models: click 'Download models automatically' below (SynthSeg 1.0, 2.0 and cortical "
            "parcellation, about 50 MB each, checked with SHA-256).<br>"
            "&nbsp;&nbsp;&nbsp;If the download is blocked on your network, download the .h5 files from "
            f"<a href='{MODEL_RELEASE_PAGE}'>this page</a> on another connection, or use your FreeSurfer "
            "<i>models</i> folder, then click 'Import models from folder'<br>"
            "4. The models are by B. Billot, J.E. Iglesias et al. and are redistributed with their "
            "permission; please cite SynthSeg (see Help)<br>"
            "5. Specify paths below"
        )
        instructions.setOpenExternalLinks(True)
        instructions.setWordWrap(True)
        layout.addRow(instructions)

        downloadModelButton = qt.QPushButton("📥 Download models automatically (SynthSeg 1.0 / 2.0 / parcellation)")
        downloadModelButton.clicked.connect(self.onDownloadModel)
        layout.addRow(downloadModelButton)

        importModelsButton = qt.QPushButton("📂 Import models from folder (offline / FreeSurfer)")
        importModelsButton.clicked.connect(self.onImportModels)
        layout.addRow(importModelsButton)

        self.engineCombo = qt.QComboBox()
        for key, label in ENGINE_LABELS.items():
            self.engineCombo.addItem(label, key)
        self.engineCombo.connect('currentIndexChanged(int)', self.onEngineChanged)
        layout.addRow("Run SynthSeg with:", self.engineCombo)

        synthsegLayout = qt.QHBoxLayout()
        self.synthsegPathEdit = qt.QLineEdit()
        self.synthsegPathEdit.setPlaceholderText("C:/path/to/SynthSeg")
        synthsegBrowseButton = qt.QPushButton("Browse...")
        synthsegBrowseButton.clicked.connect(self.onBrowseSynthSeg)
        synthsegLayout.addWidget(self.synthsegPathEdit)
        synthsegLayout.addWidget(synthsegBrowseButton)
        layout.addRow("SynthSeg Path:", synthsegLayout)

        pythonLayout = qt.QHBoxLayout()
        self.pythonPathEdit = qt.QLineEdit()
        self.pythonPathEdit.setPlaceholderText("C:/anaconda3/envs/synthseg_py38/python.exe")
        pythonBrowseButton = qt.QPushButton("Browse...")
        pythonBrowseButton.clicked.connect(self.onBrowsePython)
        pythonLayout.addWidget(self.pythonPathEdit)
        pythonLayout.addWidget(pythonBrowseButton)
        self.pythonBrowseButton = pythonBrowseButton
        layout.addRow("Python Executable:", pythonLayout)

        buttonLayout = qt.QHBoxLayout()
        saveButton = qt.QPushButton("Save")
        saveButton.clicked.connect(self.onSave)
        cancelButton = qt.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(saveButton)
        buttonLayout.addWidget(cancelButton)
        layout.addRow(buttonLayout)

    def loadCurrentConfig(self):
        config = self.logic.getConfiguration()
        self.synthsegPathEdit.setText(config.get('synthseg_path', ''))
        self.pythonPathEdit.setText(config.get('python_path', ''))
        idx = self.engineCombo.findData(config.get('engine', 'slicer'))
        self.engineCombo.setCurrentIndex(idx if idx >= 0 else 0)
        self.onEngineChanged()

    def currentEngine(self):
        return self.engineCombo.itemData(self.engineCombo.currentIndex)

    def onEngineChanged(self, index=None):
        custom = self.currentEngine() == "custom"
        self.pythonPathEdit.enabled = custom
        self.pythonBrowseButton.enabled = custom
        self.pythonPathEdit.setPlaceholderText("C:/anaconda3/envs/synthseg/python.exe" if custom
                                               else "not needed: Slicer's own Python is used")

    def _ensurePackageInstalled(self, moduleName):
        """Import moduleName in Slicer's own Python, installing it via
        slicer.util.pip_install if it isn't available yet."""
        try:
            return __import__(moduleName)
        except ImportError:
            slicer.util.pip_install(moduleName)
            return __import__(moduleName)

    def _validateDownloadedModel(self, model_file):
        """Guard against Google Drive serving its HTML warning/quota page
        instead of the real .h5 file (this happened today with synthseg_2.0.h5)."""
        if not model_file.exists():
            return False, "Downloaded file does not exist."

        size_mb = model_file.stat().st_size / (1024 * 1024)
        if size_mb < 10:
            return False, (
                f"Downloaded file is only {size_mb:.2f} MB. This is almost certainly "
                f"Google Drive's HTML warning page, not the real ~50 MB model file."
            )

        try:
            h5py = self._ensurePackageInstalled("h5py")
            with h5py.File(str(model_file), 'r'):
                pass
        except Exception as e:
            return False, f"Downloaded file could not be opened as a valid HDF5 model: {str(e)}"

        return True, "Model file verified."

    def onDownloadModel(self):
        synthseg_path = self.synthsegPathEdit.text.strip()
        if not synthseg_path:
            qt.QMessageBox.warning(self, "SynthSeg Path Required", "Please specify SynthSeg path first!")
            return

        models_dir = Path(synthseg_path) / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        # A file already present is kept: it may be a valid copy imported from FreeSurfer.
        wanted = [n for n in ALL_MODEL_FILES
                  if not ((models_dir / n).exists() and (models_dir / n).stat().st_size > 10 * 2**20)]
        if not wanted:
            if qt.QMessageBox.question(self, "Models present",
                                       f"All model files are already in:\n{models_dir}\n\nDownload them again?",
                                       qt.QMessageBox.Yes | qt.QMessageBox.No) == qt.QMessageBox.No:
                return
            wanted = list(ALL_MODEL_FILES)

        try:
            done, failed = downloadModelsWithProgress(self, models_dir, wanted)
        except DownloadCancelled:
            qt.QMessageBox.information(self, "Download cancelled", "Download cancelled. Nothing was saved for the current file.")
            return

        text = ""
        if done:
            text += "Downloaded and verified (SHA-256):\n  " + "\n  ".join(done) + "\n\n"
        if failed:
            text += "Could not download:\n  " + "\n  ".join(failed) + "\n\n" + blockedDownloadHelp()
            qt.QMessageBox.warning(self, "Model download", text.strip())
        else:
            qt.QMessageBox.information(self, "Model download", text.strip() + f"\n\nSaved to:\n{models_dir}")

    def onImportModels(self):
        """Copy SynthSeg model files from a folder (FreeSurfer models, or the user's download folder) into
        SynthSeg/models, where SynthSeg_predict.py looks for them."""
        import shutil
        synthseg_path = self.synthsegPathEdit.text.strip()
        if not synthseg_path:
            qt.QMessageBox.warning(self, "SynthSeg Path Required", "Please specify SynthSeg path first!")
            return
        candidates = findModelFolders()
        start = str(candidates[0]) if candidates else ""
        if candidates:
            msg = "Found SynthSeg models here:\n" + "\n".join(str(c) for c in candidates) + "\n\nUse the first one?"
            if qt.QMessageBox.question(self, "Models found", msg, qt.QMessageBox.Yes | qt.QMessageBox.No) == qt.QMessageBox.Yes:
                folder = start
            else:
                folder = qt.QFileDialog.getExistingDirectory(self, "Select folder with SynthSeg models", start)
        else:
            folder = qt.QFileDialog.getExistingDirectory(self, "Select folder with SynthSeg models (.h5)")
        if not folder:
            return
        models_dir = Path(synthseg_path) / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        copied, missing = [], []
        for name in ALL_MODEL_FILES:
            src = Path(folder) / name
            if not src.exists():
                missing.append(name)
                continue
            dst = models_dir / name
            if dst.exists() and dst.stat().st_size == src.stat().st_size:
                copied.append(name + " (already present)")
                continue
            ok, why = self._validateDownloadedModel(src)
            if not ok:
                missing.append(f"{name} (invalid: {why})")
                continue
            shutil.copy2(str(src), str(dst))
            copied.append(name)
        text = "Copied to " + str(models_dir) + ":\n  " + ("\n  ".join(copied) if copied else "nothing")
        if missing:
            text += "\n\nNot found in the selected folder:\n  " + "\n  ".join(missing)
        qt.QMessageBox.information(self, "Import models", text)

    def onBrowseSynthSeg(self):
        path = qt.QFileDialog.getExistingDirectory(self, "Select SynthSeg Directory")
        if path:
            self.synthsegPathEdit.setText(path)

    def onBrowsePython(self):
        path = qt.QFileDialog.getOpenFileName(self, "Select Python Executable", "", "Python (python.exe python)")
        if path:
            self.pythonPathEdit.setText(path)

    def onSave(self):
        synthseg_path = self.synthsegPathEdit.text.strip()
        python_path = self.pythonPathEdit.text.strip()
        engine = self.currentEngine()

        if not synthseg_path or (engine == "custom" and not python_path):
            qt.QMessageBox.warning(self, "Missing Information",
                                   "Please provide the SynthSeg path" + (" and the Python executable!" if engine == "custom" else "!"))
            return

        result, message = self.logic.validateAndSaveConfiguration(synthseg_path, python_path, engine)
        if result:
            self.accept()
        else:
            qt.QMessageBox.critical(self, "Validation Error", f"Configuration invalid:\n\n{message}")


#
# SlicerSynthSegLogic
#

class SlicerSynthSegLogic(ScriptedLoadableModuleLogic):
    """
    Segmentation logic. Calls the conda-env python.exe directly (no conda
    activate), matching the invocation method proven to work reliably on Windows.
    """

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.config = None
        self.loadConfiguration()

    def loadConfiguration(self):
        """Load configuration from SlicerSynthSegLib/synthseg_config.py"""
        try:
            from SlicerSynthSegLib.synthseg_config import SynthSegConfig
            self.config = SynthSegConfig()
        except Exception as e:
            logging.error(f"Failed to load SynthSegConfig: {e}")
            self.config = None

    def getConfiguration(self):
        """Saved configuration; with nothing saved yet, the default: Slicer's Python + the bundled SynthSeg."""
        config = dict(self.config.get_config()) if self.config else {}
        # A configuration saved before engines existed has a python_path and no engine: it keeps using that
        # external Python. Decided here (not only in synthseg_config) so an existing conda setup is never
        # switched to Slicer's Python, whichever version of the helper module is loaded.
        if config.get('engine') not in ENGINE_LABELS:
            config['engine'] = "custom" if config.get('python_path') else "slicer"
        if not config.get('synthseg_path'):
            bundled = bundledSynthSegPath()
            if bundled:
                config['synthseg_path'] = str(bundled)
        config.setdefault('python_path', '')
        return config

    def isConfigured(self):
        config = self.getConfiguration()
        if not config.get('synthseg_path') or not os.path.exists(config['synthseg_path']):
            return False
        if config['engine'] == "custom":
            return bool(config.get('python_path')) and os.path.exists(config['python_path'])
        return True

    def missingModels(self, mode):
        """Model files the given mode needs that are not in SynthSeg/models yet: (models_dir, [names])."""
        models_dir = Path(self.getConfiguration()['synthseg_path']) / "models"
        return models_dir, [m for m in SYNTHSEG_MODES[mode][2] if not (models_dir / m).exists()]

    def needsTensorFlowInstall(self):
        return self.getConfiguration()['engine'] == "slicer" and not slicerTensorFlowInstalled()

    def validateAndSaveConfiguration(self, synthseg_path, python_path, engine="slicer"):
        if self.config is None:
            try:
                from SlicerSynthSegLib.synthseg_config import SynthSegConfig
                self.config = SynthSegConfig()
            except Exception as e:
                return False, f"Failed to load SynthSegConfig: {str(e)}"

        valid, msg = self.config.validate_synthseg_path(synthseg_path)
        if not valid:
            return False, f"SynthSeg path invalid: {msg}"

        self.config.save_config(synthseg_path, python_path, engine)

        return True, "Configuration saved"

    def testConfiguration(self):
        if not self.isConfigured():
            return False, "Not configured"

        config = self.getConfiguration()

        valid, msg = self.config.validate_synthseg_path(config['synthseg_path'])
        if not valid:
            return False, f"SynthSeg: {msg}"

        if config['engine'] == "slicer":
            if not pythonSlicerPath():
                return False, "Python: PythonSlicer executable not found in this Slicer installation"
            tf = ("TensorFlow installed in Slicer's Python" if slicerTensorFlowInstalled()
                  else "TensorFlow not installed yet: it is installed on the first run (about 600 MB)")
            return True, f"SynthSeg: {msg}\nPython: Slicer's own Python\n{tf}"

        valid, msg2 = self.config.validate_python_env(config['python_path'])
        if not valid:
            return False, f"Python: {msg2}"

        return True, f"SynthSeg: {msg}\nPython: {config['python_path']}"

    def _resolveAndValidatePaths(self, mode="v1"):
        """Re-validate python.exe / SynthSeg_predict.py / model right before running,
        in case the on-disk state changed since the config was saved."""
        config = self.getConfiguration()

        if config['engine'] == "slicer":
            python_slicer = pythonSlicerPath()
            if not python_slicer:
                raise RuntimeError("PythonSlicer executable not found in this Slicer installation.")
            if not slicerTensorFlowInstalled():
                raise RuntimeError("TensorFlow is not installed in Slicer's Python yet. Click 'Run Segmentation' "
                                   "again and accept the installation, or choose a custom Python in 'Configure Environment'.")
            python_cmd = [python_slicer, str(MODULE_DIR / "SlicerSynthSegLib" / "run_synthseg_tfkeras.py")]
        else:
            python_path = Path(config['python_path'])
            if not python_path.exists():
                raise RuntimeError(f"Python executable not found: {python_path}")
            # The same launcher maps keras -> tf_keras when the environment has TensorFlow 2.16+
            # and leaves older environments (e.g. TF 2.4) unchanged.
            python_cmd = [str(python_path), str(MODULE_DIR / "SlicerSynthSegLib" / "run_synthseg_tfkeras.py")]

        synthseg_path = Path(config['synthseg_path'])
        predict_script = synthseg_path / "scripts" / "commands" / "SynthSeg_predict.py"
        if not predict_script.exists():
            raise RuntimeError(
                f"SynthSeg installation invalid: scripts/commands/SynthSeg_predict.py "
                f"not found under {synthseg_path}"
            )

        label, _, needed = SYNTHSEG_MODES[mode]
        missing = [m for m in needed if not (synthseg_path / "models" / m).exists()]
        if missing:
            raise RuntimeError(
                f"{label} needs these model files in {synthseg_path / 'models'}:\n  " + "\n  ".join(missing) +
                "\n\nOpen 'Configure Environment' and use 'Import models from folder' (FreeSurfer models folder, "
                "or the files downloaded from the official SynthSeg link)."
            )

        return python_cmd, config['engine'], predict_script

    def _labelNames(self, mode):
        """Label names for the chosen model: the fixed v1 table, or the names shipped with SynthSeg
        (segmentation 2.0 + parcellation) read from SynthSeg/data/labels_classes_priors."""
        if mode == "v1":
            return SYNTHSEG_V1_LABELS
        import numpy as np
        d = Path(self.getConfiguration()['synthseg_path']) / "data" / "labels_classes_priors"
        names = {}
        try:
            for lab_f, name_f in (("synthseg_segmentation_labels_2.0.npy", "synthseg_segmentation_names_2.0.npy"),
                                  ("synthseg_parcellation_labels.npy", "synthseg_parcellation_names.npy")):
                for l, n in zip(np.load(str(d / lab_f)).tolist(), np.load(str(d / name_f)).tolist()):
                    if l > 0 and l not in names:
                        names[int(l)] = str(n)
        except Exception as e:
            logging.warning(f"Could not read SynthSeg label names ({e}); using v1 names")
            names = dict(SYNTHSEG_V1_LABELS)
        names.setdefault(24, "CSF")
        return names

    def _buildColorTableNode(self, labelNames):
        """Build a small color table so segments get real anatomical names on import."""
        colorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode")
        colorNode.SetName("SynthSegColors")
        colorNode.SetTypeToUser()
        maxLabel = max(labelNames.keys())
        colorNode.SetNumberOfColors(maxLabel + 1)
        colorNode.SetColor(0, "Background", 0.0, 0.0, 0.0, 0.0)
        for labelValue in range(1, maxLabel + 1):
            name = labelNames.get(labelValue)
            if name is None:
                colorNode.SetColor(labelValue, f"Label-{labelValue}", 0.5, 0.5, 0.5, 0.0)
                continue
            hue = (labelValue * 0.61803398875) % 1.0
            r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.95)
            colorNode.SetColor(labelValue, name, r, g, b, 1.0)
        return colorNode

    def _annotateVolumeCsv(self, csvPath, subjectName, mode):
        """Put the volume name in the subject column (SynthSeg writes the temporary file name) and add the
        model used and the SynthSeg citation to every row, so they survive when tables are merged."""
        with open(csvPath, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if not rows:
            return
        rows[0] += ["synthseg_model", "citation"]
        for row in rows[1:]:
            if row:
                row[0] = subjectName
                row += [SYNTHSEG_MODES[mode][0], SYNTHSEG_CITATIONS[mode]]
        with open(csvPath, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

    def process(self, inputVolume, mode="v1"):
        """
        Run SynthSeg on inputVolume by calling the conda env's python.exe directly
        (no conda activate) and load the results back into the scene.
        Returns (segmentationNode, tableNode).
        """
        if not self.isConfigured():
            raise RuntimeError("SynthSeg environment is not configured. Click 'Configure Environment' first.")

        startTime = time.time()
        logging.info('SynthSeg processing started')

        if mode not in SYNTHSEG_MODES:
            mode = "v1"
        python_cmd, engine, predict_script = self._resolveAndValidatePaths(mode)

        with tempfile.TemporaryDirectory() as tmpDir:
            tmpPath = Path(tmpDir)

            inputPath = tmpPath / 'input.nii.gz'
            slicer.util.saveNode(inputVolume, str(inputPath))

            segPath = tmpPath / 'segmentation.nii.gz'
            volCsvPath = tmpPath / 'volumes.csv'

            cmd = python_cmd + [
                str(predict_script),
                "--i", str(inputPath),
                "--o", str(segPath),
                "--vol", str(volCsvPath),
                "--cpu",
                "--threads", SYNTHSEG_THREADS,
            ] + SYNTHSEG_MODES[mode][1]

            if engine == "slicer":
                # PythonSlicer needs Slicer's own startup environment (its Python paths)
                env = dict(slicer.util.startupEnvironment())
                env["TF_USE_LEGACY_KERAS"] = "1"
            else:
                env = os.environ.copy()
                # Slicer's embedded Python sets these to point at its own stdlib;
                # left in place, the conda python.exe tries to load Slicer's io.py
                # instead of its own and crashes at interpreter startup.
                for var in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP"):
                    env.pop(var, None)
            env["KMP_DUPLICATE_LIB_OK"] = "TRUE"

            logging.info("Running: %s", " ".join(cmd))

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=env,
            )

            pollStart = time.time()
            while proc.poll() is None:
                if time.time() - pollStart > SYNTHSEG_TIMEOUT_SECONDS:
                    proc.kill()
                    proc.communicate()
                    raise RuntimeError(
                        f"SynthSeg process did not finish within "
                        f"{SYNTHSEG_TIMEOUT_SECONDS // 60} minutes and was terminated. "
                        f"The process may be stuck, or the machine is too slow for CPU inference."
                    )
                slicer.app.processEvents()
                time.sleep(0.2)

            stdout, stderr = proc.communicate()

            if proc.returncode != 0:
                tail = "\n".join((stdout + stderr).strip().splitlines()[-25:])
                raise RuntimeError(
                    f"SynthSeg processing failed with exit code {proc.returncode}\n\n{tail}"
                )

            if not segPath.exists():
                raise RuntimeError("SynthSeg did not produce a segmentation output file.")
            if not volCsvPath.exists():
                raise RuntimeError("SynthSeg did not produce a volumes CSV output file.")

            labelmapVolumeNode = slicer.util.loadLabelVolume(str(segPath))
            colorNode = self._buildColorTableNode(self._labelNames(mode))
            labelmapVolumeNode.GetDisplayNode().SetAndObserveColorNodeID(colorNode.GetID())

            segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
            segmentationNode.SetName(f"{inputVolume.GetName()}_synthseg_{mode}")
            segmentationNode.CreateDefaultDisplayNodes()
            slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
                labelmapVolumeNode, segmentationNode
            )

            slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
            slicer.mrmlScene.RemoveNode(colorNode)

            self._annotateVolumeCsv(volCsvPath, inputVolume.GetName(), mode)
            tableNode = slicer.util.loadTable(str(volCsvPath))
            tableNode.SetName(f"{inputVolume.GetName()}_volumes")

        stopTime = time.time()
        logging.info(f'SynthSeg processing completed in {stopTime - startTime:.2f} seconds')

        return segmentationNode, tableNode


#
# SlicerSynthSegTest
#

class SlicerSynthSegTest(ScriptedLoadableModuleTest):
    """
    Test cases for SlicerSynthSeg.
    """

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_SlicerSynthSeg1()

    def test_SlicerSynthSeg1(self):
        self.delayDisplay("Starting the test")
        self.delayDisplay('Test passed')
