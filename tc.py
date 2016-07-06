#!/usr/bin/env python
# -*- coding: utf-8 -*-
# PYTHON_ARGCOMPLETE_OK
"""
tc.py <command> [<args>]

Where command is the type of build you with to invoke:
    linux        Neo4j Linux
    har          HA Robustness
"""
# StdLib imports first
from __future__ import print_function
from argparse import ArgumentParser
import sys
try:
    import urlparse
except ImportError:
    # Renamed in Python3
    from urllib import parse as urlparse
# Library imports
import requests as r

# Some constants #

# Want to request json from the server
_HEADERS = {'Accept': 'application/json',
            'Content-Type': 'application/xml'}

_REQUESTBASE = """
<build personal="{personal}" branchName="{branch}">
  <buildType id="{buildid}"/>
  <comment><text>Triggered from CLI</text></comment>
  <properties>
    <property name="remote" value="{remote}"/>
    <property name="branch" value="{branch}"/>{props}
  </properties>
</build>
"""

_REQUESTPROPERTYBASE = '\n    <property name="{name}" value="{value}"/>'

_NEO4JLINUX_ID = "JonasHaRequests_Neo4jCustom"
_HAR_ID = "JonasHaRequests_HarBranchArtifacts"

_LINUX_JDKS = ['openjdk-8', 'openjdk-7',
               'oracle-jdk-8', 'oracle-jdk-7',
               'ibmjdk-8', 'ibmjdk-7']

# End constants #


# Top level parsers

# All builds share teamcity information
_PARSER = ArgumentParser(add_help=False)
_REQUIRED = _PARSER.add_argument_group('mandatory arguments')
_REQUIRED.add_argument('-u', '--user', metavar='USERNAME',
                       help='TeamCity username', required=True)
_REQUIRED.add_argument('-p', '--password',
                       help='TeamCity password', required=True)
_PARSER.add_argument('-r', '--remote', metavar='URL',
                     help='Public remote repo where branch exists',
                     default='origin')
_PARSER.add_argument('--teamcity', metavar='URL',
                     help='Url to TeamCity',
                     default='https://build.neohq.net')
_PERSONAL_PARSER = _PARSER.add_mutually_exclusive_group(required=False)
_PERSONAL_PARSER.add_argument('--personal', dest='personal',
                              action='store_true',
                              help='Start as personal build')
_PERSONAL_PARSER.add_argument('--no-personal', dest='personal',
                              action='store_false',
                              help='Do not start as personal build')
_PARSER.set_defaults(personal=False)

# All Neo4j builds share some obvious arguments
_NEO4JPARSERBASE = ArgumentParser(add_help=False)
_NEO4JPARSERBASE.add_argument('--maven-goals', metavar='GOALS',
                              help='Maven goal(s) to invoke',
                              default='clean verify')
_NEO4JPARSERBASE.add_argument('--maven-args', metavar='ARGS',
                              help='Additional Maven arguments',
                              default='-DrunITs -DskipBrowser')
_NEO4JREQUIRED = _NEO4JPARSERBASE.add_argument_group('mandatory arguments')
_NEO4JREQUIRED.add_argument('-b', '--branch',
                            help=('Branch of Neo4j to checkout.' +
                                  'Supports special "pr/1234" syntax'),
                            required=True)

# End top level parsers

def dict_as_properties(props):
    """
    Format a dictionary as xml property tags:

        <property name=NAME value=VALUE />

    """
    xml = ""
    for k, v in props.items():
        xml += _REQUESTPROPERTYBASE.format(name=k, value=v)
    return xml


def request_xml(buildid, personal, branch, remote, props=None):
    """
    Format an XML build request
    """
    if props is None:
        props = ""

    return _REQUESTBASE.format(buildid=buildid,
                               remote=remote,
                               branch=branch,
                               props=props,
                               personal=str(personal).lower())


def send_request(user, password, url, data):
    """
    Start a build, defined in data
    """
    resp = r.post(urlparse.urljoin(url, "httpAuth/app/rest/buildQueue"),
                  auth=(user, password),
                  headers=_HEADERS,
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


def start_linux(user, password, url, personal, branch, remote,
                mvngoals, mvnargs, jdk):
    """
    Start a custom linux build
    """
    props = dict_as_properties({'project-default-jdk': "%{}%".format(jdk),
                                'maven-goals': mvngoals,
                                'maven-args': mvnargs})
    data = request_xml(_NEO4JLINUX_ID, personal, branch, remote, props)
    send_request(user, password, url, data)

def start_ha(user, password, url, personal, branch, remote, arguments):
    """
    Start a custom ha robustness build
    """
    props = dict_as_properties({'run-args': arguments})
    data = request_xml(_HAR_ID, personal, branch, remote, props)
    send_request(user, password, url, data)


class TC(object):

    def __init__(self, cliargs):
        parser = ArgumentParser(
            description='Script for triggering builds on TeamCity',
            usage=__doc__)

        parser.add_argument('command', help='Type of build to invoke')

        # Only care about the first argument
        args = parser.parse_args(cliargs[:1])

        # If no method with that name exists on this object
        if not hasattr(self, args.command):
            print('Unrecognized command:', args.command)
            parser.print_help()
            exit(1)

        # Invoke the sub command method with rest of the args
        getattr(self, args.command)(cliargs[1:])

    def linux(self, subargs):
        parser = ArgumentParser(description="Neo4j Linux",
                                parents=[_PARSER, _NEO4JPARSERBASE])
        parser.add_argument('--jdk', help='JDK to build with',
                            default=_LINUX_JDKS[0], choices=_LINUX_JDKS)

        args = parser.parse_args(subargs)

        start_linux(args.user, args.password, args.teamcity, args.personal,
                    args.branch, args.remote,
                    args.maven_goals,
                    tc_mvn_args(args.maven_args),
                    args.jdk)

    def har(self, subargs):
        # Add to top group to keep a single group
        _REQUIRED.add_argument('-b', '--branch', required=True,
                               help='Branch of Neo4j to checkout. Supports special "pr/1234" syntax')
        parser = ArgumentParser(description="HA Robustness",
                                parents=[_PARSER])
        parser.add_argument('--arguments',
                              help='Arguments to give to HA-robustness run script. Note that due to a bug, you MUST start this string with a SPACE',
                              default='-ha-cluster-size=3 -threads=10 -jvm-mode=separate -time=7200 -history -myknocks -lock_manager=forseti')

        args = parser.parse_args(subargs)

        start_ha(args.user, args.password, args.teamcity, args.personal,
                 args.branch, args.remote, args.arguments)


if __name__ == "__main__":
    TC(sys.argv[1:])
