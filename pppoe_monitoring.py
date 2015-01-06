import sys
from threading import Thread
from subprocess import Popen, PIPE
from math import sqrt
import json
import datetime
from pexpect import spawn, EOF, TIMEOUT
from bras import BRAS
from utils import cisco_to_ieee_802
import pprint

class Fping(Thread):
    """
    """
    def __init__(self, ip_list, repeat_count=10):
        """
        """
        Thread.__init__(self)
        self.ip_list = ip_list
        self.repeat_count = repeat_count
        self.result = None

    def run(self):
        """
        """
        pipe = Popen(['fping', '-C%d' % self.repeat_count, '-q', '-i25'], stdin=PIPE, stderr=PIPE, close_fds=True)
        pipe.stdin.write('\n'.join(self.ip_list))
        pipe.stdin.close()
        raw_result = pipe.stderr.read()
        self.result = {}

        for line in raw_result.splitlines():
            if 'ICMP' in line:
                # ignore the unreachable, TTL exceeded, etc. messages
                continue
            parts = line.split(' : ')
            ip = parts[0].strip()
            rtt_list = parts[1].split(' ')
            packet_loss = 100*float(rtt_list.count('-'))/len(rtt_list)
            # remove the '-' values from the list and convert the rest to float
            rtt_values = map(float, filter(lambda x: x != '-', rtt_list))

            if len(rtt_values) > 0:
                rtt_min = min(rtt_values)
                rtt_max = max(rtt_values)
                rtt_avg = sum(rtt_values)/len(rtt_values)
                rtt_dev = sqrt(sum([(v-rtt_avg)**2 for v in rtt_values])/len(rtt_values))
                self.result[ip] = {
                        'packet_loss': packet_loss,
                        'rtt_min': rtt_min,
                        'rtt_max': rtt_max,
                        'rtt_avg': rtt_avg,
                        'rtt_dev': rtt_dev,
                        }
            else:
                self.result[ip] = {
                        'packet_loss': packet_loss,
                        'rtt_min': "0",
                        'rtt_max': "0",
                        'rtt_avg': "0",
                        'rtt_dev': "0",
                        }

class NS_M5(Thread):
    """
    """
    def __init__(self, ip, username, password):
        """
        """
        Thread.__init__(self)
        self.ip = ip
        self.username = username
        self.password = password

    def run(self):
        """
        """
        try:
            child = spawn('ssh %s@%s' % (self.username, self.ip))
            child.logfile_read = open('/tmp/%s.log' % self.ip, 'w')
            child.expect('assword')
            child.sendline(self.password)
            child.expect('#')
            hostname = child.before.split('\n')[-1]
            child.sendline('wstalist')
            child.expect_exact('wstalist')
            child.expect_exact(hostname)
            json_response = child.before
            self.client_data = json.loads(json_response)
            child.sendline('/usr/www/status.cgi')
            child.expect_exact('/usr/www/status.cgi')
            child.expect_exact(hostname)
            json_response = child.before.replace('Content-Type: application/json', '')
            self.ap_data = json.loads(json_response)
            self.fetched_data = True
        except EOF:
            self.fetched_data = False
        except TIMEOUT:
            self.fetched_data = False

class NS_5(Thread):
    """
    """
    def __init__(self, ip, username, password):
        """
        """
        Thread.__init__(self)
        self.ip = ip
        self.username = username
        self.password = password

    def run(self):
        """
        """
        try:
            child = spawn('ssh %s@%s' % (self.username, self.ip))
            child.expect('assword')
            child.sendline(self.password)
            child.expect('#')
            hostname = child.before.split('\n')[-1]
            child.sendline('/usr/www/wstalist')
            child.expect_exact('/usr/www/wstalist')
            child.expect_exact(hostname)
            response = child.before
            lines = response.splitlines()[2:]
            self.client_data = []
            for info_line, rates_line, signals_line, stats_line in [lines[4*i:4*i+4] for i in range(0, len(lines)/4)]:
                mac, assoc_id, tx_rate, rx_rate, signal_strength, ccq, idle, uptime, static, noise_floor, tx_power = info_line.split('|')
                rx_packets, rx_bytes, tx_packets, tx_bytes = stats_line.split(': ')[1].split('|')
                client_datum = {}
                client_datum['mac'] = mac
                client_datum['signal'] = int(signal_strength)
                client_datum['ccq'] = int(ccq)/10
                client_datum['name'] = 'UBNT'
                client_datum['rx'] = float(rx_rate)
                client_datum['tx'] = float(tx_rate)
                client_datum['stats'] = {
                        'rx_bytes': int(rx_bytes),
                        'tx_bytes': int(tx_bytes),
                        }
                self.client_data.append(client_datum)
            self.ap_data = {}
            self.fetched_data = True
        except EOF:
            self.fetched_data = False
        except TIMEOUT:
            self.fetched_data = False

