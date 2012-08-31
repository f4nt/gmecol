#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages


install_requires = [
]

setup(
    name='gmecol',
    version='0.1',
    author='Mark Rogers',
    author_email='xxf4ntxx@gmail.com',
    url='http://github.com/f4nt/gmecol',
    description = 'Game Cataloging Software',
    packages=find_packages(),
    zip_safe=False,
    install_requires=install_requires,
    include_package_data=True,
    entry_points = {},
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
)
