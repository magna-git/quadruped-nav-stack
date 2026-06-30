cmake_minimum_required(VERSION 3.8)
project(quadruped_adapter)

set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)

set(UNITREE_SDK_DIR $ENV{HOME}/unitree_sdk2-main)

include_directories(
  ${UNITREE_SDK_DIR}/include
  ${UNITREE_SDK_DIR}/thirdparty/include
  ${UNITREE_SDK_DIR}/thirdparty/include/ddscxx
)

add_executable(robot_adapter src/robot_adapter.cpp)

target_link_libraries(robot_adapter
  ${UNITREE_SDK_DIR}/lib/x86_64/libunitree_sdk2.a
  ${UNITREE_SDK_DIR}/thirdparty/lib/x86_64/libddscxx.so
  ${UNITREE_SDK_DIR}/thirdparty/lib/x86_64/libddsc.so
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
