__author__ = 'mac7'

from paramiko import SSHClient
from paramiko import AutoAddPolicy


def cisco_to_ieee_802(cisco_mac):
    digits = cisco_mac.upper().replace('.','')
    ieee_mac = ':'.join([digits[0+2*i:2+2*i] for i in range(0,6)])
    return ieee_mac

def parsTik(host, login, passwrd): #with debug
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
    print tempList
    print '---------------------------------------------------------------------------------------------------------------------------'

    for badChar in badList:
        try:
            while badChar in tempList:
                tempList.remove(badChar)
        except:
            continue

    print tempList
    for badChar in badList:
        print badChar in tempList
    print '---------------------------------------------------------------------------------------------------------------------------'

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

    print cust
    print '---------------------------------------------------------------------------------------------------------------------------'

    for i in range(0, len(cust)):
        try:
            clients.append(tempList[cust[i]:cust[i+1]])
        except:
            clients.append(tempList[cust[i]:])
    print len(clients)
    for client in clients:
        print client
        print '*******************'

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