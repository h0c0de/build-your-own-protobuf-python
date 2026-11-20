"""Irisan 1 — varint, ZigZag, dan contoh terkerjakan panduan."""
import sys

sys.path.insert(0, ".")

from protobufku import (GalatProtobuf, baca_varint, dekode, enkode,
                        tulis_varint, zigzag_dekode, zigzag_enkode)

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


# --- Varint: jangkar panduan + klasik ------------------------------
cek(tulis_varint(1) == bytes.fromhex("01"), "varint 1")
cek(tulis_varint(150) == bytes.fromhex("9601"), "varint 150 (panduan)")
cek(tulis_varint(300) == bytes.fromhex("ac02"), "varint 300")
cek(tulis_varint(0) == b"\x00", "varint 0")
cek(tulis_varint(2**64 - 1) == bytes.fromhex("ffffffffffffffffff01"),
    "varint uint64 maks = 10 byte")
for n in [0, 1, 63, 64, 127, 128, 300, 16384, 2**32, 2**63, 2**64 - 1]:
    v, pos = baca_varint(tulis_varint(n))
    cek(v == n and pos == len(tulis_varint(n)), f"varint putaran {n}")
# Bentuk overlong diterima parser (perilaku resmi)
v, _ = baca_varint(bytes.fromhex("8000"))
cek(v == 0, "varint overlong 0 diterima")
cek_galat(lambda: baca_varint(b"\x80"), "varint terpotong ditolak")
cek_galat(lambda: baca_varint(b"\x80" * 10 + b"\x01"),
          "varint 11 byte ditolak")

# --- ZigZag: tabel panduan UTUH -------------------------------------
tabel = [(0, 0), (-1, 1), (1, 2), (-2, 3),
         (0x7FFFFFFF, 0xFFFFFFFE), (-0x80000000, 0xFFFFFFFF)]
for asal, kode in tabel:
    cek(zigzag_enkode(asal, 32) == kode, f"zigzag32 {asal}")
    cek(zigzag_dekode(kode) == asal, f"zigzag32 balik {asal}")
cek(zigzag_enkode(-500, 32) == 999, "zigzag -500 = 999 (protoskop panduan)")
for n in [-2**63, -1, 0, 1, 2**63 - 1]:
    cek(zigzag_dekode(zigzag_enkode(n, 64)) == n, f"zigzag64 putaran {n}")

# --- Contoh panduan: Test1, Test2, Test3 byte-exact ------------------
SKEMA1 = {1: ("a", "int32")}
cek(enkode(SKEMA1, {"a": 150}) == bytes.fromhex("089601"),
    "Test1 panduan: 08 96 01")
cek(dekode(SKEMA1, bytes.fromhex("089601")) == {"a": 150},
    "Test1 terdekode")
cek(enkode(SKEMA1, {"a": 0}) == b"", "proto3: nilai bawaan tak dikirim")
cek(enkode(SKEMA1, {}) == b"", "field absen tak dikirim")

SKEMA2 = {2: ("b", "string")}
cek(enkode(SKEMA2, {"b": "testing"})
    == bytes.fromhex("120774657374696e67"), "Test2 panduan byte-exact")
cek(dekode(SKEMA2, bytes.fromhex("120774657374696e67"))["b"] == "testing",
    "Test2 terdekode")

SKEMA3 = {3: ("c", "pesan", {"skema": SKEMA1})}
cek(enkode(SKEMA3, {"c": {"a": 150}}) == bytes.fromhex("1a03089601"),
    "Test3 panduan byte-exact (subpesan)")
cek(dekode(SKEMA3, bytes.fromhex("1a03089601"))["c"] == {"a": 150},
    "Test3 terdekode")

# --- int negatif: 10 byte komplemen dua ------------------------------
# Panduan: int32 -2 -> varint dari 0xFFFFFFFFFFFFFFFE
SKEMA_NEG = {1: ("a", "int32")}
mentah = enkode(SKEMA_NEG, {"a": -2})
cek(mentah == bytes.fromhex("08feffffffffffffffff01"),
    "int32 -2 = tag + 10 byte varint")
cek(dekode(SKEMA_NEG, mentah)["a"] == -2, "int32 -2 kembali")
SKEMA64 = {1: ("a", "int64")}
cek(dekode(SKEMA64, enkode(SKEMA64, {"a": -2**63}))["a"] == -2**63,
    "int64 min putaran")
# ...sedangkan sint32 -2 hanya 1 byte muatan (zigzag 3)
SKEMA_SINT = {1: ("a", "sint32")}
cek(enkode(SKEMA_SINT, {"a": -2}) == bytes.fromhex("0803"),
    "sint32 -2 = 08 03 (hemat!)")
cek(dekode(SKEMA_SINT, bytes.fromhex("0803"))["a"] == -2, "sint32 balik")

print(f"irisan 1: {lulus} cek lulus")
