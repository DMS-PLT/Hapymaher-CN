# Detours
project(detours)

# Add Library
add_library("${PROJECT_NAME}" 
    "Detours/src/creatwth.cpp"
    "Detours/src/detours.cpp"
    "Detours/src/disasm.cpp"
    "Detours/src/disolarm64.cpp"
    "Detours/src/disolx64.cpp"
    "Detours/src/disolx86.cpp"
    "Detours/src/image.cpp"
    "Detours/src/modules.cpp"
)
target_include_directories("${PROJECT_NAME}" INTERFACE "Detours/src")
target_compile_options("${PROJECT_NAME}" PRIVATE /nologo /WX /we4777 /we4800 /Zi /Gy /Gm- /Zl /DWIN32_LEAN_AND_MEAN)

