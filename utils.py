__author__ = 'mac7'

from paramiko import SSHClient
from paramiko import AutoAddPolicy


def cisco_to_ieee_802(cisco_mac):
    digits = cisco_mac.upper().replace('.','')
    ieee_mac = ':'.join([digits[0+2*i:2+2*i] for i in range(0,6)])
    return ieee_mac

def parsTik(host, login, passwrd):
    """
    :param host:
    :param login:
    :param passwrd:
    :return: List of customers (with param.)
    """
    bot = SSHClient()
    bot.set_missing_host_key_policy(AutoAddPolicy())
    bot.connect(host, username=login, password=passwrd)
    stdin, stdout, stderr = bot.exec_command('interface wireless registration-table print')
    data = stdout.readlines()
    bot.close()

    for line in data:
        print line

