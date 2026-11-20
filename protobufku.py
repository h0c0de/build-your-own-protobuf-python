"""protobufku — format kabel Protocol Buffers dari nol.

Tiga lapisan, sesuai cara formatnya sendiri berpikir:

1. Primitif: varint base-128 dan ZigZag — satuan terkecil kabel.
2. Umum (tanpa skema): pesan = daftar rekaman (nomor, tipe kabel,
   nilai). Inilah yang benar-benar berjalan di kabel; nama field
   dan tipe deklarasi TIDAK ikut dikirim.
3. Skema: kamus nomor -> (nama, jenis) yang memberi makna pada
   lapisan umum, dengan semantik proto3 (nilai bawaan tidak
   dikirim, repeated numerik packed secara bawaan).

Tipe kabel: 0 VARINT, 1 I64, 2 LEN, 3 SGROUP, 4 EGROUP, 5 I32.
"""

import struct

K_VARINT = 0
K_64 = 1
K_LEN = 2
K_SGRUP = 3
K_EGRUP = 4
K_32 = 5

_MASK64 = (1 << 64) - 1


class GalatProtobuf(Exception):
    pass


# ------------------------------------------------------------------
# Lapisan 1: varint & zigzag

def tulis_varint(n):
    """Varint base-128 little-endian-grup: 7 bit per byte, bit
    sambung di MSB. n diperlakukan sebagai uint64."""
    n &= _MASK64
    keluar = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            keluar.append(b | 0x80)
        else:
            keluar.append(b)
            return bytes(keluar)


def baca_varint(data, pos=0):
    """(nilai, pos_baru). Maksimal 10 byte; bentuk lebih-panjang
    (overlong) diterima seperti parser resmi; byte ke-10 hanya
    boleh membawa bit terbawah (sisanya dibuang, juga seperti
    parser resmi yang memotong ke 64 bit)."""
    hasil = 0
    geser = 0
    for _ in range(10):
        if pos >= len(data):
            raise GalatProtobuf("varint terpotong")
        b = data[pos]
        pos += 1
        hasil |= (b & 0x7F) << geser
        if not (b & 0x80):
            return hasil & _MASK64, pos
        geser += 7
    raise GalatProtobuf("varint lebih dari 10 byte")


def zigzag_enkode(n, bit=64):
    """(n << 1) ^ (n >> (bit-1)) dalam aritmetika bit-bit."""
    topeng = (1 << bit) - 1
    return ((n << 1) ^ (n >> (bit - 1))) & topeng


def zigzag_dekode(z):
    return (z >> 1) ^ -(z & 1)


# ------------------------------------------------------------------
# Lapisan 2: rekaman umum (tanpa skema)

def tulis_tag(nomor, tipe):
    if nomor <= 0:
        raise GalatProtobuf("nomor field harus >= 1")
    return tulis_varint((nomor << 3) | tipe)


def enkode_umum(rekaman):
    """rekaman: daftar (nomor, tipe, nilai). Nilai: int untuk
    VARINT/I32/I64 (uint mentah), bytes untuk LEN, daftar rekaman
    untuk SGRUP (EGRUP ditulis otomatis)."""
    keluar = bytearray()
    for nomor, tipe, nilai in rekaman:
        keluar += tulis_tag(nomor, tipe)
        if tipe == K_VARINT:
            keluar += tulis_varint(nilai)
        elif tipe == K_64:
            keluar += struct.pack("<Q", nilai & _MASK64)
        elif tipe == K_32:
            keluar += struct.pack("<I", nilai & 0xFFFFFFFF)
        elif tipe == K_LEN:
            keluar += tulis_varint(len(nilai))
            keluar += nilai
        elif tipe == K_SGRUP:
            keluar += enkode_umum(nilai)
            keluar += tulis_tag(nomor, K_EGRUP)
        else:
            raise GalatProtobuf(f"tipe kabel tidak bisa ditulis: {tipe}")
    return bytes(keluar)


def _baca_satu(data, pos):
    """Satu rekaman dari pos; kembalikan (nomor, tipe, nilai, pos).
    Untuk SGRUP, nilai = daftar rekaman sampai EGRUP pasangannya."""
    tag, pos = baca_varint(data, pos)
    nomor, tipe = tag >> 3, tag & 7
    if nomor == 0:
        raise GalatProtobuf("nomor field 0 tidak sah")
    if tipe == K_VARINT:
        nilai, pos = baca_varint(data, pos)
    elif tipe == K_64:
        if pos + 8 > len(data):
            raise GalatProtobuf("I64 terpotong")
        nilai = struct.unpack_from("<Q", data, pos)[0]
        pos += 8
    elif tipe == K_32:
        if pos + 4 > len(data):
            raise GalatProtobuf("I32 terpotong")
        nilai = struct.unpack_from("<I", data, pos)[0]
        pos += 4
    elif tipe == K_LEN:
        panjang, pos = baca_varint(data, pos)
        if pos + panjang > len(data):
            raise GalatProtobuf("LEN melewati akhir data")
        nilai = data[pos:pos + panjang]
        pos += panjang
    elif tipe == K_SGRUP:
        nilai = []
        while True:
            if pos >= len(data):
                raise GalatProtobuf("grup tidak ditutup")
            tag2, pos2 = baca_varint(data, pos)
            if (tag2 & 7) == K_EGRUP:
                if (tag2 >> 3) != nomor:
                    raise GalatProtobuf("EGRUP tidak cocok dengan SGRUP")
                pos = pos2
                break
            sub, pos = _baca_satu(data, pos)
            nilai.append(sub)
    elif tipe == K_EGRUP:
        raise GalatProtobuf("EGRUP tanpa SGRUP")
    else:
        raise GalatProtobuf(f"tipe kabel tidak dikenal: {tipe}")
    return (nomor, tipe, nilai), pos


