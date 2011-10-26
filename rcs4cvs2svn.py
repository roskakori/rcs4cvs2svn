#!/usr/bin/env python
"""
rcs4cvs2svn prepares an RCS project for processing with cvs2svn.

rcs4cvs2svn is useful for developers who still have ancient source code
floating around in RCS repositories and want to move it to a modern SCM system.

While rcs4cvs2svn does not provide any possibility to directly migrate to any
other SCM system, it creates a copy of your RCS repository that can be
processed by `cvs2svn <http://cvs2svn.tigris.org/>`_.

That way, you'll end up with a Subversion repository, which already may be
sufficient. Alternatively, Subversion offers a sound base for further migration
to another SCM such as Git or Mercurial, as most SCM vendors provide tools to
migrate from SVN but not from RCS.

(You can of course use rcs4cvs2svn as replacement for various rcs2cvs scripts
floating around. Unlike many of these scripts, rcs4cvs2svn can process
filenames with space characters and handles any errors it encounters.)


Usage
=====

Usage is simple::

  $ python rcs4cvs2svn.py /path/to/rcs/project /path/to/cvs/repository

There are a couple of options, for more information run::

  $ python rcs4cvs2svn.py --help


Tutorial
========

This section describes how to migrate an RCS repository to
CVS and then to Subversion.

First, create a simple RCS repository for a project called "hello" which
contains a single file, "hello.txt" with 2 revisions::

  $ mkdir -p hello/RCS
  $ cd hello
  $ echo "hello world!" >hello.txt
  $ echo "Added greetings.\\n." | ci -u hello.txt
  $ co -l hello.txt
  $ echo "hello space!" >>hello.txt
  $ echo "Added more greetings.\\n." | ci -u hello.txt

Now migrate the the RCS repository to CVS::

  $ python rcs4cvs2svn.py hello/ /tmp/hello_cvs/

The output should be::

  INFO:rcs4cvs2svn:create new CVS repository at "/tmp/hello_cvs/"
  INFO:rcs4cvs2svn:migrated 1 files from "hello/" to "/tmp/hello_cvs/"

Because CVS still is a very dated way to manage a software project, let's move
on to the next step of evolution: Subversion. You will need ``cvs2svn``,
available from <http://cvs2svn.tigris.org/>.

While there are several ways to convert CVS to SVN, the easiest for our task is
to simple create a SVN dumpfile containing the CVS as trunk::

  $ cvs2svn --trunk-only --dumpfile hello.dump /tmp/hello_cvs/

Now you can create a SVN repository and load the trunk into it::

  $ svnadmin create /tmp/hello_svn/
  $ svnadmin load /tmp/hello_svn/ <hello.dump

Moving on to even more advanced SCM systems is left as an exercise to the
reader.


License
=======

Copyright (c) 2006-2011, Thomas Aglassinger. All rights reserved. Distributed
under the `BSD License <http://www.opensource.org/licenses/bsd-license.php>`_.


Source code
===========

The source code is available from <https://github.com/roskakori/rcs4cvs2svn>.


Version information
===================

**Version 1.2, 2011-10-26**

* Fixed logging which could cause issues with file names containing non ASCII
  characters or percent signs (%).
* Improved handling of CVS target folder, which can now be a relative folder
  even though ``csv init`` expects an absolute folder.
* Improved API: Added ``rcs4cvs2svn.main()``, which can be called from Python
  similar to the command line.
* Changed test shell scripts to proper unit test.
* Cleaned up PEP8 issues.

**Version 1.1, 2010-07-06**

* Added automatic creation of CVS repository in case the target path does
  not already contain a ``CVSROOT`` folder. In order for this to work, the
  ``cvs`` command line client has  to be installed.
* Fixed protection bits in CVS which were copied from RCS and did make the
  files write protected (which was not an issue for converting to SVN but
  forced the user to remove the CVS for repeated conversion).
* Cleaned up API. Simply ``import rcs4cvs2svn`` and call
  ``initCvsRepository()`` and ``convertRcsToCvs()`` as needed.

**Version 1.0, 2010-07-04**

* Initial public release.

**Version 0.9, 2006-05-01**

* Initial internal version used to convert some of my own projects.
"""
# Copyright (c) 2006-2011, Thomas Aglassinger
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * Neither the name of Thomas Aglassinger nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# **Developer cheat sheet**
#
# Create the installer archive::
#
# $ python setup.py sdist --formats=zip
#
# Upload release to PyPI::
#
# $ python test_rcs4cvs2svn.py
# $ pep8 --repeat *.py
# $ python setup.py sdist --formats=zip upload
#
# Tag a release in the repository::
#
# $ git tag -a -m "Tagged version 1.x." 1.x
# $ git push --tags

