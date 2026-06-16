cmake_minimum_required(VERSION 3.20)
project(localfs
    VERSION 0.2.0
    DESCRIPTION "A simple, fast, and beautiful local file sharing service"
    LANGUAGES NONE
)

# Python project — CMake is used here as a build-system wrapper
# for IDE integration and cross-platform consistency.

find_package(Python3 REQUIRED COMPONENTS Interpreter)

add_custom_target(build
    COMMAND ${Python3_EXECUTABLE} -m build --wheel --sdist .
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Building wheel and sdist"
)

add_custom_target(install-local
    COMMAND ${Python3_EXECUTABLE} -m pip install --user -e .
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Installing in editable mode"
)

add_custom_target(test
    COMMAND ${Python3_EXECUTABLE} -m pytest tests/ -v --tb=short
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running tests"
)

add_custom_target(lint
    COMMAND ${Python3_EXECUTABLE} -m ruff check .
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running linter"
)

add_custom_target(format
    COMMAND ${Python3_EXECUTABLE} -m ruff format .
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running formatter"
)

add_custom_target(clean
    COMMAND ${CMAKE_COMMAND} -E remove_directory build
    COMMAND ${CMAKE_COMMAND} -E remove_directory dist
    COMMAND ${Python3_EXECUTABLE} -c "import shutil, pathlib; [shutil.rmtree(p) for p in pathlib.Path('.').glob('*.egg-info')]"
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Cleaning build artifacts"
)

add_custom_target(run
    COMMAND ${Python3_EXECUTABLE} main.py
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Starting localfs server"
)

add_custom_target(release
    COMMAND ${Python3_EXECUTABLE} -m build --wheel --sdist .
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Building release artifacts"
)

set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/dist CACHE PATH "Install prefix")
