#---------------------------------------------------------------------------
# Copyright 2013 PwC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#---------------------------------------------------------------------------

## @package reg_testmain01
## Registration Package Testing (Main)

'''
This is the main Registration script that calls the underlying
Registration functional tests located in REG_Suite001.

This test method (main()) is called through ctest, but can be
launched direct via python with proper arguments.

The resultdir argument is location where test results will be placed.
The namespace argument specifies the VistA namespace to be tested.
The coveragetype argument specifies the type of coverage files generated.
The logging-level and logging-file arguments specify the logging levels
to be used during testing (CRITICAL, ERROR, WARNING, INFO, DEBUG).

The pass/fail results from each test will be logged in the
Registration_results.txt file which will be written to the resultdir.

Created on November 2012
@author: pbradley
@copyright PwC
@license http://www.apache.org/licenses/LICENSE-2.0
'''

import sys
import logging
sys.path = ['./RAS/lib'] + ['./dataFiles'] + ['../Python/vista'] + sys.path
import REG_Suite001
import os, errno
import argparse
import datetime

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}


def timeStamped(fname, fmt='%Y-%m-%d-%H-%M-%S_{fname}'):
    ''' This method appends a date/time stamp to a filename'''
    return datetime.datetime.now().strftime(fmt).format(fname=fname)

def main():
    '''This is the main method that calls all the individual tests in the Registration test suite'''
    usage = "usage: %prog [options] arg"
    parser = argparse.ArgumentParser()
    parser.add_argument('resultdir', help='Result Directory')
    parser.add_argument('namespace', help='Namespace')
    parser.add_argument('coveragetype', help='Human readable coverage on/off')
    parser.add_argument('-l', '--logging-level', help='Logging level')
    parser.add_argument('-f', '--logging-file', help='Logging file name')
    args = parser.parse_args()
    logging_level = LOGGING_LEVELS.get(args.logging_level, logging.NOTSET)
    logging.basicConfig(level=logging_level,
                      filename=args.logging_file,
                      format='%(asctime)s %(levelname)s: %(message)s',
                      datefmt='%Y-%m-%d %H:%M:%S')

    if not os.path.isdir(args.resultdir):
      try:
         os.makedirs(args.resultdir)
      except OSError, e:
         if e.errno != errno.EEXIST:
             raise
    try:
        logging.debug('RESULTDIR: ' + args.resultdir)
        logging.debug('LOGGING:   ' + args.logging_level)
        resfile = args.resultdir + '/' + timeStamped('Registration_results.txt')
        if not os.path.isabs(args.resultdir):
            logging.error('EXCEPTION: Absolute Path Required for Result Directory')
            raise
        resultlog = file(resfile, 'w')
        REG_Suite001.startmon(resultlog, args.resultdir, args.namespace)
        REG_Suite001.setup_ward(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test001(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test002(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test003(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test004(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test005(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test006(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_test007(resultlog, args.resultdir, args.namespace)
        REG_Suite001.reg_logflow(resultlog, args.resultdir, args.namespace)
        REG_Suite001.stopmon(resultlog, args.resultdir, args.coveragetype, args.namespace)
    except Exception, e:
        resultlog.write('\nREGISTRATION TEST EXCEPTION ERROR:' + str(e))
        logging.error('*****Registration test exception*********' + str(e))
    finally:
        resultlog.write('finished')

if __name__ == '__main__':
  main()
