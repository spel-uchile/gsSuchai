import os
from distutils.core import setup

version = "0.0.0"
with open(os.path.join("config", "version.txt")) as ver_file:
    version = ver_file.readline()[:-1]

setup(
    name='groundstation',
    version=version,
    url='https://github.com/carlgonz/SerialCommander',
    license='GPL v3',
    author='Carlos Gonzalez',
    author_email='carlgonz@uchile.cl',
    description='Ground segment software to control the SUCHAI satellite',
    packages=['forms'],
    py_modules=['groundstation', "client", "telemetry"],
    scripts=['groundstation.py', ],
    include_package_data=True,
    install_requires=["numpy", "pandas", "pyzmq", "pymongo"],
    data_files=[('share/groundstation/', ['config/config.json']),
                ('share/groundstation/', ['config/version.txt']),
                ('share/groundstation/', ['config/cmd_list.txt']),
                ('share/groundstation/', ['forms/spel_icon.png']),
                ('share/applications', ['org.spel.groundstation.desktop'])]
)
