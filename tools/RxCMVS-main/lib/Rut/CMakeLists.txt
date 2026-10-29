# Main CMakeLists
cmake_minimum_required(VERSION 3.20)

# Project Name
project(Rut)

# Set Source File Path
list(APPEND "${PROJECT_NAME}_SRC_FILE" 
    "src/Rut/RxSys/Win32/File.cpp" 
    "src/Rut/RxSys/Win32/Path.cpp" 
    "src/Rut/RxSys/Win32/String.cpp" 
    "src/Rut/RxSys/Win32/System.cpp" 
    "src/Rut/RxBench.cpp" 
    "src/Rut/RxCmd.cpp" 
    "src/Rut/RxPath.cpp" 
    "src/Rut/RxFile.cpp" 
    "src/Rut/RxMem.cpp" 
    "src/Rut/RxINI.cpp" 
    "src/Rut/RxJson.cpp" 
    "src/Rut/RxStr.cpp" )

# Set Library
add_library("${PROJECT_NAME}" "${${PROJECT_NAME}_SRC_FILE}")
target_include_directories("${PROJECT_NAME}" INTERFACE "src")
target_compile_features("${PROJECT_NAME}" PRIVATE cxx_std_23)
target_compile_definitions("${PROJECT_NAME}" PRIVATE UNICODE _UNICODE)
target_compile_options("${PROJECT_NAME}" PRIVATE "$<$<CXX_COMPILER_ID:MSVC>:/source-charset:utf-8>")

# Test
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    add_subdirectory("test")
endif()

