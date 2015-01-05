def cisco_to_ieee_802(cisco_mac):
    digits = cisco_mac.upper().replace('.','')
    ieee_mac = ':'.join([digits[0+2*i:2+2*i] for i in range(0,6)])
    return ieee_mac
