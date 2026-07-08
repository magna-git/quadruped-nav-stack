# Plan de test — B2-W nav stack

## 0. Corrige depuis la derniere session (a re-verifier, pas encore teste en vrai)

- [x] `quadruped_adapter` est maintenant lance automatiquement via
      `actuation.launch.py`, inclus par `mapping.launch.py` et
      `navigation.launch.py`. Plus besoin de le demarrer a la main.
- [x] `teleop.py` publie par defaut sur `/cmd_vel` (aligne avec
      `robot_adapter` et la sortie nav2).
- [x] `profiles/b2.yaml` deplace dans `quadruped_bringup` et reellement
      charge (odom_to_tf, pointcloud_to_laserscan, robot_adapter) au lieu
      d'etre un doc mort.
- [x] `quadruped_slam` (package vide, sans rapport avec le vrai pipeline
      SLAM) supprime.

Reste ouvert :
- [ ] TF statique `robot_center -> rslidar` = identite (0,0,0,0,0,0) dans
      `sensors.launch.py` — a verifier/calibrer contre le vrai montage du LiDAR.

## 1. Build

```
colcon build --symlink-install
source install/setup.bash
```
Verifier qu'il ne manque pas `nav2_bringup`, `nav2_map_server`, `nav2_amcl`,
`nav2_controller`, `nav2_planner`, `nav2_behaviors`, `nav2_bt_navigator`,
`nav2_waypoint_follower`, `nav2_velocity_smoother`, `nav2_lifecycle_manager`,
`slam_toolbox`, `pointcloud_to_laserscan` sur la machine qui va reellement
tourner (onboard du robot, pas ce laptop de dev).

## 2. Sanity check moteur (adapter + teleop maintenant lies)

```
ros2 launch quadruped_bringup mapping.launch.py robot:=b2
ros2 run quadruped_bringup teleop
```
- Verifier que `robot_adapter` demarre bien tout seul avec le launch (log
  "SportClient B2 initialise").
- Verifier : le robot avance/recule/tourne correctement, le watchdog coupe
  bien le mouvement si plus rien n'est publie 500ms.

## 3. Mapping (deja valide, a rejouer pour confirmer le fix + la nouvelle structure)

- Verifier que le TF `map -> odom -> robot_center -> rslidar` est complet
  (`ros2 run tf2_tools view_frames`).
- Verifier que la carte se construit/se recale en bougeant peu (le fix
  2cm doit se voir : plus besoin de faire un grand trajet pour que
  slam_toolbox recale).
- Sauver une nouvelle carte si besoin :
  `ros2 run nav2_map_server map_saver_cli -f src/quadruped_bringup/maps/<nom>`
  puis **`colcon build --symlink-install`** pour qu'elle soit visible du launch nav2.

## 4. Navigation (AMCL + DWB + waypoints) — le nouveau morceau, jamais teste

```
ros2 launch quadruped_nav2 navigation.launch.py robot:=b2
```
Sans `map:=`, prend automatiquement la derniere carte sauvegardee (par date
de modification) dans `maps/`. Verifier dans les logs que c'est bien la bonne
carte qui est chargee avant de continuer.
- [ ] Les lifecycle managers passent bien tous les noeuds en `active`
  (`ros2 lifecycle list /amcl`, etc., ou `ros2 topic echo /amcl/transition_event`).
- [ ] AMCL converge : donner une pose initiale dans RViz (`2D Pose Estimate`),
  verifier que le nuage de particules se resserre en bougeant un peu.
- [ ] Costmap locale : verifier dans RViz que les obstacles reels (mur,
  personne) apparaissent bien sur `/local_costmap/costmap`.
- [ ] Envoyer un `Nav2 Goal` simple dans RViz, verifier que le robot
  planifie et suit le chemin.
- [ ] Mettre un obstacle sur le trajet : verifier que DWB devie/replanifie
  sans foncer dedans.
- [ ] Poser 2-3 waypoints via le plugin RViz *Nav2 Waypoint/Goal* et
  lancer la tournee, verifier l'enchainement.

## 5. Points a mesurer/ajuster une fois sur le vrai robot

- `robot_radius` (0.45 par defaut dans `nav2_params_b2.yaml`) — mesurer
  l'encombrement reel pattes ecartees.
- Limites de vitesse DWB (`max_vel_x/y/theta`, `acc_lim_*`) — comparer
  au comportement reel observe a l'etape 2.
- Offset physique reel du LiDAR pour la TF statique (point 0).
