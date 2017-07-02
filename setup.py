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
