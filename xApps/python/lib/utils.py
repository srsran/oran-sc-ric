def is_valid_mcc(mcc):
    return len(mcc) == 3 and mcc.isdigit()

def is_valid_mnc(mnc):
    return (len(mnc) == 2 or len(mnc) == 3) and mnc.isdigit()

def string_to_mcc(str_mcc):
    if not is_valid_mcc(str_mcc):
        return None
    mcc = 0xf000
    mcc |= (int(str_mcc[0]) << 8)
    mcc |= (int(str_mcc[1]) << 4)
    mcc |= int(str_mcc[2])
    return mcc

def string_to_mnc(str_mnc):
    if not is_valid_mnc(str_mnc):
        return None
    mnc = 0xf000 if len(str_mnc) == 3 else 0xff00
    if len(str_mnc) == 3:
        mnc |= (int(str_mnc[0]) << 8)
        mnc |= (int(str_mnc[1]) << 4)
        mnc |= int(str_mnc[2])
    else:
        mnc |= (int(str_mnc[0]) << 4)
        mnc |= int(str_mnc[1])
    return mnc

def ngap_mccmnc_to_plmn(mcc, mnc):
    nibbles = [0] * 6
    nibbles[1] = (mcc & 0x0f00) >> 8  # MCC digit 1
    nibbles[0] = (mcc & 0x00f0) >> 4  # MCC digit 2
    nibbles[3] = mcc & 0x000f         # MCC digit 3

    if (mnc & 0xff00) == 0xff00:
        # 2-digit MNC
        nibbles[2] = 0x0f               # MNC digit 1
        nibbles[5] = (mnc & 0x00f0) >> 4  # MNC digit 2
        nibbles[4] = mnc & 0x000f         # MNC digit 3
    else:
        # 3-digit MNC
        nibbles[2] = (mnc & 0x0f00) >> 8  # MNC digit 1
        nibbles[5] = (mnc & 0x00f0) >> 4  # MNC digit 2
        nibbles[4] = mnc & 0x000f         # MNC digit 3

    plmn = 0
    plmn |= nibbles[0] << 20
    plmn |= nibbles[1] << 16
    plmn |= nibbles[2] << 12
    plmn |= nibbles[3] << 8
    plmn |= nibbles[4] << 4
    plmn |= nibbles[5]
    return plmn

def plmn_string_to_bcd(plmn):
    if len(plmn) not in (5, 6):
        return 0

    mcc = string_to_mcc(plmn[:3])
    if mcc is None:
        return 0

    mnc = string_to_mnc(plmn[3:])
    if mnc is None:
        return 0

    return ngap_mccmnc_to_plmn(mcc, mnc)

def bcd_plmn_to_mcc(plmn):
    mcc = 0xf000
    mcc |= (plmn & 0x0f0000) >> 8   # MCC digit 1
    mcc |= (plmn & 0xf00000) >> 16  # MCC digit 2
    mcc |= (plmn & 0x00f00) >> 8    # MCC digit 3
    return mcc

def bcd_plmn_to_mnc(plmn):
    is_2_digit = ((plmn & 0x00f000) >> 12) == 0xf
    mnc = 0xf000
    mnc |= 0x0f00 if is_2_digit else (plmn & 0x00f000) >> 4  # MNC digit 1
    mnc |= (plmn & 0xf) << 4                                 # MNC digit 2
    mnc |= (plmn & 0xf0) >> 4                                # MNC digit 3
    return mnc

def plmn_to_bytes(plmn):
    mcc = bcd_plmn_to_mcc(plmn)
    mnc = bcd_plmn_to_mnc(plmn)
    bytes_array = [
        ((mcc & 0xf00) >> 8) + (mcc & 0xf0),
        (mcc & 0xf) + ((mnc & 0xf00) >> 4),
        ((mnc & 0xf) << 4) + ((mnc & 0xf0) >> 4)
    ]
    return bytes(bytes_array)
