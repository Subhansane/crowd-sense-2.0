#!/usr/bin/env python3
import ctypes
import json
from optparse import OptionParser
import datetime
import io
import socket
import sys
import os
import time
import select

class tracker:
    imsistate = {}
    imsis = []
    tmsis = {}
    nb_IMSI = 0
    mcc = ""
    mnc = ""
    lac = ""
    cell = ""
    country = ""
    brand = ""
    operator = ""
    purgeTimer = 10
    show_all_tmsi = False
    mcc_codes = None
    sqlite_con = None
    mysql_con = None
    mysql_cur = None
    textfilePath = None
    output_function = None
    running = True

    def __init__(self):
        self.load_mcc_codes()
        self.track_this_imsi("")
        self.output_function = self.output
        print("IMSI Catcher Initialized")

    def set_output_function(self, new_output_function):
        self.output_function = new_output_function

    def track_this_imsi(self, imsi_to_track):
        self.imsi_to_track = imsi_to_track
        self.imsi_to_track_len = len(imsi_to_track)

    def str_tmsi(self, tmsi):
        if tmsi != "":
            new_tmsi = "0x"
            for a in tmsi:
                c = hex(a)
                if len(c) == 4:
                    new_tmsi += str(c[2]) + str(c[3])
                else:
                    new_tmsi += "0" + str(c[2])
            return new_tmsi
        else:
            return ""

    def decode_imsi(self, imsi):
        new_imsi = ''
        for a in imsi:
            c = hex(a)
            if len(c) == 4:
                new_imsi += str(c[3]) + str(c[2])
            else:
                new_imsi += str(c[2]) + "0"
        mcc = new_imsi[1:4]
        mnc = new_imsi[4:6]
        return new_imsi, mcc, mnc

    def str_imsi(self, imsi, packet=""):
        new_imsi, mcc, mnc = self.decode_imsi(imsi)
        country = ""
        brand = ""
        operator = ""
        if mcc in self.mcc_codes:
            if mnc in self.mcc_codes[mcc]:
                brand, operator, country, _ = self.mcc_codes[mcc][mnc]
                new_imsi = f"{mcc} {mnc} {new_imsi[6:]}"
            elif mnc + new_imsi[6:7] in self.mcc_codes[mcc]:
                mnc += new_imsi[6:7]
                brand, operator, country, _ = self.mcc_codes[mcc][mnc]
                new_imsi = f"{mcc} {mnc} {new_imsi[7:]}"
        else:
            country = f"Unknown MCC {mcc}"
            brand = f"Unknown MNC {mnc}"
            operator = f"Unknown MNC {mnc}"
            new_imsi = f"{mcc} {mnc} {new_imsi[6:]}"
        return new_imsi, country, brand, operator

    def load_mcc_codes(self):
        try:
            with io.open('mcc-mnc/mcc_codes.json', 'r', encoding='utf8') as file:
                self.mcc_codes = json.load(file)
        except FileNotFoundError:
            os.makedirs('mcc-mnc', exist_ok=True)
            self.mcc_codes = {}

    def current_cell(self, mcc, mnc, lac, cell):
        brand = ""
        operator = ""
        country = ""
        if mcc in self.mcc_codes and mnc in self.mcc_codes[mcc]:
            brand, operator, country, _ = self.mcc_codes[mcc][mnc]
        else:
            country = f"Unknown MCC {mcc}"
            brand = f"Unknown MNC {mnc}"
            operator = f"Unknown MNC {mnc}"
        self.mcc = str(mcc)
        self.mnc = str(mnc)
        self.lac = str(lac)
        self.cell = str(cell)
        self.country = country
        self.brand = brand
        self.operator = operator

    def sqlite_file(self, filename):
        import sqlite3
        self.sqlite_con = sqlite3.connect(filename)
        self.sqlite_con.execute("CREATE TABLE IF NOT EXISTS observations(stamp datetime, tmsi1 text, tmsi2 text, imsi text, imsicountry text, imsibrand text, imsioperator text, mcc integer, mnc integer, lac integer, cell integer);")

    def text_file(self, filename):
        self.textfilePath = filename
        with open(filename, "a") as txt:
            if txt.tell() == 0:
                txt.write("stamp, tmsi1, tmsi2, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell\n")

    def output(self, cpt, tmsi1, tmsi2, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell, now, packet=None):
        output_line = f"{str(cpt):7s} ; {tmsi1:10s} ; {tmsi2:10s} ; {imsi:17s} ; {imsicountry:16s} ; {imsibrand:14s} ; {imsioperator:21s} ; {str(mcc):4s} ; {str(mnc):5s} ; {str(lac):6s} ; {str(cell):6s} ; {now.isoformat():s}"
        print(output_line)
        sys.stdout.flush()

    def pfields(self, cpt, tmsi1, tmsi2, imsi, mcc, mnc, lac, cell, packet=None):
        imsicountry = ""
        imsibrand = ""
        imsioperator = ""
        if imsi:
            imsi, imsicountry, imsibrand, imsioperator = self.str_imsi(imsi, packet)
        else:
            imsi = ""
        now = datetime.datetime.now()
        self.output_function(cpt, tmsi1, tmsi2, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell, now, packet)
        if self.textfilePath:
            with open(self.textfilePath, "a") as txt:
                txt.write(f"{str(now)}, {tmsi1}, {tmsi2}, {imsi}, {imsicountry}, {imsibrand}, {imsioperator}, {mcc}, {mnc}, {lac}, {cell}\n")
        if self.sqlite_con:
            self.sqlite_con.execute(
               "INSERT INTO observations (stamp, tmsi1, tmsi2, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
               (now, tmsi1 or None, tmsi2 or None, imsi, imsicountry, imsibrand, imsioperator, mcc, mnc, lac, cell)
            )
            self.sqlite_con.commit()

    def header(self):
        print(f"{'Nb IMSI':7s} ; {'TMSI-1':10s} ; {'TMSI-2':10s} ; {'IMSI':17s} ; {'country':16s} ; {'brand':14s} ; {'operator':21s} ; {'MCC':4s} ; {'MNC':5s} ; {'LAC':6s} ; {'CellId':6s} ; {'Timestamp':s}")
        sys.stdout.flush()

    def register_imsi(self, arfcn, imsi1="", imsi2="", tmsi1="", tmsi2="", p=""):
        do_print = False
        n = ''
        tmsi1 = self.str_tmsi(tmsi1)
        tmsi2 = self.str_tmsi(tmsi2)
        if imsi1:
            self.imsi_seen(imsi1, arfcn)
        if imsi2:
            self.imsi_seen(imsi2, arfcn)
        if imsi1 and (not self.imsi_to_track or imsi1[:self.imsi_to_track_len] == self.imsi_to_track):
            if imsi1 not in self.imsis:
                do_print = True
                self.imsis.append(imsi1)
                self.nb_IMSI += 1
                n = self.nb_IMSI
            if self.tmsis and tmsi1 and (tmsi1 not in self.tmsis or self.tmsis[tmsi1] != imsi1):
                do_print = True
                self.tmsis[tmsi1] = imsi1
            if self.tmsis and tmsi2 and (tmsi2 not in self.tmsis or self.tmsis[tmsi2] != imsi1):
                do_print = True
                self.tmsis[tmsi2] = imsi1
        if imsi2 and (not self.imsi_to_track or imsi2[:self.imsi_to_track_len] == self.imsi_to_track):
            if imsi2 not in self.imsis:
                do_print = True
                self.imsis.append(imsi2)
                self.nb_IMSI += 1
                n = self.nb_IMSI
            if self.tmsis and tmsi1 and (tmsi1 not in self.tmsis or self.tmsis[tmsi1] != imsi2):
                do_print = True
                self.tmsis[tmsi1] = imsi2
            if self.tmsis and tmsi2 and (tmsi2 not in self.tmsis or self.tmsis[tmsi2] != imsi2):
                do_print = True
                self.tmsis[tmsi2] = imsi2
        if not imsi1 and not imsi2 and tmsi1 and tmsi2:
            if self.tmsis and tmsi2 in self.tmsis:
                do_print = True
                imsi1 = self.tmsis[tmsi2]
                self.tmsis[tmsi1] = imsi1
                del self.tmsis[tmsi2]
        if do_print:
            if imsi1:
                self.pfields(str(n), tmsi1, tmsi2, imsi1, str(self.mcc), str(self.mnc), str(self.lac), str(self.cell), p)
            if imsi2:
                self.pfields(str(n), tmsi1, tmsi2, imsi2, str(self.mcc), str(self.mnc), str(self.lac), str(self.cell), p)

    def imsi_seen(self, imsi, arfcn):
        now = datetime.datetime.now()
        imsi, mcc, mnc = self.decode_imsi(imsi)
        if imsi in self.imsistate:
            self.imsistate[imsi]["lastseen"] = now
        else:
            self.imsistate[imsi] = {
                "firstseen": now,
                "lastseen": now,
                "imsi": imsi,
                "arfcn": arfcn,
            }

