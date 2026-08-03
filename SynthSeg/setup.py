#!/usr/bin/env python

import sys
import os
import setuptools

python_version = sys.version[:3]

# Support Python 3.6, 3.8, 3.9, 3.10, 3.11, 3.12
if python_version not in ['3.6', '3.8', '3.9']:
    print(f'Warning: This package is tested on Python 3.6 and 3.8, you are using {python_version}')
    print('Using requirements for Python 3.8...')
    python_version = '3.8'

requirements_file = 'requirements_python' + python_version + '.txt'

# Fallback to 3.8 requirements if specific version not found
if not os.path.exists(requirements_file):
    print(f'Requirements file {requirements_file} not found, using requirements_python3.8.txt')
    requirements_file = 'requirements_python3.8.txt'

with open(requirements_file) as f:
    required_packages = [line.strip() for line in f.readlines()]

print(setuptools.find_packages())

setuptools.setup(name='SynthSeg',
                 version='2.0',
                 license='Apache 2.0',
                 description='Domain-agnostic segmentation of brain scans',
                 author='Benjamin Billot',
                 url='https://github.com/BBillot/SynthSeg',
                 keywords=['segmentation', 'domain-agnostic', 'brain'],
                 packages=setuptools.find_packages(),
                 python_requires='>=3.6',
                 install_requires=required_packages,
                 include_package_data=True)
