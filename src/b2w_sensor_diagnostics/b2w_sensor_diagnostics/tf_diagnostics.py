from typing import List, Optional, Sequence, Tuple

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


class TfDiagnostics(Node):
    def __init__(self) -> None:
        super().__init__('tf_diagnostics')
        self._buffer = Buffer()
        self._listener = TransformListener(self._buffer, self, spin_thread=False)
        self._pairs = (
            ('robot_center', 'rslidar'),
            ('robot_center', 'dog_imu_link'),
            ('dog_imu_link', 'rslidar'),
            ('odom', 'robot_center'),
            ('map', 'odom'),
        )
        self.create_timer(2.0, self._report)

    def _lookup(self, target_frame: str, source_frame: str) -> Tuple[bool, List[str]]:
        try:
            transform = self._buffer.lookup_transform(
                target_frame,
                source_frame,
                Time(),
                timeout=Duration(seconds=0.05),
            )
        except TransformException as exc:
            return False, [
                f'Transform: {target_frame} -> {source_frame}',
                '  Available: no',
                f'  Error: {str(exc).replace(chr(34) * 2, chr(34))}',
            ]
        except Exception as exc:
            return False, [
                f'Transform: {target_frame} -> {source_frame}',
                '  Available: no',
                f'  Error: {str(exc).replace(chr(34) * 2, chr(34))}',
            ]

        t = transform.transform.translation
        q = transform.transform.rotation
        return True, [
            f'Transform: {target_frame} -> {source_frame}',
            '  Available: yes',
            f'  Translation: x={t.x:.6f} y={t.y:.6f} z={t.z:.6f}',
            f'  Quaternion: x={q.x:.6f} y={q.y:.6f} z={q.z:.6f} w={q.w:.6f}',
        ]

    def _can_chain(self, target_frame: str, source_frame: str) -> bool:
        try:
            return self._buffer.can_transform(
                target_frame,
                source_frame,
                Time(),
                timeout=Duration(seconds=0.05),
            )
        except Exception:
            return False

    def _report(self) -> None:
        lines = ['========== TF DIAGNOSTICS ==========']
        available_count = 0
        for target, source in self._pairs:
            available, block = self._lookup(target, source)
            if available:
                available_count += 1
            lines.extend(['', *block])

        odom_to_rslidar = self._can_chain('odom', 'rslidar')
        odom_to_imu = self._can_chain('odom', 'dog_imu_link')
        lidar_and_imu_connected = self._can_chain('robot_center', 'rslidar') and self._can_chain(
            'robot_center', 'dog_imu_link'
        )
        map_to_odom = self._can_chain('map', 'odom')

        if available_count == 0:
            observation = 'No TF frames detected'
        elif odom_to_rslidar and odom_to_imu and lidar_and_imu_connected:
            observation = 'Required TF tree available'
        else:
            observation = 'TF tree partially available'

        lines.extend(
            [
                '',
                f'Global observation: {observation}',
                '',
                'Chains:',
                f'  odom -> rslidar: {"yes" if odom_to_rslidar else "no"}',
                f'  odom -> dog_imu_link: {"yes" if odom_to_imu else "no"}',
                f'  LiDAR and IMU connected to robot_center: {"yes" if lidar_and_imu_connected else "no"}',
                f'  map -> odom: {"yes" if map_to_odom else "no"}',
                '',
                '====================================',
            ]
        )
        for line in lines:
            self.get_logger().info(line)


def main(args: Optional[Sequence[str]] = None) -> None:
    rclpy.init(args=args)
    node = TfDiagnostics()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
