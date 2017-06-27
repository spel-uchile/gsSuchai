from distutils.core import setup

setup(
    name='groundstation',
    version='0.4.3',
    url='https://github.com/carlgonz/SerialCommander',
    license='GPL v3',
    author='Carlos Gonzalez',
    author_email='contacto.carlosgonzalezqgmail.com',
    description='A simple serial interface to send commands',

    packages=['forms'],
    py_modules=['groundstation', "client", "telemetry"],
    scripts=['groundstation.py', ],
    include_package_data=True,
    install_requires=["pyzmq", "pymongo"],
    data_files=[('share/groundstation/', ['config/config.json']),
                ('share/groundstation/', ['config/cmd_list.txt']),
                ('share/groundstation/', ['forms/spel_icon.png']),
                ('share/applications', ['org.spel.groundstation.desktop'])]
)
