"""Start FireScout FS-01 in VMware or a native Ubuntu installation.

VMware: ros2 launch firescout_fs01 simulation.launch.py sim_mode:=vm
Native: ros2 launch firescout_fs01 simulation.launch.py sim_mode:=native
"""

from pathlib import Path
import subprocess
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    OpaqueFunction,
    RegisterEventHandler,
    TimerAction,
)
from launch.event_handlers import OnProcessStart
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start_firescout(context):
    sim_mode = LaunchConfiguration('sim_mode').perform(context)
    share = Path(get_package_share_directory('firescout_fs01'))

    world_file = share / 'worlds' / 'industrial_world.sdf'
    xacro_file = share / 'urdf' / 'firescout.urdf.xacro'
    bridge_file = share / 'config' / 'bridge.yaml'
    rviz_file = share / 'rviz' / 'firescout.rviz'

    robot_description = subprocess.check_output(
        ['xacro', str(xacro_file)], text=True
    )
    urdf_file = Path(tempfile.gettempdir()) / 'firescout_fs01_generated.urdf'
    urdf_file.write_text(robot_description, encoding='utf-8')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
        output='screen',
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': str(bridge_file)}],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', str(rviz_file)],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    robot_spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-world', 'industrial_world',
            '-name', 'firescout_fs01',
            '-file', str(urdf_file),
            '-x', '0', '-y', '-1.8', '-z', '0.15',
        ],
        output='screen',
    )

    if sim_mode == 'vm':
        gazebo = ExecuteProcess(
            cmd=[
                'gz', 'sim', '-v', '4', '-r', '-s',
                '--render-engine-server', 'ogre2',
                str(world_file),
            ],
            additional_env={'LIBGL_ALWAYS_SOFTWARE': '1'},
            output='screen',
        )
        gui = TimerAction(
            period=3.0,
            actions=[ExecuteProcess(
                cmd=['gz', 'sim', '-g', '--render-engine-gui', 'ogre'],
                output='screen',
            )],
        )
    else:
        gazebo = ExecuteProcess(
            cmd=['gz', 'sim', '-v', '4', '-r', str(world_file)],
            output='screen',
        )
        gui = None  # Native mode: Gazebo starts GUI with the server.

    # Wait after the Gazebo process starts before requesting model creation.
    spawn_handler = RegisterEventHandler(
        OnProcessStart(
            target_action=gazebo,
            on_start=[TimerAction(period=8.0, actions=[robot_spawn])],
        )
    )

    actions = [spawn_handler, gazebo, bridge, robot_state_publisher, rviz]
    if gui is not None:
        actions.append(gui)
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'sim_mode',
            default_value='vm',
            choices=['vm', 'native'],
            description='vm: split Gazebo rendering, native: standard Gazebo',
        ),
        OpaqueFunction(function=start_firescout),
    ])
