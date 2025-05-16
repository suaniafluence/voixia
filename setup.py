# setup.py
from setuptools import setup, find_packages

setup(
    name='voixia',
    version='0.1.0',
    packages=find_packages(exclude=['tests*']),
    install_requires=[
        # Répétez ici les dépendances principales si vous le souhaitez,
        # ou laissez vide si vous vous fiez à requirements.txt
    ],
)
