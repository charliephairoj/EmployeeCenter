"""
Tests the specified module
"""
import os
import sys
import subprocess
import logging

import django


logger = logging.getLogger(__name__)


def test_module(module):
    cmd = "python manage.py test {0} --settings=EmployeeCenter.test-settings --keepdb".format(module)
    subprocess.call(cmd, shell=True)

def test_coverage(module='EmployeeCenter'):
    try:
        src = module.split('.')[0]
    except Exception as e:
        src = '.'
    cmd = "python -m coverage run --source='{0}' manage.py test {0}"
    cmd = cmd.format(src, module)
    cmd += ' --settings=EmployeeCenter.test-settings --keepdb --parallel'
    subprocess.call(cmd, shell=True)
    cmd2 = 'python -m coverage report -m'
    subprocess.call(cmd2, shell=True)
    
if __name__ == '__main__':
    logger.debug(__name__)
    try:
        module_to_test = sys.argv[1]
        if module_to_test == 'all':
            test_module('')
        elif module_to_test == 'coverage':
            module_to_test = sys.argv[2] or 'EmployeeCenter'
            test_coverage(module_to_test)
        else:
            test_module(module_to_test)
    except IndexError:
        print "Error: Please specify a module to test"
        

