"""Irisan 2 — lapisan umum, grup, Test4 tiga bentuk, malformed."""
import sys

sys.path.insert(0, ".")

from protobufku import (GalatProtobuf, K_32, K_64, K_LEN, K_SGRUP,
                        K_VARINT, dekode, dekode_umum, enkode, enkode_umum)

lulus = 0


def cek(kondisi, pesan):
    global lulus
    assert kondisi, pesan
    lulus += 1


def cek_galat(fungsi, pesan):
    global lulus
    try:
        fungsi()
    except GalatProtobuf:
        lulus += 1
        return
    raise AssertionError(f"tidak naik GalatProtobuf: {pesan}")


# --- Lapisan umum bolak-balik semua tipe kabel -----------------------
rekaman = [
    (1, K_VARINT, 150),
    (2, K_LEN, b"testing"),
    (3, K_32, 0xDEADBEEF),
    (4, K_64, 0x1122334455667788),
    (5, K_SGRUP, [(1, K_VARINT, 7), (2, K_LEN, b"di dalam grup")]),
]
mentah = enkode_umum(rekaman)
cek(dekode_umum(mentah) == rekaman, "umum: semua tipe + grup bersarang")
cek(enkode_umum(dekode_umum(mentah)) == mentah, "umum: enkode ulang identik")
cek(dekode_umum(b"") == [], "umum: pesan kosong")

# --- Test4 panduan: TIGA enkode sah, satu makna -----------------------
SKEMA4 = {4: ("d", "string"),
          5: ("e", "int32", {"berulang": True})}
MAKNA = {"d": "hello", "e": [1, 2, 3]}
packed_utuh = bytes.fromhex("220568656c6c6f2a03010203")
packed_belah = bytes.fromhex("2a020102" "220568656c6c6f" "2a0103")
expanded = bytes.fromhex("2801" "2802" "220568656c6c6f" "2803")
cek(enkode(SKEMA4, MAKNA) == packed_utuh,
    "Test4: enkode-ku = bentuk packed panduan")
for bentuk, nama in [(packed_utuh, "packed utuh"),
                     (packed_belah, "packed terbelah dua rekaman"),
                     (expanded, "expanded berselang field lain")]:
    cek(dekode(SKEMA4, bentuk) == MAKNA, f"Test4 terdekode: {nama}")

# Repeated fixed juga packed; kedua bentuk diterima
SKEMA_F = {1: ("v", "fixed32", {"berulang": True})}
satu = enkode(SKEMA_F, {"v": [1, 2]})
cek(satu == bytes.fromhex("0a08" "01000000" "02000000"),
    "fixed32 repeated packed")
cek(dekode(SKEMA_F, bytes.fromhex("0d01000000" "0d02000000"))["v"] == [1, 2],
    "fixed32 expanded diterima juga")

# --- Field asing dipertahankan ----------------------------------------
SKEMA_A = {1: ("a", "int32")}
data = bytes.fromhex("089601") + bytes.fromhex("3807")  # field 7 varint 7
hasil = dekode(SKEMA_A, data)
cek(hasil["a"] == 150 and hasil["_asing"] == [(7, K_VARINT, 7)],
    "field asing tercatat")
cek(enkode(SKEMA_A, hasil) == data, "enkode ulang mempertahankan asing")

# Field dikenal dengan tipe kabel SALAH diperlakukan asing
data2 = bytes.fromhex("0a026869")          # field 1 sebagai LEN
hasil2 = dekode(SKEMA_A, data2)
cek(hasil2["a"] == 0 and hasil2["_asing"] == [(1, K_LEN, b"hi")],
    "tipe kabel salah -> asing, nilai bawaan dipakai")

# --- Malformed ---------------------------------------------------------
cek_galat(lambda: dekode_umum(bytes.fromhex("08")),
          "varint muatan hilang")
cek_galat(lambda: dekode_umum(bytes.fromhex("0e00")),
          "tipe kabel 6 ditolak")
cek_galat(lambda: dekode_umum(bytes.fromhex("00")),
          "nomor field 0 ditolak")
cek_galat(lambda: dekode_umum(bytes.fromhex("1207aa")),
          "LEN melewati akhir ditolak")
cek_galat(lambda: dekode_umum(bytes.fromhex("1c")),
          "EGRUP yatim ditolak")
cek_galat(lambda: dekode_umum(bytes.fromhex("2b0801")),
          "grup tak tertutup ditolak")
cek_galat(lambda: dekode_umum(bytes.fromhex("2b24")),
          "EGRUP nomor lain ditolak")
# string bukan UTF-8 pada field string -> galat
SKEMA_S = {1: ("s", "string")}
cek_galat(lambda: dekode(SKEMA_S, bytes.fromhex("0a01ff")),
          "string UTF-8 rusak ditolak")

print(f"irisan 2: {lulus} cek lulus")
