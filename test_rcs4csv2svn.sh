#!/bin/sh

# Cleanup everything left from previous runs.
rm -rfv hello hello_rcs /tmp/hello_cvs /tmp/hello_svn
if [ $? -ne 0 ];then
   echo "*** ERROR: see above for details"
   exit 1
fi

# Create a simple RCS repository.
mkdir -p hello/RCS
cd hello
echo "hello world!" >hello.txt
echo "Added greetings.\n." | ci -u hello.txt
co -l hello.txt
echo "hello space!" >>hello.txt
echo "Added more greetings.\n." | ci -u hello.txt

# Migrate RCS to CSV.
cd ..
python ./rcs4cvs2svn.py hello/ /tmp/hello_cvs/
if [ $? -ne 0 ];then
   echo "*** ERROR: see above for details"
   exit 1
fi

# Migrate RCS to SVN dump.
cvs2svn --trunk-only --dumpfile hello.dump /tmp/hello_cvs/
if [ $? -ne 0 ];then
   echo "*** ERROR: see above for details"
   exit 1
fi

# Import SNV dump into SVN repository.
svnadmin create /tmp/hello_svn/
svnadmin load /tmp/hello_svn/ <hello.dump
if [ $? -ne 0 ];then
   echo "*** ERROR: see above for details"
   exit 1
fi
