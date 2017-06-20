from setuptools import find_packages, setup

setup(
    name='sanest',
    description="sane nested dictionaries and lists",
    version='0.0.1',
    packages=find_packages(where='src'),
    package_dir={"": 'src'},
    author="wouter bolsterlee",
    author_email="wouter@bolsterl.ee",
    url='https://github.com/wbolster/sanest',
    license="BSD",
)
