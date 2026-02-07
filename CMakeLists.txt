@"
cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SlicerSynthSeg)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/niyaziacer/SlicerSynthSeg")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "SlicerSynthSeg Team")
set(EXTENSION_DESCRIPTION "Automated brain MRI segmentation using SynthSeg")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/niyaziacer/SlicerSynthSeg/main/SlicerSynthSeg.png")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_DEPENDS "NA")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(`${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SlicerSynthSeg)

#-----------------------------------------------------------------------------
include(`${Slicer_EXTENSION_GENERATE_CONFIG})
include(`${Slicer_EXTENSION_CPACK})
"@ | Out-File -FilePath "C:\Users\LENOVO\Desktop\SynthSeg_test\SlicerSynthSegPublic\CMakeLists.txt" -Encoding UTF8