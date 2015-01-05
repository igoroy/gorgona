import pexpect
import sys

class BRAS():
    def __init__(self, ip, username, password, login_method='telnet', log_stdout=False):

        """Create BRAS object that fetches
        users and established PPPoE sessions
        from cisco router"""

        bras_child = pexpect.spawn('%s %s' % (login_method, ip))
        if log_stdout:
            bras_child.logfile_read = sys.stdout
        bras_child.expect('sername')
        bras_child.sendline(username)
        bras_child.expect('assword')
        bras_child.sendline(password)
        bras_child.expect('>')
        bras_child.sendline('terminal length 0')
        bras_child.expect('>')
        bras_child.sendline('sh pppoe sess')
        bras_child.expect('>')
        self._session_lines = bras_child.before.splitlines()[:-1]
        while 'SID  LocMAC' not in self._session_lines[0]:
            self._session_lines.pop(0)
        self._session_lines.pop(0)
        bras_child.sendline('sh users | i PPPoE')
        bras_child.expect('>')
        self._user_lines = bras_child.before.splitlines()[1:-1]
        bras_child.sendline('q')

    def user_lines(self):
        """return the list of lines in
        'sh users | i PPPoE' output"""
        return self._user_lines

    def session_lines(self):
        """return the list of lines in
        'sh pppoe sess' output"""
        return self._session_lines
