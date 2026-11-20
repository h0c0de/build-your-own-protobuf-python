"""Irisan 3 — diferensial melawan pustaka protobuf resmi 7.x.

Pesan DINAMIS: descriptor dibangun programatik (tanpa protoc),
satu pesan berisi semua tipe skalar + enum + subpesan + repeated
packed. Byte serialisasi harus identik dua arah.

Jalankan: ../protobuf-ref/venv/bin/python uji_irisan3.py
"""
import sys

sys.path.insert(0, ".")

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from protobufku import dekode, enkode

F = descriptor_pb2.FieldDescriptorProto
lulus = 0


def cek(kondisi, pesan):
    global lulus
    assert kondisi, pesan
    lulus += 1


def field(nama, nomor, tipe, label=F.LABEL_OPTIONAL, type_name=None,
          packed=None):
    f = F(name=nama, number=nomor, label=label, type=tipe)
    if type_name:
        f.type_name = type_name
    if packed is not None:
        f.options.packed = packed
    return f


fdp = descriptor_pb2.FileDescriptorProto(
    name="uji.proto", package="uji", syntax="proto3")

enum = fdp.enum_type.add(name="Warna")
for nama, nomor in [("MERAH", 0), ("HIJAU", 1), ("BIRU", 2)]:
    v = enum.value.add(name=nama, number=nomor)

dalam = fdp.message_type.add(name="Dalam")
dalam.field.append(field("a", 1, F.TYPE_INT32))

lg = fdp.message_type.add(name="Lengkap")
lg.field.append(field("i32", 1, F.TYPE_INT32))
lg.field.append(field("i64", 2, F.TYPE_INT64))
lg.field.append(field("u32", 3, F.TYPE_UINT32))
lg.field.append(field("u64", 4, F.TYPE_UINT64))
lg.field.append(field("s32", 5, F.TYPE_SINT32))
lg.field.append(field("s64", 6, F.TYPE_SINT64))
lg.field.append(field("b", 7, F.TYPE_BOOL))
lg.field.append(field("e", 8, F.TYPE_ENUM, type_name=".uji.Warna"))
lg.field.append(field("f64", 9, F.TYPE_FIXED64))
lg.field.append(field("sf64", 10, F.TYPE_SFIXED64))
lg.field.append(field("dbl", 11, F.TYPE_DOUBLE))
lg.field.append(field("f32", 12, F.TYPE_FIXED32))
lg.field.append(field("sf32", 13, F.TYPE_SFIXED32))
lg.field.append(field("flt", 14, F.TYPE_FLOAT))
lg.field.append(field("s", 15, F.TYPE_STRING))
lg.field.append(field("byt", 16, F.TYPE_BYTES))
lg.field.append(field("dalam", 17, F.TYPE_MESSAGE, type_name=".uji.Dalam"))
lg.field.append(field("rep", 18, F.TYPE_INT32, F.LABEL_REPEATED))
lg.field.append(field("reps", 19, F.TYPE_STRING, F.LABEL_REPEATED))
lg.field.append(field("repd", 20, F.TYPE_DOUBLE, F.LABEL_REPEATED))

pool = descriptor_pool.DescriptorPool()
pool.Add(fdp)
KelasLengkap = message_factory.GetMessageClass(
    pool.FindMessageTypeByName("uji.Lengkap"))

SKEMA_DALAM = {1: ("a", "int32")}
SKEMA = {
    1: ("i32", "int32"), 2: ("i64", "int64"), 3: ("u32", "uint32"),
    4: ("u64", "uint64"), 5: ("s32", "sint32"), 6: ("s64", "sint64"),
    7: ("b", "bool"), 8: ("e", "enum"), 9: ("f64", "fixed64"),
    10: ("sf64", "sfixed64"), 11: ("dbl", "double"),
    12: ("f32", "fixed32"), 13: ("sf32", "sfixed32"),
    14: ("flt", "float"), 15: ("s", "string"), 16: ("byt", "bytes"),
    17: ("dalam", "pesan", {"skema": SKEMA_DALAM}),
    18: ("rep", "int32", {"berulang": True}),
    19: ("reps", "string", {"berulang": True}),
    20: ("repd", "double", {"berulang": True}),
}

BATERAI = [
    {"i32": 150},
    {"i32": -2, "i64": -2**63, "u32": 2**32 - 1, "u64": 2**64 - 1,
     "s32": -123456, "s64": 2**62, "b": True, "e": 2,
     "f64": 2**64 - 2, "sf64": -9, "dbl": 25.4, "f32": 7,
     "sf32": -7, "flt": 1.5, "s": "halo 🌍", "byt": b"\x00\xff",
     "dalam": {"a": -1}, "rep": [3, 270, 86942], "reps": ["a", "b"],
     "repd": [0.5, -0.25]},
    {"i32": -2147483648, "s32": 2147483647, "dbl": -0.0 if False else 3.141592653589793,
     "flt": -0.25, "s": "", "rep": [], "dalam": {"a": 0}},
    {},
]


def samakan(nilai):
    """Samakan bentuk dict-ku dengan bawaan proto3 penuh."""
    penuh = {"i32": 0, "i64": 0, "u32": 0, "u64": 0, "s32": 0,
             "s64": 0, "b": False, "e": 0, "f64": 0, "sf64": 0,
             "dbl": 0.0, "f32": 0, "sf32": 0, "flt": 0.0, "s": "",
             "byt": b"", "dalam": None, "rep": [], "reps": [],
             "repd": []}
    penuh.update(nilai)
    return penuh


for i, nilai in enumerate(BATERAI):
    m = KelasLengkap()
    for kunci, v in nilai.items():
        attr = getattr(m, kunci)
        if kunci in ("rep", "reps", "repd"):
            attr.extend(v)
        elif kunci == "dalam":
            attr.a = v["a"]
        else:
            setattr(m, kunci, v)
    byte_mereka = m.SerializeToString()
    byteku = enkode(SKEMA, nilai)
    cek(byte_mereka == byteku, f"baterai {i}: byte serialisasi identik")

    # Mereka mengurai byte-ku
    m2 = KelasLengkap()
    m2.ParseFromString(byteku)
    cek(m2.SerializeToString() == byte_mereka,
        f"baterai {i}: mereka mengurai byte-ku sama")
    # Aku mengurai byte mereka
    hasil = dekode(SKEMA, byte_mereka)
    cek(hasil == samakan(nilai), f"baterai {i}: aku mengurai byte mereka")

print(f"irisan 3: {lulus} cek lulus")
