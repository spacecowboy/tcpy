#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script for triggering personal builds on TeamCity.  Specify `-h` with a
specific sub command for more specific help.
"""

from __future__ import print_function
import requests as r
from argparse import ArgumentParser
import sys

try:
    import urlparse
except ImportError:
    # Renamed in Python3
    from urllib import parse as urlparse


# Some constants #

# Want to request json from the server
_headers = {'Accept': 'application/json',
            'Content-Type': 'application/xml'}

_requestbase = """
<build personal="true" branchName="{branch}">
  <buildType id="{buildid}"/>
  <comment><text>Triggered from CLI</text></comment>
  <properties>
    <property name="remote" value="{remote}"/>
    <property name="branch" value="{branch}"/>{props}
  </properties>
</build>
"""

_requestpropertybase = '\n    <property name="{name}" value="{value}"/>'

_neo4jlinux_id = "JonasHaRequests_Neo4jCustom"

_linux_jdks = ['openjdk-8', 'openjdk-7',
               'oracle-jdk-8', 'oracle-jdk-7',
               'ibmjdk-8', 'ibmjdk-7']

# End constants #


def dict_as_properties(props):
    """
    Format a dictionary as xml property tags:

        <property name=NAME value=VALUE />

    """
    xml = ""
    for k, v in props.items():
        xml += _requestpropertybase.format(name=k, value=v)
    return xml


def request_xml(buildid, branch, remote, props):
    """
    Format an XML build request
    """
    return _requestbase.format(buildid=buildid,
                               remote=remote,
                               branch=branch,
                               props=props)


def send_request(user, password, url, data):
    """
    Start a build, defined in data
    """
    resp = r.post(urlparse.urljoin(url, "httpAuth/app/rest/buildQueue"),
                  auth=(user, password),
                  headers=_headers,
                  data=data)

    if resp.ok:
        print("Build started. View status at")
        print(resp.json().get('webUrl'))
    else:
        print("Could not start build:")
        print(resp.status_code)
        try:
            print(resp.json())
        except:
            print(resp.text)
        exit(1)


def tc_mvn_args(original):
    """
    Add some useful maven arguments in TC
    """
    return "-DfailIfNoTests=false -Dmaven.test.failure.ignore=true --show-version " + original


def start_linux(user, password, url, branch, remote, mvngoals, mvnargs, jdk):
    """
    Start a custom linux build
    """
    props = dict_as_properties({'project-default-jdk': "%{}%".format(jdk),
                                'maven-goals': mvngoals,
                                'maven-args': mvnargs})
    data = request_xml(_neo4jlinux_id, branch, remote, props)
    send_request(user, password, url, data)


def main(cliargs):
    """
    Parse the command line arguments and provide help for the user.
    """
    mainparser = ArgumentParser(epilog=__doc__)
    # Use a subcommand for each build configuration
    subparsers = mainparser.add_subparsers(title='build types', dest='subcmd')

    # All builds share teamcity information
    _parserbase = ArgumentParser(add_help=False)
    _required = _parserbase.add_argument_group('mandatory arguments')
    _required.add_argument('-u', '--user', metavar='USERNAME',
                           help='TeamCity username', required=True)
    _required.add_argument('-p', '--password',
                           help='TeamCity password', required=True)
    _required.add_argument('-b', '--branch',
                           help='Branch on remote to checkout', required=True)
    _parserbase.add_argument('-r', '--remote', metavar='URL',
                             help='Public remote repo where branch exists',
                             default='origin')
    _parserbase.add_argument('--teamcity', metavar='URL',
                             help='Url to TeamCity',
                             default='https://build.neohq.net')

    # All Neo4j builds share some obvious arguments
    _neo4jparserbase = ArgumentParser(add_help=False)
    _neo4jparserbase.add_argument('--maven-goals', metavar='GOALS',
                                  help='Maven goal(s) to invoke',
                                  default='clean verify')
    _neo4jparserbase.add_argument('--maven-args', metavar='ARGS',
                                  help='Additional Maven arguments',
                                  default='-DrunITs -DskipBrowser')

    # Linux
    linuxparser = subparsers.add_parser('linux', help='Neo4j Linux',
                                        parents=[_parserbase,
                                                 _neo4jparserbase])
    linuxparser.add_argument('--jdk', help='JDK to build with',
                             default=_linux_jdks[0], choices=_linux_jdks)

    # Parse the arguments given
    args = mainparser.parse_args(cliargs)

    # Select action based on sub command
    if args.subcmd is None:
        mainparser.print_help()
        exit()
    elif args.subcmd == "linux":
        start_linux(args.user, args.password, args.teamcity,
                    args.branch, args.remote,
                    args.maven_goals,
                    tc_mvn_args(args.maven_args),
                    args.jdk)


if __name__ == "__main__":
    main(sys.argv[1:])
