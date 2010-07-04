#!/usr/bin/env python
"""rcs4cvs2svn.py -- Prepare RCS project for cvs2svn."""

import errno
import getopt
import logging
import os
import os.path
import shutil
import sys

log = logging.getLogger("rcs4cvs2svn")

def listFiles(baseDir):
  assert baseDir is not None
  result = []
  absoluteBaseDir = os.path.abspath(baseDir)
  for root, dirs, files in os.walk(baseDir):
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
            raise error

def cli():
    # Set up logging.
    logging.basicConfig()
    log.setLevel(logging.INFO)

    # Parse command line arguments.
    options, others =  getopt.getopt(sys.argv[1:], "v", ["verbose"])
    if len(others) != 2:
        errorMessage = "<rcs source path> and <cvs target path> must be specified, but there where: " + str(others)
        raise getopt.GetoptError(errorMessage, others)
    rcsDir = others[0]
    flattenedDir = others[1]
    for option, value in options:
        if option in ("--verbose", "-v"):
            log.setLevel(logging.DEBUG)
        else:
            assert False, "option must be implemented: " + option

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
    cli()