def dekode_umum(data):
    """Seluruh pesan -> daftar rekaman (nomor, tipe, nilai)."""
    rekaman = []
    pos = 0
    while pos < len(data):
        satu, pos = _baca_satu(data, pos)
        rekaman.append(satu)
    return rekaman


# ------------------------------------------------------------------
# Lapisan 3: skema (semantik proto3)

# jenis -> (tipe kabel tunggal, bisa dipacked)
_JENIS = {
    "int32": (K_VARINT, True), "int64": (K_VARINT, True),
    "uint32": (K_VARINT, True), "uint64": (K_VARINT, True),
    "sint32": (K_VARINT, True), "sint64": (K_VARINT, True),
    "bool": (K_VARINT, True), "enum": (K_VARINT, True),
    "fixed64": (K_64, True), "sfixed64": (K_64, True),
    "double": (K_64, True),
    "fixed32": (K_32, True), "sfixed32": (K_32, True),
    "float": (K_32, True),
    "string": (K_LEN, False), "bytes": (K_LEN, False),
    "pesan": (K_LEN, False),
}

_BAWAAN = {
    "int32": 0, "int64": 0, "uint32": 0, "uint64": 0,
    "sint32": 0, "sint64": 0, "bool": False, "enum": 0,
    "fixed64": 0, "sfixed64": 0, "double": 0.0,
    "fixed32": 0, "sfixed32": 0, "float": 0.0,
    "string": "", "bytes": b"", "pesan": None,
}


def _tulis_nilai(jenis, nilai):
    """Nilai Python -> muatan mentah sesuai tipe kabel jenisnya
    (untuk VARINT: byte varint; I32/I64: byte tetap; LEN: isi)."""
    if jenis in ("int32", "int64", "enum"):
        return tulis_varint(nilai & _MASK64)
    if jenis in ("uint32", "uint64"):
        return tulis_varint(nilai)
    if jenis == "bool":
        return tulis_varint(1 if nilai else 0)
    if jenis == "sint32":
        return tulis_varint(zigzag_enkode(nilai, 32))
    if jenis == "sint64":
        return tulis_varint(zigzag_enkode(nilai, 64))
    if jenis == "fixed64":
        return struct.pack("<Q", nilai)
    if jenis == "sfixed64":
        return struct.pack("<q", nilai)
    if jenis == "double":
        return struct.pack("<d", nilai)
    if jenis == "fixed32":
        return struct.pack("<I", nilai)
    if jenis == "sfixed32":
        return struct.pack("<i", nilai)
    if jenis == "float":
        return struct.pack("<f", nilai)
    raise GalatProtobuf(f"jenis bukan skalar: {jenis}")


def _baca_nilai(jenis, mentah):
    """Muatan mentah (untuk VARINT: nilai uint64 hasil baca_varint;
    lain: bytes) -> nilai Python bertipe."""
    if jenis in ("int32", "enum"):
        v = mentah & 0xFFFFFFFF
        return v - (1 << 32) if v >= (1 << 31) else v
    if jenis == "int64":
        v = mentah & _MASK64
        return v - (1 << 64) if v >= (1 << 63) else v
    if jenis == "uint32":
        return mentah & 0xFFFFFFFF
    if jenis == "uint64":
        return mentah & _MASK64
    if jenis == "bool":
        return mentah != 0
    if jenis == "sint32":
        return zigzag_dekode(mentah & 0xFFFFFFFF)
    if jenis == "sint64":
        return zigzag_dekode(mentah & _MASK64)
    if jenis == "fixed64":
        return struct.unpack("<Q", mentah)[0]
    if jenis == "sfixed64":
        return struct.unpack("<q", mentah)[0]
    if jenis == "double":
        return struct.unpack("<d", mentah)[0]
    if jenis == "fixed32":
        return struct.unpack("<I", mentah)[0]
    if jenis == "sfixed32":
        return struct.unpack("<i", mentah)[0]
    if jenis == "float":
        return struct.unpack("<f", mentah)[0]
    raise GalatProtobuf(f"jenis bukan skalar: {jenis}")


