import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import subprocess
import tempfile
from pathlib import Path

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
Click 'Configure Environment' to set paths.
"""
        self.parent.acknowledgementText = """
Based on SynthSeg by Benjamin Billot et al.<br>
Implementation: Prof. Dr. Niyazi Acer
"""

#
# SlicerSynthSegWidget
#

class SlicerSynthSegWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class"""

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Designer)
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/SlicerSynthSeg.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class
        self.logic = SlicerSynthSegLogic()

        # Connections
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.configureButton.connect('clicked(bool)', self.onConfigureButton)
        self.ui.testConfigButton.connect('clicked(bool)', self.onTestConfiguration)
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

        # Make sure parameter node is initialized
        self.initializeParameterNode()
        
        # Check if configured
        self.updateConfigurationStatus()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self):
        """
        Called each time the user opens this module.
        """
        self.initializeParameterNode()

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        pass

    def onSceneStartClose(self, caller, event):
        """
        Called when the scene is about to be closed.
        """
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event):
        """
        Called when the scene is closed.
        """
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self):
        """
        Ensure parameter node exists and observed.
        """
        self.setParameterNode(self.logic.getParameterNode())

    def setParameterNode(self, inputParameterNode):
        """
        Set and observe parameter node.
        """
        if inputParameterNode:
            self.logic.setDefaultParameters(inputParameterNode)

        if self._parameterNode is not None:
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
        self._parameterNode = inputParameterNode
        if self._parameterNode is not None:
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

        self.updateGUIFromParameterNode()

    def updateGUIFromParameterNode(self, caller=None, event=None):
        """
        Update GUI from parameter node.
        """
        if self._parameterNode is None or self._updatingGUIFromParameterNode:
            return

        self._updatingGUIFromParameterNode = True

        # Update buttons state
        if self.ui.inputVolumeSelector.currentNode() and self.logic.isConfigured():
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.enabled = False

        self._updatingGUIFromParameterNode = False

    def updateConfigurationStatus(self):
        """
        Update configuration status display.
        """
        if self.logic.isConfigured():
            config = self.logic.getConfiguration()
            self.ui.configStatusLabel.text = f"✓ Configured\nSynthSeg: {config.get('synthseg_path', 'N/A')}\nPython: {config.get('python_path', 'N/A')}"
            self.ui.configStatusLabel.styleSheet = "color: green;"
        else:
            self.ui.configStatusLabel.text = "⚠ Not configured\nClick 'Configure Environment' to set paths"
            self.ui.configStatusLabel.styleSheet = "color: red;"

    def onConfigureButton(self):
        """
        Show configuration dialog.
        """
        dialog = ConfigurationDialog(self.logic)
        if dialog.exec_():
            self.updateConfigurationStatus()
            slicer.util.infoDisplay("Configuration saved successfully!")

    def onTestConfiguration(self):
        """
        Test current configuration.
        """
        if not self.logic.isConfigured():
            slicer.util.errorDisplay("Please configure environment first!")
            return

        result, message = self.logic.testConfiguration()
        if result:
            slicer.util.infoDisplay(f"✓ Configuration valid!\n\n{message}")
        else:
            slicer.util.errorDisplay(f"✗ Configuration error:\n\n{message}")

    def onApplyButton(self):
        """
        Run processing when user clicks "Apply" button.
        """
        try:
            # Get input volume
            inputVolume = self.ui.inputVolumeSelector.currentNode()
            if not inputVolume:
                raise ValueError("Please select an input volume")

            # Check configuration
            if not self.logic.isConfigured():
                raise ValueError("Please configure environment first!\nClick 'Configure Environment' button.")

            # Disable button during processing
            self.ui.applyButton.enabled = False
            self.ui.applyButton.text = "Processing..."
            slicer.app.processEvents()

            # Run segmentation
            outputSegmentation = self.logic.process(inputVolume)

            # Success message
            slicer.util.infoDisplay("Segmentation completed successfully!")

        except Exception as e:
            slicer.util.errorDisplay(f"Failed to compute results: {str(e)}\n\nPlease check:\n1. Configuration is correct\n2. Input image is valid\n3. SynthSeg models are installed")
            import traceback
            traceback.print_exc()
        finally:
            self.ui.applyButton.enabled = True
            self.ui.applyButton.text = "Run Segmentation"


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

        # Instructions
        instructions = qt.QLabel(
            "<b>Setup Instructions:</b><br>"
            "1. Download SynthSeg from: <a href='https://github.com/BBillot/SynthSeg'>GitHub</a><br>"
            "2. Create Anaconda environment with TensorFlow, Keras, nibabel<br>"
            "3. Download model: <a href='https://drive.google.com/file/d/11ZW9ZxaESJk7RkMMVMAjyoGraCXgLwoq/view?usp=sharing'>synthseg_1.0.h5</a> → Save to SynthSeg/models/<br>"
            "4. Specify paths below"
        )
        instructions.setOpenExternalLinks(True)
        instructions.setWordWrap(True)
        layout.addRow(instructions)

        # SynthSeg path
        synthsegLayout = qt.QHBoxLayout()
        self.synthsegPathEdit = qt.QLineEdit()
        self.synthsegPathEdit.setPlaceholderText("C:/path/to/SynthSeg")
        synthsegBrowseButton = qt.QPushButton("Browse...")
        synthsegBrowseButton.clicked.connect(self.onBrowseSynthSeg)
        synthsegLayout.addWidget(self.synthsegPathEdit)
        synthsegLayout.addWidget(synthsegBrowseButton)
        layout.addRow("SynthSeg Path:", synthsegLayout)

        # Python path
        pythonLayout = qt.QHBoxLayout()
        self.pythonPathEdit = qt.QLineEdit()
        self.pythonPathEdit.setPlaceholderText("C:/anaconda3/envs/synthseg38/python.exe")
        pythonBrowseButton = qt.QPushButton("Browse...")
        pythonBrowseButton.clicked.connect(self.onBrowsePython)
        pythonLayout.addWidget(self.pythonPathEdit)
        pythonLayout.addWidget(pythonBrowseButton)
        layout.addRow("Python Executable:", pythonLayout)

        # Buttons
        buttonLayout = qt.QHBoxLayout()
        saveButton = qt.QPushButton("Save")
        saveButton.clicked.connect(self.onSave)
        cancelButton = qt.QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(saveButton)
        buttonLayout.addWidget(cancelButton)
        layout.addRow(buttonLayout)

    def loadCurrentConfig(self):
        """Load current configuration"""
        config = self.logic.getConfiguration()
        self.synthsegPathEdit.setText(config.get('synthseg_path', ''))
        self.pythonPathEdit.setText(config.get('python_path', ''))

    def onBrowseSynthSeg(self):
        """Browse for SynthSeg directory"""
        path = qt.QFileDialog.getExistingDirectory(self, "Select SynthSeg Directory")
        if path:
            self.synthsegPathEdit.setText(path)

    def onBrowsePython(self):
        """Browse for Python executable"""
        path = qt.QFileDialog.getOpenFileName(self, "Select Python Executable", "", "Python (python.exe python)")
        if path:
            self.pythonPathEdit.setText(path)

    def onSave(self):
        """Save configuration"""
        synthseg_path = self.synthsegPathEdit.text.strip()
        python_path = self.pythonPathEdit.text.strip()

        if not synthseg_path or not python_path:
            qt.QMessageBox.warning(self, "Missing Information", "Please provide both paths!")
            return

        # Validate
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
    Segmentation logic.
    """

    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        self.config = None
        self.loadConfiguration()

    def loadConfiguration(self):
        """Load configuration from SynthSegConfig"""
        try:
            from SynthSegConfig import SynthSegConfig
            self.config = SynthSegConfig()
        except:
            self.config = None

    def isConfigured(self):
        """Check if environment is configured"""
        if self.config is None:
            return False
        return self.config.is_configured()

    def getConfiguration(self):
        """Get current configuration"""
        if self.config:
            return self.config.get_config()
        return {}

    def validateAndSaveConfiguration(self, synthseg_path, python_path):
        """Validate and save configuration"""
        if self.config is None:
            try:
                from SynthSegConfig import SynthSegConfig
                self.config = SynthSegConfig()
            except Exception as e:
                return False, f"Failed to load SynthSegConfig: {str(e)}"

        # Validate SynthSeg path
        valid, msg = self.config.validate_synthseg_path(synthseg_path)
        if not valid:
            return False, f"SynthSeg path invalid: {msg}"

        # Validate Python environment
        valid, msg = self.config.validate_python_env(python_path)
        if not valid:
            return False, f"Python environment invalid: {msg}"

        # Save
        self.config.save_config(synthseg_path, python_path)
        return True, "Configuration saved"

    def testConfiguration(self):
        """Test current configuration"""
        if not self.isConfigured():
            return False, "Not configured"

        config = self.getConfiguration()

        # Test SynthSeg
        valid, msg = self.config.validate_synthseg_path(config['synthseg_path'])
        if not valid:
            return False, f"SynthSeg: {msg}"

        # Test Python
        valid, msg = self.config.validate_python_env(config['python_path'])
        if not valid:
            return False, f"Python: {msg}"

        return True, "All checks passed!"

    def process(self, inputVolume):
        """
        Run the segmentation algorithm.
        """
        import time
        startTime = time.time()
        logging.info('Processing started')

        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpDir:
            tmpPath = Path(tmpDir)

            # Save input volume
            inputPath = tmpPath / 'input.nii.gz'
            slicer.util.saveNode(inputVolume, str(inputPath))

            # Get script path
            scriptPath = Path(__file__).parent / 'synthseg_complete.py'

            # Run segmentation
            config = self.getConfiguration()
            cmd = [
                config['python_path'],
                str(scriptPath),
                '--input', str(inputPath),
                '--output', str(tmpPath)
            ]

            logging.info(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"SynthSeg processing failed with exit code {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}")

            # Load segmentation
            segPath = tmpPath / 'segmentation.nii.gz'
            if not segPath.exists():
                raise RuntimeError("Segmentation file not created")

            outputSegmentation = slicer.util.loadSegmentation(str(segPath))

        stopTime = time.time()
        logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')

        return outputSegmentation


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
