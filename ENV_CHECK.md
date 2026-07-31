# Validation de l'environnement

Effectuer ces contrôles dans le terminal qui servira à lancer le stack.

## ROS

```bash
echo $ROS_DISTRO
```

La valeur attendue pour ce dépôt est `humble`.

## DDS

```bash
echo $RMW_IMPLEMENTATION
```

La valeur attendue est `rmw_cyclonedds_cpp` après chargement de
`scripts/env/setup_robot_internal.sh`.

## Réseau

```bash
ip -br addr
```

Vérifier que l'interface configurée dans le fichier CycloneDDS est active et
possède une adresse sur le réseau du robot.

## Découverte ROS

```bash
ros2 topic list
```

Vérifier que les topics attendus du robot et du stack sont découverts.

## TF

```bash
ros2 run tf2_tools view_frames
```

Ouvrir le graphe généré et vérifier que la chaîne suivante est complète et
continue :

```text
map
 |
odom
 |
base_link
```
