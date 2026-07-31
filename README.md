# quadruped-nav-stack

## Description du projet

`quadruped-nav-stack` est un workspace ROS 2 Humble pour la perception, la
cartographie SLAM, la localisation et la navigation de robots quadrupèdes. Le
cœur du stack est générique : un robot est intégré par configuration, sans
créer de branche dédiée.

## Branches `main` et `refactor/reorganize-repository`

- `main` conserve la première version et son ancienne organisation.
- `refactor/reorganize-repository` porte la nouvelle architecture générique,
  organisée en packages ROS 2 et pilotée par des profils robots.

Les évolutions propres à un robot doivent rester dans les profils,
configurations et adapters prévus à cet effet, et non dans des branches Go2,
B2 ou D1.

## Architecture générale

```text
src/
├── quadruped_bringup/   # Capteurs, TF, SLAM, profils et cartes
├── quadruped_nav2/      # Localisation et navigation Nav2
└── quadruped_adapter/   # Interface entre /cmd_vel et le SDK constructeur
scripts/
├── dds/                 # Configuration CycloneDDS
└── env/                 # Initialisation de l'environnement
```

Le cœur du stack est générique. Les différences entre robots sont isolées
dans :

- `src/quadruped_bringup/profiles/<robot>.yaml` pour les topics, frames et
  limites du robot ;
- `src/quadruped_bringup/config/slam_config_<robot>.yaml` pour SLAM Toolbox ;
- l'adapter spécifique au constructeur, qui traduit `/cmd_vel` vers son SDK.

Les paramètres Nav2 propres au robot suivent le même identifiant dans
`src/quadruped_nav2/config/nav2_params_<robot>.yaml`.

## Installation

Installer ROS 2 Humble, créer ou ouvrir ce workspace, puis installer les
dépendances déclarées par les packages :

```bash
rosdep install --from-paths src --ignore-src -r -y
```

Le SDK Unitree 2 doit être installé séparément. Indiquer son emplacement avant
la compilation (le chemin par défaut est `$HOME/unitree_sdk2`) :

```bash
export UNITREE_SDK_DIR=$HOME/unitree_sdk2
```

Il est aussi possible de le fournir directement à CMake avec
`--cmake-args -DUNITREE_SDK_DIR=/path/to/unitree_sdk2` lors du build `colcon`.

Les principales dépendances système sont aussi récapitulées dans
`requirements.txt`.

## Compilation

```bash
colcon build --symlink-install
```

## Source

Dans chaque nouveau terminal :

```bash
source install/setup.bash
```

## Sélection d'un robot

Le paramètre de launch `robot` sélectionne les fichiers portant le même
identifiant. Par exemple :

```bash
ros2 launch quadruped_bringup mapping.launch.py robot:=b2
ros2 launch quadruped_nav2 navigation.launch.py robot:=b2
```

Pour utiliser un profil existant différent, remplacer `b2` par son identifiant
(par exemple `d1`). Le profil, la configuration SLAM correspondante et
l'adapter constructeur doivent être disponibles ; aucune branche robot n'est
nécessaire.
