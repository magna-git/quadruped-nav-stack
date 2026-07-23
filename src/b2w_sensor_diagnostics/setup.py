from setuptools import find_packages, setup

package_name = 'b2w_sensor_diagnostics'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='unitree',
    maintainer_email='dia.khadijetou96@gmail.com',
    description='Read-only diagnostics for the stable B2-W stack.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'tf_diagnostics = b2w_sensor_diagnostics.tf_diagnostics:main',
        ],
    },
)
