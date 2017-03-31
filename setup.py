from setuptools import setup, find_packages
import os

setup_dir = os.path.dirname(__file__)
readme_path = os.path.join(setup_dir, 'README.rst')
version_path = os.path.join(setup_dir, 'logbeam/version.py')
requirements_path = os.path.join(setup_dir, "requirements.txt")
requirements_dev_path = os.path.join(setup_dir, "requirements-dev.txt")

__version__ = None
with open(version_path) as f:
    code = compile(f.read(), version_path, 'exec')
    exec(code)

with open(readme_path) as readme_file:
    readme = readme_file.read()

with open(requirements_path) as req_file:
    requirements = req_file.read().splitlines()

with open(requirements_dev_path) as req_file:
    requirements_dev = req_file.read().splitlines()

setup(
    name='logbeam',
    version=__version__,
    author='Nicholas Robinson-Wall',
    author_email='nick@robinson-wall.com',
    packages=find_packages(),
    url='https://github.com/osperlabs/logbeam',
    description='CloudWatch Logs - Python logging handler',
    long_description=readme,
    install_requires=requirements,
    tests_require=requirements_dev,
    package_data={'logbeam': ['requirements.txt', 'requirements-dev.txt']},
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Logging',
    ],
)
