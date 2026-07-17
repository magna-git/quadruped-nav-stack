# Architecture générale

## Objectif

`quadruped-nav-stack` fournit une base ROS 2 réutilisable pour le mapping,
la localisation, la navigation et le contrôle de plusieurs robots mobiles.

Le projet distingue clairement :

- les composants ROS 2 génériques ;
- les configurations propres à chaque robot ;
- l’interface entre `/cmd_vel` et le SDK du constructeur.

## Architecture logique

```text
Capteurs du robot
    |
    +-- LiDAR 3D
    +-- Odométrie
    +-- IMU
    |
    v
Perception et transformations TF
    |
    +-- pointcloud_to_laserscan
    +-- odom_to_tf
    +-- transforms statiques
    |
    v
SLAM / Localisation
    |
    +-- SLAM Toolbox
    +-- carte OccupancyGrid
    |
    v
Nav2
    |
    +-- planificateur
    +-- contrôleur
    +-- costmaps
    +-- waypoints
    |
    v
/cmd_vel
    |
    v
quadruped_adapter
    |
    v
SDK constructeur
    |
    v
Robot
