from setuptools import setup, find_packages

setup(
    name = 'autodse',
    version = '0.1',
    keywords='merlin autodse',
    description = 'Automated design space exploration for the Merlin compiler',
    license = 'Falcon License',
    url = 'https://github.com/falcon-computing/Merlin_DSE',
    author = 'Falcon Computing Solutions, Inc',
    author_email = '',
    packages = find_packages(),
    include_package_data = True,
    platforms = 'any',
    install_requires = [],
)