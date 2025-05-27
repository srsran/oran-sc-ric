import os
import asn1tools
import math
from ..utils import plmn_string_to_bcd, plmn_to_bytes

class nr_cgi_packer(object):
    _my_dir = os.path.dirname(os.path.abspath(__file__))
    _asn1_files = [_my_dir+'/nr_cgi.asn']
    _asn1_compiler = asn1tools.compile_files(_asn1_files, 'per')

    @staticmethod
    def pack_nrcgi(plmn_id, nr_cell_id):
        """
        Pack NRCGI data into ASN.1 format
        
        Args:
            plmn_id (str or bytes): PLMN Identity as string (e.g. "00101") or 3 bytes
            nr_cell_id (int or bytes): NR Cell Identity as 36 bits (5 bytes)
            
        Returns:
            bytes: Packed NRCGI data
        """
        # Handle PLMN ID input
        if isinstance(plmn_id, str):
            plmn_id = plmn_string_to_bcd(plmn_id)
            plmn_id = plmn_to_bytes(plmn_id)
        elif isinstance(plmn_id, bytes):
            if len(plmn_id) != 3:
                raise ValueError("PLMN Identity must be 3 bytes when provided as bytes")
        else:
            raise ValueError("PLMN Identity must be string or bytes")

        # Handle NR Cell ID input
        if isinstance(nr_cell_id, int):
            if nr_cell_id < 0 or nr_cell_id > (1 << 36) - 1:
                raise ValueError("NR Cell Identity must fit in 36 bits")
            # Convert to 5 bytes (big-endian)
            # Shift left by 4 bits since we only use 36 bits out of 40 bits (5 bytes)
            nr_cell_id_bytes = (nr_cell_id << 4).to_bytes(5, byteorder='big')
        elif isinstance(nr_cell_id, bytes) and len(nr_cell_id) == 5:
            # Convert bytes to int, shift left 4 bits, then back to bytes
            nr_cell_id_int = int.from_bytes(nr_cell_id, byteorder='big')
            nr_cell_id_bytes = (nr_cell_id_int << 4).to_bytes(5, byteorder='big')
        else:
            raise ValueError("NR Cell Identity must be int or 5 bytes")
            
        nrcgi = {
            'ext': False,
            'pLMN-Identity': plmn_id,
            'nRCellIdentity': (nr_cell_id_bytes, 36),
        }
        return nr_cgi_packer._asn1_compiler.encode('NRCGI', nrcgi)

    @staticmethod
    def unpack_nrcgi(packed_data):
        """
        Unpack NRCGI data from ASN.1 format
        
        Args:
            packed_data (bytes): Packed NRCGI data
            
        Returns:
            dict: Dictionary containing PLMN Identity and NR Cell Identity
        """
        return nr_cgi_packer._asn1_compiler.decode('NRCGI', packed_data)
