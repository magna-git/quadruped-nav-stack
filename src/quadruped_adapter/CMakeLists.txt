cmake_minimum_required(VERSION 3.8)
project(quadruped_adapter)

set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

if(NOT DEFINED UNITREE_SDK_DIR OR UNITREE_SDK_DIR STREQUAL "")
  if(DEFINED ENV{UNITREE_SDK_DIR} AND NOT "$ENV{UNITREE_SDK_DIR}" STREQUAL "")
    set(UNITREE_SDK_DIR "$ENV{UNITREE_SDK_DIR}")
  else()
    set(UNITREE_SDK_DIR "$ENV{HOME}/unitree_sdk2")
  endif()
endif()
set(UNITREE_SDK_DIR "${UNITREE_SDK_DIR}" CACHE PATH
  "Path to the separately installed Unitree SDK 2")

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
  set(UNITREE_SDK_ARCH aarch64)
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64|AMD64)$")
  set(UNITREE_SDK_ARCH x86_64)
else()
  message(FATAL_ERROR
    "Unsupported architecture '${CMAKE_SYSTEM_PROCESSOR}' for Unitree SDK 2")
endif()

set(UNITREE_SDK_LIBRARY_DIR "${UNITREE_SDK_DIR}/lib/${UNITREE_SDK_ARCH}")
set(UNITREE_SDK_THIRDPARTY_LIBRARY_DIR
  "${UNITREE_SDK_DIR}/thirdparty/lib/${UNITREE_SDK_ARCH}")

foreach(required_path
    "${UNITREE_SDK_DIR}/include"
    "${UNITREE_SDK_DIR}/thirdparty/include"
    "${UNITREE_SDK_LIBRARY_DIR}/libunitree_sdk2.a"
    "${UNITREE_SDK_THIRDPARTY_LIBRARY_DIR}/libddscxx.so"
    "${UNITREE_SDK_THIRDPARTY_LIBRARY_DIR}/libddsc.so")
  if(NOT EXISTS "${required_path}")
    message(FATAL_ERROR
      "Unitree SDK 2 is missing or incomplete at '${UNITREE_SDK_DIR}'. "
      "Set UNITREE_SDK_DIR with -DUNITREE_SDK_DIR=/path/to/unitree_sdk2 "
      "or export UNITREE_SDK_DIR=/path/to/unitree_sdk2.")
  endif()
endforeach()

include_directories(
  ${UNITREE_SDK_DIR}/include
  ${UNITREE_SDK_DIR}/thirdparty/include
  ${UNITREE_SDK_DIR}/thirdparty/include/ddscxx
)

add_executable(robot_adapter src/robot_adapter.cpp)

target_link_libraries(robot_adapter
  ${UNITREE_SDK_LIBRARY_DIR}/libunitree_sdk2.a
  ${UNITREE_SDK_THIRDPARTY_LIBRARY_DIR}/libddscxx.so
  ${UNITREE_SDK_THIRDPARTY_LIBRARY_DIR}/libddsc.so
  pthread
  dl
)

ament_target_dependencies(robot_adapter
  rclcpp
  geometry_msgs
)

install(TARGETS robot_adapter
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
