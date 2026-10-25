#-----------------------------------------------------------------------------
set(MODULE_NAME SlicerSynthSeg)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  SlicerSynthSegLib/__init__.py
  SlicerSynthSegLib/synthseg_config.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/UI/${MODULE_NAME}.ui
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
