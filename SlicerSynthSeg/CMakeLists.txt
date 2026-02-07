@"
#-----------------------------------------------------------------------------
set(MODULE_NAME SlicerSynthSeg)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  `${MODULE_NAME}.py
  synthseg_complete.py
  __init__.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/`${MODULE_NAME}.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME `${MODULE_NAME}
  SCRIPTS `${MODULE_PYTHON_SCRIPTS}
  RESOURCES `${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
"@ | Out-File -FilePath "C:\Users\LENOVO\Desktop\SynthSeg_test\SlicerSynthSegPublic\SlicerSynthSeg\CMakeLists.txt" -Encoding UTF8