class gsmtap_hdr(ctypes.BigEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("version", ctypes.c_ubyte),
        ("hdr_len", ctypes.c_ubyte),
        ("type", ctypes.c_ubyte),
        ("timeslot", ctypes.c_ubyte),
        ("arfcn", ctypes.c_uint16),
        ("signal_dbm", ctypes.c_ubyte),
        ("snr_db", ctypes.c_ubyte),
        ("frame_number", ctypes.c_uint32),
        ("sub_type", ctypes.c_ubyte),
        ("antenna_nr", ctypes.c_ubyte),
        ("sub_slot", ctypes.c_ubyte),
        ("res", ctypes.c_ubyte),
    ]

def find_cell(gsm, udpdata, t=None):
    if gsm.sub_type == 0x01:
        p = bytearray(udpdata)
        if p[0x12] == 0x1b:
            m = hex(p[0x15])
            if len(m) < 4:
                mcc = m[2] + '0'
            else:
                mcc = m[3] + m[2]
            mcc += str(p[0x16] & 0x0f)
            m = hex(p[0x17])
            if len(m) < 4:
                mnc = m[2] + '0'
            else:
                mnc = m[3] + m[2]
            lac = p[0x18] * 256 + p[0x19]
            cell = p[0x13] * 256 + p[0x14]
            t.current_cell(mcc, mnc, lac, cell)

