"""
Tests for rcs4cvs2svn
"""
import logging
import os.path
import shutil
import subprocess
import unittest

import rcs4cvs2svn

_HelloFolderPath = "hello"
_HelloTxt = "hello.txt"
_HelloTxtPath = os.path.join(_HelloFolderPath, _HelloTxt)
_HelloCvsFolderPath = "hello_cvs"
_HelloRcsFolderPath = "hello_rcs"
_HelloSvnFolderPath = "hello_svn"
_HelloDumpPath = "hello.dump"
_SvnListPath = "svn-list.txt"


def _writeTo(targetPath, linesToWrite):
    assert targetPath is not None
    assert linesToWrite is not None
    with open(targetPath, "w") as targetFile:
        for line in linesToWrite:
            targetFile.write(line)
            targetFile.write(os.linesep)


class Rcs4Csv2SvnTest(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(_HelloFolderPath, ignore_errors=True)
        os.mkdir(_HelloFolderPath)
        shutil.rmtree(_HelloRcsFolderPath, ignore_errors=True)
        os.mkdir(_HelloRcsFolderPath)
        self._messagePath = "test_rcs4cvs2svn_message.txt"
        shutil.rmtree(_HelloCvsFolderPath, ignore_errors=True)
        shutil.rmtree(_HelloSvnFolderPath, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(self._messagePath, ignore_errors=True)

    def _writeMessage(self, linesToWrite):
        assert linesToWrite is not None
        actualLinesToWrite = list(linesToWrite)
        actualLinesToWrite.append(".")
        _writeTo(self._messagePath, actualLinesToWrite)

    def _buildTestRcsRepository(self):
        shutil.rmtree(_HelloFolderPath, ignore_errors=True)
        os.mkdir(_HelloFolderPath)
        os.mkdir(os.path.join(_HelloFolderPath, "RCS"))
        oldCurrentFolder = os.getcwdu()
        os.chdir(_HelloFolderPath)
        try:
            # Create a simple RCS repository.
            _writeTo(_HelloTxt, ["hello world."])
            self._writeMessage(["Added greetings."])
            with open(self._messagePath, "r") as messageFile:
                exitCode = subprocess.call(
                    ["ci", "-u", os.path.basename(_HelloTxtPath)],
                    stdin=messageFile
                )
            self.assertEqual(exitCode, 0)

            exitCode = subprocess.call([
                "co", "-l", os.path.basename(_HelloTxtPath)
            ])
            self.assertEqual(exitCode, 0)

            _writeTo(_HelloTxt, ["hello world.", "hello space."])
            self._writeMessage(["Added more greetings."])
            with open(self._messagePath, "r") as messageFile:
                exitCode = subprocess.call(
                    ["ci", "-u", os.path.basename(_HelloTxtPath)],
                    stdin=messageFile
                )
            self.assertEqual(exitCode, 0)
        finally:
            os.chdir(oldCurrentFolder)

    def _buildAndMigrateTestRcsToCsv(self):
        self._buildTestRcsRepository()
        rcs4cvs2svn.initCvsRepository(_HelloCvsFolderPath)
        rcs4cvs2svn.convertRcsToCvs(_HelloFolderPath, _HelloCvsFolderPath)

    def _removeTestRcsAndCvs(self):
        shutil.rmtree(_HelloFolderPath)
        shutil.rmtree(_HelloRcsFolderPath)
        shutil.rmtree(_HelloCvsFolderPath)

    def testCanMigrateRcsToCvs(self):
        self._buildAndMigrateTestRcsToCsv()
        self._removeTestRcsAndCvs()

    def testCanMigrateRcsToSvn(self):
        # Note: In order for this test to work, subversion and cvs2svn must be
        # installed.

        self._buildAndMigrateTestRcsToCsv()

        # Build svn dump file.
        subprocess.check_call([
            "cvs2svn",
            "--trunk-only",
            "--dumpfile",
            _HelloDumpPath,
            _HelloCvsFolderPath
        ])

        # Create a local svn repository and import the dump.
        subprocess.check_call(["svnadmin", "create", _HelloSvnFolderPath])
        with open(_HelloDumpPath, "rb") as helloDumpFile:
            subprocess.check_call(
                ["svnadmin", "load", _HelloSvnFolderPath],
                stdin=helloDumpFile
            )

        # Assert that trunk contains all files committed by RCS.
        with open(_SvnListPath, "w") as svnListFile:
            # FIXME: Find and use some "path2url" function in standard API.
            trunkUrl = u"file://localhost%s" \
                % os.path.join(os.path.abspath(_HelloSvnFolderPath), "trunk")
            subprocess.check_call(
                ["svn", "list", trunkUrl],
                stdout=svnListFile
            )
        expectedFilePathsInTrunk = {
            "CVSROOT": False,
            "hello.txt": False
        }
        with open(_SvnListPath, "r") as svnListFile:
            for filePathToCheck in svnListFile:
                filePathToCheck = filePathToCheck.rstrip("\n\r\\/")
                self.assertTrue(
                    filePathToCheck in expectedFilePathsInTrunk,
                    "unexpected file in trunk: %r" % filePathToCheck
                )
                expectedFilePathsInTrunk[filePathToCheck] = True
        for filePathToCheck, found in expectedFilePathsInTrunk.items():
            self.assertTrue(
                found,
                "file must be found in trunk: %r" % filePathToCheck
            )

        # Clean up.
        shutil.rmtree(_HelloFolderPath)
        shutil.rmtree(_HelloRcsFolderPath)
        shutil.rmtree(_HelloCvsFolderPath)
        shutil.rmtree(_HelloSvnFolderPath)
        os.remove(_HelloDumpPath)
        os.remove(_SvnListPath)

    def testCanMigrateRcsToCvsUsingMain(self):
        self._buildTestRcsRepository()
        exitCode = rcs4cvs2svn.main([
            os.path.basename(__file__),
            _HelloFolderPath,
            _HelloCvsFolderPath
        ])
        self.assertEqual(exitCode, 0)
        self._removeTestRcsAndCvs()

    def testCanMigrateRcsToCvsUsingMainWithVerboseLogging(self):
        self._buildTestRcsRepository()
        exitCode = rcs4cvs2svn.main([
            os.path.basename(__file__),
            "--verbose",
            _HelloFolderPath,
            _HelloCvsFolderPath
        ])
        self.assertEqual(exitCode, 0)
        self._removeTestRcsAndCvs()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    unittest.main()
