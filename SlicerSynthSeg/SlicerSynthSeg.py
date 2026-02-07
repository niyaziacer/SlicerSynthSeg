import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import numpy as np

#
# SlicerSynthSeg
#

class SlicerSynthSeg(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "SynthSeg"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["SlicerSynthSeg Team"]
        self.parent.helpText = """
        This module performs automated brain MRI segmentation using SynthSeg.
        It segments brain structures and exports volume measurements.
        """
        self.parent.acknowledgementText = """
        Based on SynthSeg by BBillot et al.
        https://github.com/BBillot/SynthSeg
        """

#
# SlicerSynthSegWidget
#

class SlicerSynthSegWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._updatingGUIFromParameterNode = False

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Create the main collapsible button
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Parameters"
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        #
        # Input volume selector
        #
        self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
        self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputVolumeSelector.selectNodeUponCreation = True
        self.inputVolumeSelector.addEnabled = False
        self.inputVolumeSelector.removeEnabled = False
        self.inputVolumeSelector.noneEnabled = False
        self.inputVolumeSelector.showHidden = False
        self.inputVolumeSelector.showChildNodeTypes = False
        self.inputVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.inputVolumeSelector.setToolTip("Select the input T1 MRI volume")
        parametersFormLayout.addRow("Input Volume: ", self.inputVolumeSelector)

        #
        # Output segmentation selector
        #
        self.outputSegmentationSelector = slicer.qMRMLNodeComboBox()
        self.outputSegmentationSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
        self.outputSegmentationSelector.selectNodeUponCreation = True
        self.outputSegmentationSelector.addEnabled = True
        self.outputSegmentationSelector.removeEnabled = True
        self.outputSegmentationSelector.noneEnabled = True
        self.outputSegmentationSelector.showHidden = False
        self.outputSegmentationSelector.showChildNodeTypes = False
        self.outputSegmentationSelector.setMRMLScene(slicer.mrmlScene)
        self.outputSegmentationSelector.setToolTip("Select or create output segmentation")
        parametersFormLayout.addRow("Output Segmentation: ", self.outputSegmentationSelector)

        #
        # Apply Button
        #
        self.applyButton = qt.QPushButton("Run Segmentation")
        self.applyButton.toolTip = "Run the SynthSeg segmentation algorithm"
        self.applyButton.enabled = False
        parametersFormLayout.addRow(self.applyButton)

        #
        # Status Label
        #
        self.statusLabel = qt.QLabel("")
        self.statusLabel.setWordWrap(True)
        parametersFormLayout.addRow(self.statusLabel)

        # Create logic class
        self.logic = SlicerSynthSegLogic()

        # Connections
        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
        self.outputSegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Refresh Apply button state
        self.onSelect()

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def onSelect(self):
        """
        Update the apply button state based on selections
        """
        self.applyButton.enabled = self.inputVolumeSelector.currentNode() is not None

    def onApplyButton(self):
        """
        Run processing when user clicks "Apply" button.
        """
        try:
            self.applyButton.enabled = False
            self.statusLabel.text = "Running SynthSeg segmentation... This may take several minutes."
            slicer.app.processEvents()

            # Get input/output nodes
            inputVolume = self.inputVolumeSelector.currentNode()
            outputSegmentation = self.outputSegmentationSelector.currentNode()
            
            if not outputSegmentation:
                outputSegmentation = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
                outputSegmentation.SetName(inputVolume.GetName() + "_SynthSeg")
                self.outputSegmentationSelector.setCurrentNode(outputSegmentation)

            # Run segmentation
            self.logic.process(inputVolume, outputSegmentation)

            self.statusLabel.text = "Segmentation completed successfully!"

        except Exception as e:
            self.statusLabel.text = f"Error: {str(e)}"
            slicer.util.errorDisplay("Failed to compute results: "+str(e))
            import traceback
            traceback.print_exc()
        finally:
            self.applyButton.enabled = True


#
# SlicerSynthSegLogic
#

class SlicerSynthSegLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self):
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    def setDefaultParameters(self, parameterNode):
        """
        Initialize parameter node with default settings.
        """
        if not parameterNode.GetParameter("Threshold"):
            parameterNode.SetParameter("Threshold", "100.0")

    def process(self, inputVolume, outputSegmentation):
        """
        Run the processing algorithm using SynthSeg.
        :param inputVolume: volume to be segmented
        :param outputSegmentation: segmentation result
        """
        
        if not inputVolume or not outputSegmentation:
            raise ValueError("Input or output volume is invalid")

        import time
        import tempfile
        import subprocess
        import sys
        from pathlib import Path
        import shutil
        
        startTime = time.time()
        logging.info('Processing started')

        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        input_file = temp_dir / "input.nii.gz"
        output_file = temp_dir / "segmentation.nii.gz"
        csv_file = temp_dir / "volumes.csv"
        
        try:
            # Save input volume to file
            logging.info(f"Saving input volume to: {input_file}")
            slicer.util.saveNode(inputVolume, str(input_file))
            
            # Find synthseg_complete.py script
            module_dir = Path(__file__).parent
            synthseg_script = module_dir / "synthseg_complete.py"
            
            if not synthseg_script.exists():
                raise FileNotFoundError(f"SynthSeg script not found at: {synthseg_script}\nPlease ensure synthseg_complete.py is in the module folder.")
            
            logging.info(f"Found SynthSeg script at: {synthseg_script}")
            
            # Run SynthSeg
            logging.info("Running SynthSeg segmentation (this may take several minutes)...")
            cmd = [
                sys.executable,
                str(synthseg_script),
                '--input', str(input_file),
                '--output', str(temp_dir),
                '--keep-csv'
            ]
            
            logging.info(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging.info("SynthSeg output:")
            logging.info(result.stdout)
            
            if result.stderr:
                logging.warning("SynthSeg warnings/errors:")
                logging.warning(result.stderr)
            
            # Load segmentation result
            if output_file.exists():
                logging.info(f"Loading segmentation from: {output_file}")
                segNode = slicer.util.loadSegmentation(str(output_file))
                
                if segNode:
                    # Copy segments to output
                    outputSegmentation.GetSegmentation().RemoveAllSegments()
                    for i in range(segNode.GetSegmentation().GetNumberOfSegments()):
                        segment = segNode.GetSegmentation().GetNthSegment(i)
                        outputSegmentation.GetSegmentation().AddSegment(segment)
                    
                    # Set reference geometry
                    outputSegmentation.SetReferenceImageGeometryParameterFromVolumeNode(inputVolume)
                    
                    # Remove temporary node
                    slicer.mrmlScene.RemoveNode(segNode)
                    
                    logging.info(f'Processing completed successfully in {time.time()-startTime:.2f} seconds')
                    logging.info(f'Number of segments: {outputSegmentation.GetSegmentation().GetNumberOfSegments()}')
                else:
                    raise RuntimeError("Failed to load segmentation file")
            else:
                raise RuntimeError(f"Segmentation output not created at: {output_file}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"SynthSeg processing failed with exit code {e.returncode}\n"
            error_msg += f"stdout: {e.stdout}\n"
            error_msg += f"stderr: {e.stderr}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logging.error(f"SynthSeg processing failed: {str(e)}")
            raise
        finally:
            # Cleanup temporary files
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logging.info("Cleaned up temporary files")
            except Exception as e:
                logging.warning(f"Failed to cleanup temporary files: {str(e)}")


#
# SlicerSynthSegTest
#

class SlicerSynthSegTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_SlicerSynthSeg1()

    def test_SlicerSynthSeg1(self):
        """ Test basic functionality
        """

        self.delayDisplay("Starting the test")

        # Test the module logic
        logic = SlicerSynthSegLogic()

        self.delayDisplay('Test passed')