class routerOS(Thread): #unfinished
    """
    """
    def __init__(self, ip, username, password):
        """
        """
        Thread.__init__(self)
        self.ip = ip
        self.username = username
        self.password = password

    def run(self):
        """
        """
        try:
            child = spawn('telnet %s' % self.ip)
            child.logfile_read = open('/tmp/%s.log' % self.ip, 'w')
            child.expect('Login:')
            child.sendline(self.username)
            child.expect('Password:')
            child.sendline(self.password)
            child.expect('>')

            json_response = child.before
            self.client_data = json.loads(json_response)

            json_response = child.before.replace('Content-Type: application/json', '')
            self.ap_data = json.loads(json_response)
            self.fetched_data = True
        except EOF:
            self.fetched_data = False
        except TIMEOUT:
            self.fetched_data = False

def find_station_client(station_mapping, mac):
    """
    """
    for station in station_mapping:
        for client_datum in station_mapping[station]['client_data']:
            if client_datum['mac'] == mac:
                return station, client_datum
    return None, None

def format_nsca(service, client, status_code, text, values):
    """
    """
    nsca_line = '%s\t%s\t%d\t%s' % (
            service,
            client,
            status_code,
            text,
            )
    if len(values) > 0:
        nsca_line += '|'
    for name, val, t, postfix in values:
        if val is not None:
            nsca_line += '%s=%s%s%s ' % (name, val, t, postfix or '')
    return nsca_line

def main():
    """
    """
    custAuth = json.load(open(sys.path[0]+'/psswd.json'))
    hercules = BRAS(ip=custAuth[bras][ip], username=custAuth[bras][login], password=custAuth[bras][passwd])
    virtual_access_mapping = {}
    lcp_macs = []
    pta_macs = []

    for i in range(0, len(hercules.session_lines())/2):
        first_line = hercules.session_lines()[2*i]
        second_line = hercules.session_lines()[2*i + 1]
        uid, sid, remote_mac, port, virtual_template, virtual_access, state = [part.strip() for part in first_line.split( )]
        remote_mac = cisco_to_ieee_802(remote_mac)
        if state == 'LCP':
            lcp_macs.append(remote_mac)
        else:
            pta_macs.append(remote_mac)
            local_mac, v_text, vlan_id, status = [part.strip() for part in second_line.split( )]
            local_mac = cisco_to_ieee_802(local_mac)
            vlan_id = vlan_id[1:]

            virtual_access_mapping[virtual_access] = {
                    'mac': remote_mac,
                    }

    for line in hercules.user_lines():
