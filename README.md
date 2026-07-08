# quadruped-nav-stack

Stack de navigation ROS 2 (Jazzy) pour quadrupede Unitree B2-W.

## Structure du workspace

```
src/
  quadruped_adapter/   Pont cmd_vel -> SDK Unitree (C++), watchdog inclus
  quadruped_bringup/   Chaine de perception + mapping
    launch/sensors.launch.py   TF lidar, odom_to_tf, pointcloud_to_laserscan (commun)
    launch/mapping.launch.py   sensors + slam_toolbox (mode mapping)
    maps/                      Cartes sauvegardees (.pgm/.yaml)
  quadruped_nav2/      Stack de navigation nav2
    launch/navigation.launch.py  AMCL + DWB + planif + waypoints
    config/nav2_params.yaml      Tous les parametres nav2, commentes
profiles/b2.yaml       Parametres robot (topics, limites de vitesse, frames)
```

## Mapping

```
ros2 launch quadruped_bringup mapping.launch.py
```

Une fois la carte satisfaisante, la sauvegarder dans `src/quadruped_bringup/maps/` :

```
ros2 run nav2_map_server map_saver_cli -f src/quadruped_bringup/maps/<nom_carte>
```

## Navigation (localisation + evitement d'obstacles + waypoints)

```
ros2 launch quadruped_nav2 navigation.launch.py map:=<chemin_vers_carte>.yaml
```

Par defaut, `map` pointe vers `innov8_map.yaml` (deja fournie).

- **Localisation** : AMCL sur la carte statique.
- **Evitement d'obstacles** : costmap locale alimentee par `/scan_synced`, controller DWB.
- **Waypoints** : dans RViz, plugin *Nav2 Waypoint/Goal*, poser plusieurs points puis
  lancer la mission. Alternative scriptee possible via `nav2_simple_commander`
  (`follow_waypoints`) si besoin d'automatiser une tournee.

Rappel : les valeurs marquees `TODO` dans `nav2_params.yaml` (rayon du robot,
limites de vitesse precises) sont des defauts raisonnables a affiner avec les
vraies mesures/perfs du B2-W avant un deploiement en conditions reelles.
