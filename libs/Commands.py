#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import subprocess
import os
import re
import time

try:
    from . import Messages
    from .Preferences import Preferences
except:
    from Libs import Messages
    from Libs.Preferences import Preferences


class CommandsPy(object):
    """
    Class to handle the different functions allowed by
    the platformio API, to know more information visit
    the web site: www.platformio.org
    """

    def __init__(self, env_path=False, console=False, cwd=None):
        super(CommandsPy, self).__init__()
        self.Preferences = Preferences()
        self.message_queue = Messages.MessageQueue(console)
        self.message_queue.startPrint()
        self.error_running = False
        self.console = console
        self.cwd = cwd

        # env_path from preferences
        if(not env_path):
            env_path = self.Preferences.get('env_path', False)

        # Set the enviroment Path
        if(env_path):
            os.environ['PATH'] = env_path

    def runCommand(self, commands, setReturn=False, extra_message=None):
        """
        Runs a CLI command to  do/get the differents options from platformIO
        """

        if(not commands):
            return False

        # get verbose from preferences
        verbose = self.Preferences.get('verbose_output', False)

        # get command
        command = self.createCommand(commands, verbose)

        # Console message
        cmd_type = self.getTypeAction(command)
        current_time = time.strftime('%H:%M:%S')
        start_time = time.time()
        if(cmd_type):
            self.message_queue.put(cmd_type, current_time, extra_message)

        # run command
        process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, cwd=self.cwd,
                                   universal_newlines=True, shell=True)

        # real time error build output
        # ('-v --verbose' in command and not verbose)
        if(not verbose and 'version' not in command and 'json' not in command):
            error, down, previous = False, False, ''
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    # print took time and break the loop
                    if(error):
                        self.error_running = True
                        current_time = time.strftime('%H:%M:%S')
                        diff_time = time.time() - start_time
                        diff_time = '{0:.2f}'.format(diff_time)
                        message = '\\n{0} it took {1}s\\n'
                        self.message_queue.put(
                            message, current_time, diff_time)
                    break

                # detect error
                if('in function' in output.lower() or
                        'in file' in output.lower() or
                        'error:' in output.lower()):
                    if(not error):
                        current_time = time.strftime('%H:%M:%S')
                        message = 'Error\\n{0} Details:\\n\\n'
                        self.message_queue.put(message, current_time)
                        error = True

                # realtime output for build command
                if('run' in command and '-e' in command and not 'upload'):
                    if('installing' in output.lower()):
                        package = re.match(
                            r'\w+\s(\w+-*\w+)\s\w+', output).group(1)
                        message = '\\nInstalling {0} package: '
                        self.message_queue.put(message, package)

                    # output messages
                    if (output.strip() and error and 'scons' not in output and
                            'platform' not in output.lower() and
                            'took' not in output.lower() and
                            '..' not in output and not
                            '.' == output.strip() and
                            'exit status' not in output.lower()):
                        self.message_queue.put(output)

                # strings used in more than one command
                if('already' in output.lower()):
                    message = 'Already installed\\n'
                    self.message_queue.put(message)

                if('downloading' in output.lower() and output.replace(" ", "") and output.replace(" ", "") != previous):
                    message = 'Downloading package\\n\\nIt may take a while, please be patient.\\n'
                    self.message_queue.put(message)

                if('unpacking' in output.lower() and output.replace(" ", "") and output.replace(" ", "") != previous):
                    message = 'Unpacking...\\n'
                    self.message_queue.put(message)

                if(output.replace(" ", "")):
                    previous = output

        # output
        output = process.communicate()
        stdout = output[0]
        stderr = output[1]
        return_code = process.returncode

        # set error
        if(return_code > 0):
            self.error_running = True

        # Print success status
        if(self.console and not verbose and return_code == 0):
            diff_time = time.time() - start_time
            diff_time = '{0:.2f}'.format(diff_time)
            message = 'Success | it took {0}s\\n'
            self.message_queue.put(message, diff_time)

        # print full verbose output (when is active)
        if(verbose):
            self.message_queue.put(stdout)
            if(stderr):
                self.message_queue.put(stderr)

        # return output
        if(setReturn):
            return stdout

    def getTypeAction(self, command):
        """
        Get the type of action, to get the header
        and print it in the user console

        Arguments:
            command {string} -- CLI command
        """
        if 'init' in command:
            return '{0} Initializing the project | '
        elif '-e' in command and not 'upload' in command:
            return '{0} Building the project | '
        elif '--upload-port' in command:
            return '{0} Uploading firmware | '
        elif '-t clean' in command:
            return '{0} Cleaning built files | '
        elif 'lib install' in command:
            return'{0} Installing Library {1} | '
        elif 'lib uninstall' in command:
            return'{0} Uninstalling Library {1} | '
        else:
            return None

    def createCommand(self, commands, verbose):
        """
        Create the full CLI command based in the verbose mode

        Arguments:
            command {list} -- actions command to run in platformIO
            verbose {bool} -- verbose mode user preference
        """
        options = commands[0]

        try:
            args = commands[1]
        except:
            args = ''

        # output errors only
        if(not verbose and 'run' == options and '-e' in args and not 'upload'):
            args += ' -v --verbose'

        command = "platformio -f -c sublimetext %s %s 2>&1" % (
            options, args)

        return command
