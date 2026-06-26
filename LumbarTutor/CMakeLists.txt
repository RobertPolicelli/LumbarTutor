cmake_minimum_required(VERSION 2.8.9)

project(LumbarTutor)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "www.perktutor.org")
set(EXTENSION_CATEGORY "Training")
set(EXTENSION_CONTRIBUTORS "Matthew S. Holden (Perk Lab, Queen's University)")
set(EXTENSION_DESCRIPTION "Lumbar puncture training")
set(EXTENSION_ICONURL "")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_DEPENDS "PerkTutor")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(LumbarTutor)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
