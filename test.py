"""
Tests the specified module
"""
import sys
import subprocess


def test_module(module):
    cmd = "python manage.py test {0} --settings=EmployeeCenter.test-settings".format(module)
    subprocess.call(cmd, shell=True)
    
if __name__ == '__main__':
    try:
        module_to_test = sys.argv[1]
        if module_to_test == 'all':
            test_module('')
        else:
            test_module(module_to_test)
    except IndexError:
        print "Error: Please specify a module to test"
        
    