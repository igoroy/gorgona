__author__ = 'mac7'

from paramiko import SSHClient
from paramiko import AutoAddPolicy


def cisco_to_ieee_802(cisco_mac):
    digits = cisco_mac.upper().replace('.','')
    ieee_mac = ':'.join([digits[0+2*i:2+2*i] for i in range(0,6)])
    return ieee_mac

def parsDatum(source):
    """
    :param source: List os customers param.
    :return: Dict. 'client_datum' with customers stat
    """
    client_datum = {}
    for param in source:
        try:
            data = param.split('=')
            if data[0] == 'mac-address':
                client_datum['mac'] = data[1]
            elif data[0] == 'signal-strength':
                client_datum['signal'] = int(data[1][:3])
            elif data[0] == 'tx-ccq':
                client_datum['ccq'] = int(data[1][:2])
            elif data[0] == 'rx-rate':
                Mbps = data[1].find('M')
                client_datum['rx'] = float(data[1][1:Mbps])
            elif data[0] == 'tx-rate':
                Mbps = data[1].find('M')
                client_datum['tx'] = float(data[1][1:Mbps])
            elif data[0] == 'radio-name':
                client_datum['name'] = data[1]
            elif data[0] == 'bytes':
                _rx, _tx = data[1].split(',')
                client_datum['stats'] = {
                    'rx_bytes': int(_rx),
                    'tx_bytes': int(_tx),
                    }
        except:
            continue
    return client_datum


def parsTik(host, login, passwrd):
    """
    :param host: BTS MikroTik only
    :param login:
    :param passwrd:
    :return: List of customers (with param.)
    """
    bot = SSHClient()
    bot.set_missing_host_key_policy(AutoAddPolicy())
    bot.connect(host, username=login, password=passwrd)
    stdin, stdout, stderr = bot.exec_command('interface wireless registration-table print stats')
    data = stdout.read()
    bot.close()

    tempList = data.split(' ')
    badList = ['', '\r\n', '\r\n\r\n']

    for badChar in badList:
        try:
            while badChar in tempList:
                tempList.remove(badChar)
        except:
            continue

    cust = []
    clients = []

    if len(tempList) > 0:
        cnt = 0
        flag = True
        cust.append(tempList.index(str(cnt)))
        while flag:
            if str(cnt+1) in tempList:
                cust.append(tempList.index(str(cnt+1)))
                cnt += 1
            else:
                flag = False

    for i in range(0, len(cust)):
        try:
            clients.append(tempList[cust[i]:cust[i+1]])
        except:
            clients.append(tempList[cust[i]:])
    return clients

"""
    Template of customers data structure
"""
#    client_datum = {}
#    client_datum['mac'] = mac
#    client_datum['signal'] = int(signal_strength)
#    client_datum['ccq'] = int(ccq)/10
#    client_datum['name'] = 'UBNT'
#    client_datum['rx'] = float(rx_rate)
#    client_datum['tx'] = float(tx_rate)
#    client_datum['stats'] = {
#        'rx_bytes': int(rx_bytes),
#        'tx_bytes': int(tx_bytes),
#        }