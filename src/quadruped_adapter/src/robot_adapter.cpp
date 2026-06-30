#include <memory>
#include <string>
#include <chrono>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"

#include "unitree/robot/channel/channel_factory.hpp"
#include "unitree/robot/b2/sport/sport_client.hpp"

using namespace std::chrono_literals;

class RobotAdapter : public rclcpp::Node
{
public:
  RobotAdapter() : Node("robot_adapter")
  {
    // -- 1. Paramètres (lus depuis le profil YAML ou valeurs par défaut) --
    this->declare_parameter("cmd_vel_topic", "/cmd_vel");
    this->declare_parameter("network_interface", "eth0");
    this->declare_parameter("max_vx", 0.5);
    this->declare_parameter("max_vy", 0.3);
    this->declare_parameter("max_vyaw", 0.8);

    cmd_vel_topic_ = this->get_parameter("cmd_vel_topic").as_string();
    std::string iface = this->get_parameter("network_interface").as_string();
    max_vx_   = this->get_parameter("max_vx").as_double();
    max_vy_   = this->get_parameter("max_vy").as_double();
    max_vyaw_ = this->get_parameter("max_vyaw").as_double();

    RCLCPP_INFO(this->get_logger(),
      "RobotAdapter démarré | interface=%s | max_vx=%.2f max_vy=%.2f max_vyaw=%.2f",
      iface.c_str(), max_vx_, max_vy_, max_vyaw_);

    // -- 2. Initialiser le SDK Unitree --
    unitree::robot::ChannelFactory::Instance()->Init(0, iface);

    sport_client_ = std::make_unique<unitree::robot::b2::SportClient>();
    sport_client_->SetTimeout(1.0f);
    sport_client_->Init();

    RCLCPP_INFO(this->get_logger(), "SportClient B2 initialisé");

    // -- 3. Subscriber /cmd_vel --
    sub_cmd_vel_ = this->create_subscription<geometry_msgs::msg::Twist>(
      cmd_vel_topic_, 1,
      [this](const geometry_msgs::msg::Twist::SharedPtr msg) {
        this->onCmdVel(msg);
      });

    RCLCPP_INFO(this->get_logger(),
      "En attente de commandes sur %s", cmd_vel_topic_.c_str());

    // -- 4. Timer watchdog 500ms --
    // Si plus aucun cmd_vel reçu depuis 500ms → stop
    watchdog_ = this->create_wall_timer(500ms, [this]() {
      auto now = this->now();
      if (last_cmd_time_.seconds() > 0 &&
          (now - last_cmd_time_).seconds() > 0.5) {
        sport_client_->StopMove();
        vx_ = vy_ = vyaw_ = 0.0;
      }
    });
  }

  ~RobotAdapter() {
    if (sport_client_) {
      sport_client_->StopMove();
    }
  }

private:
  void onCmdVel(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    // Clamp aux limites du profil
    vx_   = std::clamp(msg->linear.x,  -max_vx_,   max_vx_);
    vy_   = std::clamp(msg->linear.y,  -max_vy_,   max_vy_);
    vyaw_ = std::clamp(msg->angular.z, -max_vyaw_, max_vyaw_);

    last_cmd_time_ = this->now();

    // Appel direct au SDK Unitree
    sport_client_->Move(
      static_cast<float>(vx_),
      static_cast<float>(vy_),
      static_cast<float>(vyaw_)
    );

    RCLCPP_INFO_THROTTLE(this->get_logger(), *this->get_clock(), 1000,
      "Move → vx=%.2f vy=%.2f vyaw=%.2f", vx_, vy_, vyaw_);
  }

  // Paramètres
  std::string cmd_vel_topic_;
  double max_vx_, max_vy_, max_vyaw_;

  // SDK Unitree
  std::unique_ptr<unitree::robot::b2::SportClient> sport_client_;

  // ROS2
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr sub_cmd_vel_;
  rclcpp::TimerBase::SharedPtr watchdog_;

  // Etat
  double vx_ = 0.0, vy_ = 0.0, vyaw_ = 0.0;
  rclcpp::Time last_cmd_time_{0, 0, RCL_ROS_TIME};
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<RobotAdapter>());
  rclcpp::shutdown();
  return 0;
}
