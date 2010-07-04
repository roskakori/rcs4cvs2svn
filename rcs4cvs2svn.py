#!/usr/bin/env python
"""
rcs4cvs2svn prepares an RCS project for processing with cvs2svn.

rcs4cvs2svn is useful for developers who still have ancient source code
floating around in RCS repositories and want to move it to a modern
SCM system.

While rcs4cvs2svn does not provide any possibility to directly migrate
to any other SCM system, it creates a copy of your RCS repository that
can be processed by cvs2svn, available from <http://cvs2svn.tigris.org/>.

That way, you'll end up with a Subversion repository, which already
may be sufficient. Alternatively, Subversion offers a sound base
for further migration to another SCM such as Git or Mercurial, as most
SCM vendors provide tools to migrate from SVN but not RCS. 

(You can of course use rcs4cvs2svn as replacement for various rcs2cvs
scripts floating around. Unlike many of these scripts, 
rcs4cvs2svn can process 
filenames with space characters and handles any errors it
encounters.)

Usage
=====

Usage is simple::

  cvs -d /path/to/cvs/repository init
  python rcs4cvs2svn /path/to/rcs/project /path/to/cvs/repository

There are a couple of options, for more information run::

  python rcs4cvs2svn --help


Tutorial
========

This section describes how to migrate an RCS repository to
CSV and then to Subversion.

First, create a simple RCS repository for a project called "hello"
which contains a single file, "hello.txt" with 2 revisions::

  mkdir -p hello/RCS
  cd hello
  echo "hello world!" >hello.txt
  echo "Added greetings.\n." | ci -u hello.txt
  co -l hello.txt
  echo "hello space!" >>hello.txt
  echo "Added more greetings.\n." | ci -u hello.txt

Next, create a new CVS repository which will act as destination::

  cvs -d /tmp/hello_cvs init

Now migrate the the RCS repository to CSV.

  python rcs4cvs2svn.py hello/ /tmp/hello_cvs/

Because CVS still is a very dated way to manage a software project,
let's move on to the next step of evolution: Subversion. You will
need ``cvs2svn``, available from <http://cvs2svn.tigris.org/>.

While there are several ways to convert CVS to SVN, the easiest
for our task is to simple create a SVN dumpfile containing the
CVS as trunk::

  cvs2svn --trunk-only --dumpfile hello.dump /tmp/hello_cvs/

Now you can create a SVN repository and load the trunk into it::

  svnadmin create /tmp/hello_svn/
  svnadmin load /tmp/hello_svn/ <hello.dump

Moving on to even more advanced SCM systems is left as an
exercise to the reader.
 
License
=======

Copyright (c) 2006-2010, Thomas Aglassinger. All rights reserved.
Distributed under the BSD License.

Version information
===================

Version 1.0, 2010-07-04
-----------------------

Initial public release.

Version 0.9, 2006-05-01
-----------------------

Initial internal version used to convert some of my own projects.
"""
# Copyright (c) 2006-2010, Thomas Aglassinger
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
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Developer cheat sheet:
#
# Create the installer archive:
#
# > python setup.py sdist --formats=zip
# 
# Upload release to PyPI:
#
# > sh test_rcs4csv2svn.sh
# > python setup.py sdist --formats=zip upload
#
# Tag a release in the repository:
# > svn copy -m "Added tag for version 1.x." file:///Users/${USER}/Repositories/test_rcs4csv2svn/trunk file:///Users/${USER}/Repositories/test_rcs4csv2svn/tags/1.x

import errno
import logging
import optparse
import os.path
import shutil
import sys

log = logging.getLogger("rcs4cvs2svn")

__version__ = "1.0"

VERSION_REV, VERSION_DATE = "$Id$".split()[2:4]

def listFiles(baseDir):
    assert baseDir is not None
    result = []
    absoluteBaseDir = os.path.abspath(baseDir)
    for root, _, files in os.walk(baseDir):
        for name in files:
            absoluteFilePath = os.path.abspath(os.path.join(root, name))
            if absoluteFilePath.find(".svn") == -1:
                relativeFilePath = absoluteFilePath[len(absoluteBaseDir) + 1:]
                result.append(relativeFilePath)
    return result

def makedirs(dst):
    "Like os.makedirs(), but does not raise OSError if directory already exists."
    assert dst is not None
    try:
        os.makedirs(dst)
    except OSError, error:
        if error.errno != errno.EEXIST:
            raise

def cli():
    # Parse command line arguments.
    parser = optparse.OptionParser(
        usage = "usage: %prog [options] RCS_FOLDER CVS_FOLDER\n\nPrepare an RCS project for processing with cvs2svn.",
        version = "%prog " + __version__
    )
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="log all actions performed in console")
    (options, others) = parser.parse_args()
    if len(others) == 0:
        parser.error("RCS_FOLDER and CVS_FOLDER must be specified")
    elif len(others) == 1:
        parser.error("CVS_FOLDER must be specified")
    elif len(others) > 2:
        parser.error("unknown options must be removed: %s" % others[2:])
    rcsDir = others[0]
    flattenedDir = others[1]
    if options.verbose:
        log.setLevel(logging.DEBUG)

    rcsFiles = listFiles(rcsDir)
    copiedFileCount = 0
    for filePath in rcsFiles:
        if filePath.endswith(",v"):
            rcsFilePath = os.path.join(rcsDir, filePath)
            possibleRcsDir = os.path.split(filePath)[0]
            possibleRcsDirName = os.path.split(possibleRcsDir)[1]
            if possibleRcsDirName == "RCS":
                rcsParentDir = os.path.split(possibleRcsDir)[0]
                rcsFileName = os.path.split(rcsFilePath)[1]
                flattenedFilePath = os.path.join(flattenedDir, os.path.join(rcsParentDir, rcsFileName))
                log.debug("copy \"%s\" -> \"%s\"" %(filePath, flattenedFilePath))
                makedirs(os.path.split(flattenedFilePath)[0])
                shutil.copy(rcsFilePath, flattenedFilePath)
                copiedFileCount += 1
    log.info("migrated %d files from \"%s\" to \"%s\"" %(copiedFileCount, rcsDir, flattenedDir))

if __name__ == "__main__":
    # Set up logging.
    logging.basicConfig()
    log.setLevel(logging.INFO)
    exitCode = 1
    try:
        cli()
        exitCode = 0
    except EnvironmentError, error:
        log.error(error)
    except Exception, error:
        log.exception(error)
    sys.exit(exitCode)
