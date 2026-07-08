#!/usr/bin/env python3

import argparse
import select
import sys
import termios
import threading
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import QoSProfile


HELP_TEXT = """
Teleoperation ROS2 B2
  Z : avancer
  S : reculer
  Q : translation gauche
  D : translation droite
  A : rotation gauche
  E : rotation droite
  Espace : stop
  C : active/desactive la teleop
  H : aide
  X : quitter
""".strip()


class RawTerminal:
    def __init__(self) -> None:
        self.fd = sys.stdin.fileno()
        self.original = termios.tcgetattr(self.fd)

    def __enter__(self):
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.original)


class TeleopNode(Node):
    def __init__(self, topic: str, publish_hz: float) -> None:
        super().__init__("unitree_ros2_headless_teleop")
        qos = QoSProfile(depth=1)
        self.publisher = self.create_publisher(Twist, topic, qos)
        self.enabled = True
        self.command = (0.0, 0.0, 0.0)
        self.last_sent = None
        self.lock = threading.Lock()
        self.timer = self.create_timer(1.0 / publish_hz, self.publish_current_command)

    def set_command(self, vx: float, vy: float, wz: float) -> None:
        with self.lock:
            self.command = (vx, vy, wz)

    def toggle_enabled(self) -> bool:
        with self.lock:
            self.enabled = not self.enabled
            if not self.enabled:
                self.command = (0.0, 0.0, 0.0)
            return self.enabled

    def stop(self) -> None:
        self.set_command(0.0, 0.0, 0.0)
        self.publish_current_command(force=True)

    def publish_current_command(self, force: bool = False) -> None:
        with self.lock:
            enabled = self.enabled
            vx, vy, wz = self.command

        if not enabled:
            vx, vy, wz = 0.0, 0.0, 0.0

        twist = Twist()
        twist.linear.x = float(vx)
        twist.linear.y = float(vy)
        twist.angular.z = float(wz)
        self.publisher.publish(twist)

        current = (vx, vy, wz, enabled)
        if force or current != self.last_sent:
            status = "activee" if enabled else "desactivee"
            self.get_logger().info(
                f"cmd_vel -> x={vx:.2f} y={vy:.2f} yaw={wz:.2f} teleop={status}"
            )
            self.last_sent = current


def parse_args():
    parser = argparse.ArgumentParser(description="Teleop headless ROS2 pour Unitree B2")
    parser.add_argument(
        "--topic",
        default="/cmd_vel",
        help="Topic cmd_vel cible",
    )
    parser.add_argument("--vx", type=float, default=0.30, help="Vitesse avant/arriere (m/s)")
    parser.add_argument("--vy", type=float, default=0.20, help="Vitesse laterale (m/s)")
    parser.add_argument("--vyaw", type=float, default=0.50, help="Rotation (rad/s)")
    parser.add_argument("--rate", type=float, default=20.0, help="Frequence de publication (Hz)")
    return parser.parse_args()


def read_char(timeout: float = 0.1):
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
      return sys.stdin.read(1)
    return None


def main():
    args = parse_args()

    rclpy.init()
    node = TeleopNode(args.topic, args.rate)

    spinner = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spinner.start()

    print(f"Publication sur {args.topic}")
    print(HELP_TEXT)

    try:
        with RawTerminal():
            while rclpy.ok():
                char = read_char()
                if char is None:
                    continue

                if char in ("z", "Z", "w", "W"):
                    node.set_command(args.vx, 0.0, 0.0)
                elif char in ("s", "S"):
                    node.set_command(-args.vx, 0.0, 0.0)
                elif char in ("q", "Q"):
                    node.set_command(0.0, args.vy, 0.0)
                elif char in ("d", "D"):
                    node.set_command(0.0, -args.vy, 0.0)
                elif char in ("a", "A"):
                    node.set_command(0.0, 0.0, args.vyaw)
                elif char in ("e", "E"):
                    node.set_command(0.0, 0.0, -args.vyaw)
                elif char == " ":
                    node.stop()
                elif char in ("c", "C"):
                    enabled = node.toggle_enabled()
                    print(f"Teleop {'activee' if enabled else 'desactivee'}")
                elif char in ("h", "H"):
                    print(HELP_TEXT)
                elif char in ("x", "X"):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        time.sleep(0.1)
        node.destroy_node()
        rclpy.shutdown()
        spinner.join(timeout=1.0)


if __name__ == "__main__":
    main()
