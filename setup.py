from setuptools import setup, find_packages
setup(
    name="linkapp.readinglist",
    version="0.1",
    packages=["linkapp.readinglist"],
    install_requires=['redis', 'pika', 'strict_rfc3339', 'requests', 'webob']
)