import errno
import logging
import optparse
import os.path
import shutil
import subprocess
import sys

log = logging.getLogger("rcs4cvs2svn")

__version__ = "1.2"


def _listFiles(folderToListPath):
    assert folderToListPath is not None

    result = []
    absoluteBaseDir = os.path.abspath(folderToListPath)
    for root, _, files in os.walk(folderToListPath):
        for name in files:
            absoluteFilePath = os.path.abspath(os.path.join(root, name))
            if absoluteFilePath.find(".svn") == -1:
                relativeFilePath = absoluteFilePath[len(absoluteBaseDir) + 1:]
                result.append(relativeFilePath)
    return result


def _makedirs(folderToCreatePath):
    """
    Like ``os.makedirs()``, but does not raise OSError if directory already
    exists.
    """
    assert folderToCreatePath is not None

    try:
        os.makedirs(folderToCreatePath)
    except OSError, error:
        if error.errno != errno.EEXIST:
            raise


def initCvsRepository(cvsTargetFolderPath):
    """
    Check that ``cvsTargetFolderPath`` is a path to a CVS repository and if
    not, call the ``csv`` command line client to create one.
    """
    assert cvsTargetFolderPath is not None

    absoluteCvsTargetFolderPath = os.path.abspath(cvsTargetFolderPath)
    cvsRootPath = os.path.join(absoluteCvsTargetFolderPath, "CVSROOT")
    if not os.path.exists(cvsRootPath):
        log.info(u"create new CVS repository at \"%s\"",
            absoluteCvsTargetFolderPath)
        subprocess.check_call([
            "cvs", "-d", absoluteCvsTargetFolderPath, "init"
        ])


def convertRcsToCvs(rcsSourceFolderPath, cvsTargetFolderPath):
    """
    Convert source code in RCS repository  ``rcsSourceFolderPath`` to
    existing CVS repository at ``cvsTargetFolderPath``.
    """
    assert rcsSourceFolderPath is not  None
    assert cvsTargetFolderPath is not None

    rcsFiles = _listFiles(rcsSourceFolderPath)
    copiedFileCount = 0
    for filePath in rcsFiles:
        if filePath.endswith(",v"):
            rcsFilePath = os.path.join(rcsSourceFolderPath, filePath)
            possibleRcsDir = os.path.split(filePath)[0]
            possibleRcsDirName = os.path.split(possibleRcsDir)[1]
            if possibleRcsDirName == "RCS":
                rcsParentDir = os.path.split(possibleRcsDir)[0]
                rcsFileName = os.path.split(rcsFilePath)[1]
                flattenedFilePath = os.path.join(
                    cvsTargetFolderPath,
                    os.path.join(rcsParentDir, rcsFileName)
                )
                log.debug(u"copy \"%s\" -> \"%s\"",
                    filePath, flattenedFilePath)
                _makedirs(os.path.split(flattenedFilePath)[0])
                # Copy file without permission bits.
                shutil.copyfile(rcsFilePath, flattenedFilePath)
                copiedFileCount += 1
    log.info(
        u"migrated %d files from \"%s\" to \"%s\"",
        copiedFileCount, rcsSourceFolderPath, cvsTargetFolderPath
    )


def _parsedOptions(arguments):
    assert arguments is not None

    # Parse command line options.
    Usage = """usage: %prog [options] RCS_FOLDER CVS_FOLDER

    Prepare an RCS project for processing with cvs2svn."""
    parser = optparse.OptionParser(
        usage=Usage,
        version="%prog " + __version__
    )
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="log all actions performed in console")
    (options, others) = parser.parse_args(arguments)
    if len(others) == 0:
        parser.error("RCS_FOLDER and CVS_FOLDER must be specified")
    elif len(others) == 1:
        parser.error("CVS_FOLDER must be specified")
    elif len(others) > 2:
        parser.error("unknown options must be removed: %s" % others[2:])
    if options.verbose:
        log.setLevel(logging.DEBUG)

    rcsSourceFolderPath = others[0]
    cvsTargetFolderPath = others[1]

    return rcsSourceFolderPath, cvsTargetFolderPath


def main(argv=None):
    if argv is None:
        argv = sys.argv

    exitCode = 1
    try:
        rcsSourceFolderPath, cvsTargetFolderPath = _parsedOptions(argv[1:])
        initCvsRepository(cvsTargetFolderPath)
        convertRcsToCvs(rcsSourceFolderPath, cvsTargetFolderPath)
        exitCode = 0
    except (EnvironmentError, subprocess.CalledProcessError), error:
        log.error(error)
    except KeyboardInterrupt:
        log.warning(u"interrupted by user")
    except Exception, error:
        log.exception(error)
    return exitCode

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
