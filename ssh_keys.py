import json
import pexpect
import sys

stations = json.load(open('stations.json'))
for station in stations:
    try:
        child = pexpect.spawn('ssh radio@%s' % station)
        index = child.expect(['yes', 'assword'])
        if index == 0:
            child.sendline('yes\n')
            print '\n\nStation %s ok' % station
        elif index == 1:
            print 'Station %s already added' % station
        child.close()
    except pexpect.EOF:
        print 'Station %s failed' % station