def find_imsi(udpdata, t=None):
    if t is None:
        return
    gsm = gsmtap_hdr.from_buffer_copy(udpdata)
    if gsm.sub_type == 0x1:
        find_cell(gsm, udpdata, t=t)
    else:
        p = bytearray(udpdata)
        tmsi1 = ""
        tmsi2 = ""
        imsi1 = ""
        imsi2 = ""
        if p[0x12] == 0x21:
            if p[0x14] == 0x08 and (p[0x15] & 0x1) == 0x1:
                imsi1 = p[0x15:][:8]
                if p[0x10] == 0x59 and p[0x1E] == 0x08 and (p[0x1F] & 0x1) == 0x1:
                    imsi2 = p[0x1F:][:8]
                elif p[0x10] == 0x4d and p[0x1E] == 0x05 and p[0x1F] == 0xf4:
                    tmsi1 = p[0x20:][:4]
                t.register_imsi(gsm.arfcn, imsi1, imsi2, tmsi1, tmsi2, p)
            elif p[0x1B] == 0x08 and (p[0x1C] & 0x1) == 0x1:
                tmsi1 = p[0x16:][:4]
                imsi2 = p[0x1C:][:8]
                t.register_imsi(gsm.arfcn, imsi1, imsi2, tmsi1, tmsi2, p)
            elif p[0x14] == 0x05 and (p[0x15] & 0x07) == 4:
                tmsi1 = p[0x16:][:4]
                if p[0x1B] == 0x05 and (p[0x1C] & 0x07) == 4:
                    tmsi2 = p[0x1D:][:4]
                t.register_imsi(gsm.arfcn, imsi1, imsi2, tmsi1, tmsi2, p)
        elif p[0x12] == 0x22:
            if p[0x1D] == 0x08 and (p[0x1E] & 0x1) == 0x1:
                tmsi1 = p[0x14:][:4]
                tmsi2 = p[0x18:][:4]
                imsi2 = p[0x1E:][:8]
                t.register_imsi(gsm.arfcn, imsi1, imsi2, tmsi1, tmsi2, p)

def udpserver(port, prn, t):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', port)
    sock.bind(server_address)
    sock.setblocking(0)
    print(f"Listening on port {port} for GSMTAP data...")
    while t.running:
        try:
            ready = select.select([sock], [], [], 1.0)
            if ready[0]:
                udpdata, address = sock.recvfrom(4096)
                if prn:
                    prn(udpdata, t)
        except KeyboardInterrupt:
            print("Shutting down...")
            t.running = False
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.1)

if __name__ == "__main__":
    imsitracker = tracker()
    parser = OptionParser(usage="%prog: [options]")
    parser.add_option("-p", "--port", dest="port", default="4729", type="int", help="Port")
    parser.add_option("-w", "--sqlite", dest="sqlite", default=None, type="string", help="Save to SQLite file")
    parser.add_option("-t", "--txt", dest="txt", default=None, type="string", help="Save to TXT file")
    parser.add_option("-a", "--alltmsi", action="store_true", dest="show_all_tmsi", help="Show TMSI without IMSI")
    (options, args) = parser.parse_args()
    if options.sqlite:
        imsitracker.sqlite_file(options.sqlite)
    if options.txt:
        imsitracker.text_file(options.txt)
    imsitracker.show_all_tmsi = options.show_all_tmsi
    imsitracker.header()
    try:
        udpserver(port=options.port, prn=find_imsi, t=imsitracker)
    except KeyboardInterrupt:
        print("IMSI Catcher stopped")
    except Exception as e:
        print(f"Error: {e}")
