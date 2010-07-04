#!/bin/sh

# Cleanup everything left from previous runs.
rm -rfv hello hello_rcs /tmp/hello_cvs /tmp/hello_svn

# Create a simple RCS repository.
mkdir -p hello/RCS
cd hello
echo "hello world!" >hello.txt
echo "Added greetings.\n." | ci -u hello.txt
co -l hello.txt
echo "hello space!" >>hello.txt
echo "Added more greetings.\n." | ci -u hello.txt

# Create CVS repository (requires an absolute path).
cvs -d /tmp/hello_cvs init

# Migrate RCS to CSV.
python rcs4cvs2svn.py hello/ /tmp/hello_cvs/

# Migrate RCS to SVN dump.
cvs2svn --trunk-only --dumpfile hello.dump /tmp/hello_cvs/

# Import SNV dump into SVN repository.
svnadmin create /tmp/hello_svn/
svnadmin load /tmp/hello_svn/ <hello.dump

if [ $? -eq 0 ];then
   echo "Ok, test repository migrated"
else
   echo "*** ERROR: see above for details"
fi
