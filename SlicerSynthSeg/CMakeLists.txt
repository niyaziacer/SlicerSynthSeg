#-----------------------------------------------------------------------------
set(MODULE_NAME SlicerSynthSeg)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  SlicerSynthSegLib/__init__.py
  SlicerSynthSegLib/synthseg_config.py
  SlicerSynthSegLib/run_synthseg_tfkeras.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/UI/${MODULE_NAME}.ui
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
# Bundled SynthSeg source code (B. Billot et al., Apache License 2.0, see SynthSeg/LICENSE.txt).
# Installed next to the module so the packaged extension contains it; the model weights (.h5) are not
# packaged: they are downloaded on first use.
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../SynthSeg/
  DESTINATION ${Slicer_INSTALL_QTSCRIPTEDMODULES_LIB_DIR}/SlicerSynthSegLib/SynthSeg
  COMPONENT RuntimeLibraries
  PATTERN "*.h5" EXCLUDE
  PATTERN "__pycache__" EXCLUDE
  PATTERN ".gitignore" EXCLUDE
  )
