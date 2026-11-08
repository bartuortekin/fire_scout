cmake_minimum_required(VERSION 3.8)
project(firescout_fs01)
find_package(ament_cmake REQUIRED)
install(
    DIRECTORY urdf worlds config launch rviz
    DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/camera_monitor.py
  scripts/imu_monitor.py
  scripts/lidar_monitor.py
  scripts/firescout_fsm.py
  DESTINATION lib/${PROJECT_NAME}
)
ament_package()
