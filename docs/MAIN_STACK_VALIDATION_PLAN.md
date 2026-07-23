# Main Stack Validation Plan

## Objectif

Valider sur le B2-W le pipeline stable:

`/rslidar_points -> pointcloud_to_laserscan -> /scan_synced -> slam_toolbox -> map -> amcl -> nav2 -> /cmd_vel -> quadruped_adapter`

## Protocole Materiel

1. Charger l'environnement
   - `cd /home/unitree/unified_nav_ws`
   - `source /opt/ros/humble/setup.bash`
   - `source install/setup.bash`
   - `source scripts/setup_env.sh`

2. Verification perception seule
   - `ros2 launch quadruped_bringup sensors.launch.py robot:=b2`
   - verifier `/rslidar_points`, `/scan`, `/scan_synced`, `/dog_odom`
   - lancer `ros2 run quadruped_slam scan_diagnostics`
   - lancer `ros2 run b2w_sensor_diagnostics tf_diagnostics`

3. Validation mapping
   - `ros2 launch quadruped_slam mapping.launch.py robot:=b2`
   - dans RViz, verifier TF, `/scan_synced`, `/map`, `/dog_odom`
   - deplacer le robot en teleop seulement apres verification visuelle
   - verifier que `map -> odom` reste stable et que la carte se construit

4. Sauvegarde carte
   - `./scripts/save_map.sh b2w_office`
   - verifier la creation de `maps/b2w_office.yaml` et `maps/b2w_office.pgm`

5. Validation localisation
   - `ros2 launch quadruped_nav2 localization.launch.py map:=/home/unitree/unified_nav_ws/maps/b2w_office.yaml robot:=b2`
   - dans RViz, utiliser `2D Pose Estimate`
   - verifier que le scan s'aligne avec la carte

6. Validation navigation
   - `ros2 launch quadruped_nav2 navigation.launch.py map:=/home/unitree/unified_nav_ws/maps/b2w_office.yaml robot:=b2`
   - verifier presence des actions Nav2
   - verifier `/cmd_vel` et `robot_adapter`
   - envoyer un goal court dans un espace degage
   - valider ensuite un petit jeu de waypoints

7. Validation hors mouvement
   - `./scripts/validate_main_stack.sh`

## Criteres D'Acceptation

- TF complet: `map -> odom -> robot_center -> {rslidar, dog_imu_link}`
- `/scan_synced` stable et cohérent avec la carte
- sauvegarde de carte reproductible
- localisation AMCL re-alignable via `2D Pose Estimate`
- Nav2 capable d'atteindre un goal simple
- `/cmd_vel` coherent et borne avant mouvement reel
