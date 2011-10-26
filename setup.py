"""
Installer for rcs4csv2svn.
"""
from distutils.core import setup

import rcs4cvs2svn

setup(
    name="rcs4cvs2svn",
    version=rcs4cvs2svn.__version__,
    py_modules=["rcs4cvs2svn", "test_rcs4cvs2svn"],
    description="prepare RCS project for processing with cvs2svn",
    keywords="rcs cvs svn convert migrate import",
    author="Thomas Aglassinger",
    author_email="roskakori@users.sourceforge.net",
    url="http://pypi.python.org/pypi/rcs4cvs2svn/",
    license="BSD License",
    long_description=rcs4cvs2svn.__doc__,  # @UndefinedVariable
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Version Control :: RCS",
    ],
)
