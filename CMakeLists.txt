cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(SynthSeg)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/niyaziacer/SlicerSynthSeg")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Niyazi Acer (Erciyes University)")
set(EXTENSION_DESCRIPTION "Brain MRI segmentation with SynthSeg (Billot et al.): contrast- and resolution-agnostic segmentation of 30+ structures, optional Desikan-Killiany cortical parcellation (SynthSeg 2.0) and a volume table. Runs in Slicer's own Python: TensorFlow and the model files are installed on first use, no conda needed.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/niyaziacer/SlicerSynthSeg/main/SlicerSynthSeg/Resources/Icons/SlicerSynthSeg.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/niyaziacer/SlicerSynthSeg/main/docs/screenshot.jpeg")
set(EXTENSION_DEPENDS "NA")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(SlicerSynthSeg)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
