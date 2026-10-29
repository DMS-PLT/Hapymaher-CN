# Main CMakeLists
cmake_minimum_required(VERSION 3.20)

# Project Name
project(RxHook)

# Add Third Library
add_subdirectory("third")

# Set Source File Path
list(APPEND "${PROJECT_NAME}_SRC_FILE" 
    "src/RxHook/API.cpp" 
    "src/RxHook/Mem.cpp" 
    "src/RxHook/Hook.cpp" 
    "src/RxHook/ErrorMsg.cpp" )

# Set Current Library
add_library("${PROJECT_NAME}" "${${PROJECT_NAME}_SRC_FILE}")
target_include_directories("${PROJECT_NAME}" INTERFACE "src")
target_compile_features("${PROJECT_NAME}" PRIVATE cxx_std_23)
target_compile_definitions("${PROJECT_NAME}" PRIVATE UNICODE _UNICODE)
target_compile_options("${PROJECT_NAME}" PRIVATE "$<$<CXX_COMPILER_ID:MSVC>:/source-charset:utf-8>")

# Add Library
target_link_libraries("${PROJECT_NAME}" PRIVATE detours)

# Test
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    add_subdirectory("test")
endif()