#        virtual_access, username, mode, idle, ip_address = [
#                part.strip() for part in line.split( )]
        temp_userlines = [part.strip() for part in line.split( )]
        if len(temp_userlines) == 4:
            virtual_access, username, mode, idle = temp_userlines
            ip_address = '127.0.0.1'
        else:
            virtual_access, username, mode, idle, ip_address = temp_userlines

        virtual_access_mapping[virtual_access].update({
            'ip': ip_address,
            'username': username,
            })

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(virtual_access_mapping)
    stations = json.load(open(sys.path[0]+'/stations.json'))
    fping = Fping([virtual_access_mapping[v]['ip'] for v in virtual_access_mapping])
    station_procs = [NS_M5(ip, custAuth[bts][login], custAuth[bts][passwd]) for ip in stations if stations[ip]['type']=='ns_m5']
    station_procs += [NS_5(ip, custAuth[bts][login], custAuth[bts][passwd]) for ip in stations if stations[ip]['type']=='ns_5']
    station_mapping = {}
    fping.start()
    for station_proc in station_procs:
        station_proc.start()
    for station_proc in station_procs:
        station_proc.join()
        if station_proc.fetched_data:
            station_mapping.update({station_proc.ip: {
                'client_data': station_proc.client_data,
                'ap_data': station_proc.ap_data,
                }})
    pp.pprint(station_mapping)
    fping.join()
    pp.pprint(fping.result)
    nsca_lines = []
    clients = json.load(open(sys.path[0]+'/clients.json'))

    for vi in virtual_access_mapping:
        ip = virtual_access_mapping[vi]['ip']
        mac = virtual_access_mapping[vi]['mac']
        username = virtual_access_mapping[vi]['username']
        rtt_min = fping.result[ip]['rtt_min']
        rtt_avg = fping.result[ip]['rtt_avg']
        rtt_max = fping.result[ip]['rtt_max']
        rtt_dev = fping.result[ip]['rtt_dev']
        packet_loss = fping.result[ip]['packet_loss']
        station, client_datum = find_station_client(station_mapping, mac)
        if station:
            nsca_line = format_nsca(stations[station]['service'], mac.replace(':', '-'), 0, 'Username: %s; PPPoE IP: %s; Wi-Fi name: %s' % (username, ip, client_datum['name'],), [('signal', client_datum['signal'],'dBm', None),
                        ('ccq', client_datum['ccq'], '%', None),
                        ('rtt_min', rtt_min, 'ms', None),
                        ('rtt_avg', rtt_avg, 'ms', None),
                        ('rtt_max', rtt_max, 'ms', None),
                        ('packet_loss', packet_loss, '%', None),
                        ('rx_bytes', client_datum['stats']['rx_bytes'], 'c', ';;;0;512000'),
                        ('tx_bytes', client_datum['stats']['tx_bytes'], 'c', ';;;0;512000'),
                        ]
                    )
            nsca_lines.append(nsca_line)
            if mac not in clients.keys():
                log = open(sys.path[0] + '/clients.log', 'a')
                print >> log, '%s\tClient with MAC %s added to station %s' % (
                        datetime.datetime.now(),
                        mac,
                        station,
                        )
                clients[mac] = station
                log.close()
            elif clients[mac] != station:
                log = open(sys.path[0] + '/clients.log', 'a')
                print >> log, '%s\tClient with MAC %s moved from station %s to station %s' % (
                        datetime.datetime.now(),
                        mac,
                        clients[mac],
                        station,
                        )
                clients[mac] = station
                log.close()
        else:
            print 'Could not find MAC %s on stations' % mac

    for mac in lcp_macs:
        try:
            nsca_lines.append(format_nsca(
                stations[clients[mac]]['service'],
                mac.replace(':', '-'),
                2,
                'LCP (probably RADIUS rejects the client)',
                []))
        except KeyError:
            pass

    for mac in clients.keys():
        if mac not in lcp_macs and mac not in pta_macs:
            station, client_datum = find_station_client(station_mapping, mac)
            if station:
                status = 'Client connected to BS with signal %s, but PPPoE is down' % client_datum['signal']
            else:
                status = 'Client offline'
            nsca_lines.append(format_nsca(
                stations[clients[mac]]['service'],
                mac.replace(':', '-'),
                2,
                status,
                []))


    json.dump(clients, open(sys.path[0]+'/clients.json', 'w'), indent=True, sort_keys=True)

    pipe = Popen(
            ['/usr/local/bin/send_nsca', '-H', '192.168.248.103', '-c', '/usr/local/etc/send_nsca.cfg'],
            stdin=PIPE,
            stdout=PIPE,
            close_fds=True)

    pipe.stdin.write('\x17'.join(nsca_lines))
    pipe.stdin.write('\n')
    pipe.stdin.close()
    print pipe.stdout.read()


if __name__ == '__main__':
    main()