def _urai_spesifikasi(skema):
    """skema: {nomor: (nama, jenis[, opsi])} -> struktur kaya."""
    hasil = {}
    for nomor, spec in skema.items():
        nama, jenis = spec[0], spec[1]
        opsi = spec[2] if len(spec) > 2 else {}
        hasil[nomor] = (nama, jenis, opsi)
    return hasil


def enkode(skema, nilai):
    """dict nama->nilai -> byte kabel. Field diurutkan nomor;
    nilai bawaan proto3 tidak dikirim; '_asing' (daftar rekaman
    umum dari dekode) ditulis ulang apa adanya di akhir."""
    spec = _urai_spesifikasi(skema)
    keluar = bytearray()
    for nomor in sorted(spec):
        nama, jenis, opsi = spec[nomor]
        if nama not in nilai:
            continue
        v = nilai[nama]
        tipe, bisa_packed = _JENIS[jenis]
        if opsi.get("berulang"):
            if not v:
                continue
            if bisa_packed and opsi.get("packed", True):
                isi = b"".join(
                    _tulis_isi(jenis, opsi, x) for x in v)
                keluar += tulis_tag(nomor, K_LEN)
                keluar += tulis_varint(len(isi))
                keluar += isi
            else:
                for x in v:
                    keluar += _tulis_rekaman(nomor, jenis, opsi, x)
        else:
            if jenis != "pesan" and v == _BAWAAN[jenis]:
                continue
            if jenis == "pesan" and v is None:
                continue
            keluar += _tulis_rekaman(nomor, jenis, opsi, v)
    if nilai.get("_asing"):
        keluar += enkode_umum(nilai["_asing"])
    return bytes(keluar)


def _tulis_isi(jenis, opsi, v):
    """Isi satu elemen (tanpa tag) untuk packed / LEN."""
    if jenis == "string":
        return v.encode("utf-8")
    if jenis == "bytes":
        return bytes(v)
    if jenis == "pesan":
        return enkode(opsi["skema"], v)
    return _tulis_nilai(jenis, v)


def _tulis_rekaman(nomor, jenis, opsi, v):
    tipe, _ = _JENIS[jenis]
    if tipe == K_LEN:
        isi = _tulis_isi(jenis, opsi, v)
        return tulis_tag(nomor, K_LEN) + tulis_varint(len(isi)) + isi
    return tulis_tag(nomor, tipe) + _tulis_nilai(jenis, v)


def dekode(skema, data):
    """byte kabel -> dict nama->nilai (semua field skema hadir
    dengan bawaan proto3; field asing di '_asing')."""
    spec = _urai_spesifikasi(skema)
    hasil = {}
    for nomor, (nama, jenis, opsi) in spec.items():
        hasil[nama] = [] if opsi.get("berulang") else _BAWAAN[jenis]
    asing = []
    for nomor, tipe, muatan in dekode_umum(data):
        if nomor not in spec:
            asing.append((nomor, tipe, muatan))
            continue
        nama, jenis, opsi = spec[nomor]
        tipe_sah, bisa_packed = _JENIS[jenis]
        if opsi.get("berulang") and bisa_packed and tipe == K_LEN:
            # Bentuk packed: urai isi sebagai deretan elemen.
            elemen = _urai_packed(jenis, muatan)
            hasil[nama].extend(elemen)
            continue
        if tipe != tipe_sah:
            asing.append((nomor, tipe, muatan))
            continue
        v = _baca_rekaman(jenis, opsi, tipe, muatan)
        if opsi.get("berulang"):
            hasil[nama].append(v)
        else:
            hasil[nama] = v
    if asing:
        hasil["_asing"] = asing
    return hasil


def _urai_packed(jenis, isi):
    tipe, _ = _JENIS[jenis]
    elemen = []
    pos = 0
    while pos < len(isi):
        if tipe == K_VARINT:
            mentah, pos = baca_varint(isi, pos)
        elif tipe == K_64:
            if pos + 8 > len(isi):
                raise GalatProtobuf("elemen packed I64 terpotong")
            mentah = isi[pos:pos + 8]
            pos += 8
        elif tipe == K_32:
            if pos + 4 > len(isi):
                raise GalatProtobuf("elemen packed I32 terpotong")
            mentah = isi[pos:pos + 4]
            pos += 4
        elemen.append(_baca_nilai(jenis, mentah))
    return elemen


def _baca_rekaman(jenis, opsi, tipe, muatan):
    # Lapisan umum menyerahkan I32/I64 sebagai int; jenis fixed/
    # float butuh byte mentahnya lagi untuk ditafsir ulang.
    if jenis in ("fixed64", "sfixed64", "double"):
        muatan = struct.pack("<Q", muatan)
    elif jenis in ("fixed32", "sfixed32", "float"):
        muatan = struct.pack("<I", muatan)
    if jenis == "string":
        try:
            return muatan.decode("utf-8")
        except UnicodeDecodeError:
            raise GalatProtobuf("field string bukan UTF-8 sah")
    if jenis == "bytes":
        return bytes(muatan)
    if jenis == "pesan":
        return dekode(opsi["skema"], muatan)
    return _baca_nilai(jenis, muatan)
