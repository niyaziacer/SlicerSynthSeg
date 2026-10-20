import os
import time
import logging
import subprocess
import tempfile
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

# Model choices: (label shown in the panel, CLI flags, model files needed in SynthSeg/models)
SYNTHSEG_MODES = {
    "v1": ("SynthSeg 1.0", ["--v1"], ["synthseg_1.0.h5"]),
    "v2": ("SynthSeg 2.0", [], ["synthseg_2.0.h5"]),
    "v2parc": ("SynthSeg 2.0 + cortical parcellation", ["--parc"], ["synthseg_2.0.h5", "synthseg_parc_2.0.h5"]),
}
ALL_MODEL_FILES = ["synthseg_1.0.h5", "synthseg_2.0.h5", "synthseg_parc_2.0.h5"]


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
<b>Requirements:</b><br>
1. SynthSeg installation (download from GitHub)<br>
2. Python environment with TensorFlow, Keras, nibabel<br>
<br>
<b>First-time setup:</b><br>
Click 'Configure Environment' to set paths.<br>
<br>
<b>Models:</b> SynthSeg 1.0 can be downloaded from the configuration dialog. SynthSeg 2.0 and the cortical
parcellation need synthseg_2.0.h5 and synthseg_parc_2.0.h5: use 'Import models from folder' in the
configuration dialog and point it to your FreeSurfer models folder, or to the folder where you saved the
files from the official SynthSeg download link.
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
            self.ui.configStatusLabel.text = f"✓ Configured\nSynthSeg: {config.get('synthseg_path', 'N/A')}\nPython: {config.get('python_path', 'N/A')}"
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
            "1. Download SynthSeg from: <a href='https://github.com/BBillot/SynthSeg'>GitHub</a><br>"
            "2. Create a conda environment with TensorFlow, Keras, nibabel<br>"
            "3. Model: click 'Download Model Automatically' below, OR download "
            f"<a href='{SYNTHSEG_V1_MODEL_DRIVE_VIEW_URL}'>synthseg_1.0.h5</a> manually "
            "and place it in SynthSeg/models/<br>"
            "4. For SynthSeg 2.0 / cortical parcellation: click 'Import models from folder' and choose your "
            "FreeSurfer <i>models</i> folder, or the folder where you saved synthseg_2.0.h5 and "
            f"synthseg_parc_2.0.h5 from the <a href='{SYNTHSEG_OFFICIAL_MODELS_URL}'>official SynthSeg download</a><br>"
            "5. Specify paths below"
        )
        instructions.setOpenExternalLinks(True)
        instructions.setWordWrap(True)
        layout.addRow(instructions)

        downloadModelButton = qt.QPushButton("📥 Download Model Automatically (SynthSeg 1.0)")
        downloadModelButton.clicked.connect(self.onDownloadModel)
        layout.addRow(downloadModelButton)

        importModelsButton = qt.QPushButton("📂 Import models from folder (SynthSeg 2.0 / parcellation)")
        importModelsButton.clicked.connect(self.onImportModels)
        layout.addRow(importModelsButton)

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
            qt.QMessageBox.warning(self, "SynthSeg Path Required",
                                 "Please specify SynthSeg path first!")
            return

        models_dir = Path(synthseg_path) / "models"
        model_file = models_dir / "synthseg_1.0.h5"

        if model_file.exists():
            reply = qt.QMessageBox.question(self, "Model Exists",
                                          f"Model already exists at:\n{model_file}\n\nDownload again?",
                                          qt.QMessageBox.Yes | qt.QMessageBox.No)
            if reply == qt.QMessageBox.No:
                return

        models_dir.mkdir(parents=True, exist_ok=True)

        try:
            gdown = self._ensurePackageInstalled("gdown")
        except Exception as e:
            qt.QMessageBox.critical(self, "gdown Not Available",
                                  f"Could not install/import gdown:\n{str(e)}\n\n"
                                  f"Please download the model manually from:\n{SYNTHSEG_V1_MODEL_DRIVE_VIEW_URL}\n"
                                  f"and place it at:\n{model_file}")
            return

        progress = qt.QProgressDialog("Downloading model (~50 MB) with gdown...", "Cancel", 0, 0, self)
        progress.setWindowModality(qt.Qt.WindowModal)
        progress.show()
        slicer.app.processEvents()

        try:
            url = f"https://drive.google.com/uc?id={SYNTHSEG_V1_MODEL_DRIVE_ID}"
            gdown.download(url, str(model_file), quiet=False, fuzzy=True)
        except Exception as e:
            progress.close()
            if model_file.exists():
                model_file.unlink()
            qt.QMessageBox.critical(self, "Download Failed",
                                  f"gdown download failed:\n{str(e)}\n\n"
                                  f"Please download manually from:\n{SYNTHSEG_V1_MODEL_DRIVE_VIEW_URL}\n"
                                  f"and save it to:\n{model_file}")
            return
        finally:
            progress.close()

        valid, msg = self._validateDownloadedModel(model_file)
        if not valid:
            if model_file.exists():
                model_file.unlink()
            qt.QMessageBox.critical(self, "Download Verification Failed",
                                  f"{msg}\n\n"
                                  f"Please download the model manually from:\n{SYNTHSEG_V1_MODEL_DRIVE_VIEW_URL}\n"
                                  f"and save it to:\n{model_file}")
            return

        qt.QMessageBox.information(self, "Success",
                                 f"Model downloaded and verified successfully!\n\nSaved to:\n{model_file}")

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

        if not synthseg_path or not python_path:
            qt.QMessageBox.warning(self, "Missing Information", "Please provide both paths!")
            return

        result, message = self.logic.validateAndSaveConfiguration(synthseg_path, python_path)
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
        """Load configuration from SynthSegConfig (same directory as this module)"""
        try:
            from SynthSegConfig import SynthSegConfig
            self.config = SynthSegConfig()
        except Exception as e:
            logging.error(f"Failed to load SynthSegConfig: {e}")
            self.config = None

    def isConfigured(self):
        if self.config is None:
            return False
        return self.config.is_configured()

    def getConfiguration(self):
        if self.config:
            return self.config.get_config()
        return {}

    def validateAndSaveConfiguration(self, synthseg_path, python_path):
        if self.config is None:
            try:
                from SynthSegConfig import SynthSegConfig
                self.config = SynthSegConfig()
            except Exception as e:
                return False, f"Failed to load SynthSegConfig: {str(e)}"

        valid, msg = self.config.validate_synthseg_path(synthseg_path)
        if not valid:
            return False, f"SynthSeg path invalid: {msg}"

        self.config.save_config(synthseg_path, python_path)

        return True, "Configuration saved"

    def testConfiguration(self):
        if not self.isConfigured():
            return False, "Not configured"

        config = self.getConfiguration()

        valid, msg = self.config.validate_synthseg_path(config['synthseg_path'])
        if not valid:
            return False, f"SynthSeg: {msg}"

        valid, msg = self.config.validate_python_env(config['python_path'])
        if not valid:
            return False, f"Python: {msg}"

        return True, "All checks passed!"

    def _resolveAndValidatePaths(self, mode="v1"):
        """Re-validate python.exe / SynthSeg_predict.py / model right before running,
        in case the on-disk state changed since the config was saved."""
        config = self.getConfiguration()

        python_path = Path(config['python_path'])
        if not python_path.exists():
            raise RuntimeError(f"Python executable not found: {python_path}")

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

        return python_path, predict_script

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
        python_path, predict_script = self._resolveAndValidatePaths(mode)

        with tempfile.TemporaryDirectory() as tmpDir:
            tmpPath = Path(tmpDir)

            inputPath = tmpPath / 'input.nii.gz'
            slicer.util.saveNode(inputVolume, str(inputPath))

            segPath = tmpPath / 'segmentation.nii.gz'
            volCsvPath = tmpPath / 'volumes.csv'

            cmd = [
                str(python_path), str(predict_script),
                "--i", str(inputPath),
                "--o", str(segPath),
                "--vol", str(volCsvPath),
                "--cpu",
                "--threads", SYNTHSEG_THREADS,
            ] + SYNTHSEG_MODES[mode][1]

            env = os.environ.copy()
            env["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            # Slicer's embedded Python sets these to point at its own stdlib;
            # left in place, the conda python.exe tries to load Slicer's io.py
            # instead of its own and crashes at interpreter startup.
            for var in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP"):
                env.pop(var, None)

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
