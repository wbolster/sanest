import os.path

from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as fp:
    long_description = fp.read()

setup(
    name='sanest',
    version='0.0.1',
    description="sane nested dictionaries and lists",
    long_description=long_description,
    author="wouter bolsterlee",
    author_email="wouter@bolsterl.ee",
    url='https://github.com/wbolster/sanest',
    packages=find_packages(where='src'),
    package_dir={"": 'src'},
    license="BSD",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
