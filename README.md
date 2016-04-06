Script for triggering personal builds on TeamCity. The program's help
strings are quite complete, so just do

    tc.py -h

to see what sub commands you can call. For more specfic help, just do

    tc.py {subcommand} -h

To install easily, you can do this:

    pip install git+https://github.com/spacecowboy/tcpy.git

## Some examples

These might become outdated, but should serve as inspiration.

### Running the most basic linux build with default settings

    tc.py -u XXX -p YYY --branch 3.1

### Run linux on an IBM JDK

    tc.py -u XXX -p YYY --branch 3.1 --jdk ibmjdk-8

### Only compile, don't do tests

    tc.py -u XXX -p YYY --branch 3.1 --maven-goals "clean compile"

### Quick feedback, build only what's necessary to run a single specific test

    tc.py -u XXX -p YYY --branch 3.0 --maven-args "-Dtest=MuninnPageCacheWithAdversarialFileDispatcherIT -pl :neo4j-io -am"

### Run with defaults, but checkout the branch from your own repo

    tc.py -u XXX -p YYY --branch flakytest --remote https://github.com/spacecowboy/neo4j.git
