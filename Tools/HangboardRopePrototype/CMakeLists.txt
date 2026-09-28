cmake_minimum_required(VERSION 3.16)
project(hang_ten_rope_prototype LANGUAGES CXX)

set(BULLET_SOURCE "" CACHE PATH "Bullet 3.25 source root")
set(BULLET_BUILD "" CACHE PATH "Bullet 3.25 build root")
set(JSON_HEADER_DIR "" CACHE PATH "Directory containing json-v3.12.0.hpp")
foreach(required BULLET_SOURCE BULLET_BUILD JSON_HEADER_DIR)
  if(NOT IS_DIRECTORY "${${required}}")
    message(FATAL_ERROR "${required} must point to an existing directory")
  endif()
endforeach()

add_executable(rope_solver rope_solver.cpp)
target_compile_features(rope_solver PRIVATE cxx_std_17)
target_compile_definitions(rope_solver PRIVATE BT_USE_DOUBLE_PRECISION)
target_include_directories(rope_solver PRIVATE "${BULLET_SOURCE}/src" "${JSON_HEADER_DIR}")
target_link_libraries(rope_solver PRIVATE
  "${BULLET_BUILD}/src/BulletSoftBody/libBulletSoftBody.a"
  "${BULLET_BUILD}/src/BulletDynamics/libBulletDynamics.a"
  "${BULLET_BUILD}/src/BulletCollision/libBulletCollision.a"
  "${BULLET_BUILD}/src/LinearMath/libLinearMath.a"
)
