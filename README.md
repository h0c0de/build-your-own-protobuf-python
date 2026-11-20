# Build Your Own — Protobuf Wire Format

**Format kabel Protocol Buffers** dalam Python murni, tiga
lapisan: varint & ZigZag, rekaman umum tanpa skema, dan lapisan
skema ber-semantik proto3. Dibuktikan byte-exact dengan contoh
terkerjakan panduan *Encoding* resmi (Test1–Test4), lalu
**byte serialisasi identik dua arah melawan pustaka `protobuf`
resmi** untuk pesan berisi semua tipe skalar, enum, subpesan,
dan repeated packed.

Pelajaran intinya: yang berjalan di kabel hanyalah nomor field
dan tipe kabel — nama dan tipe deklarasi hidup di skema, bukan
di data.

## Isi

| Berkas | Isi |
|---|---|
| `protobufku.py` | Varint/ZigZag, lapisan umum (grup termasuk), lapisan skema proto3 |
| `uji_irisan1.py` … `uji_irisan3.py` | Uji per irisan (irisan 3 perlu `protobuf` resmi) |

## Memakai

```python
from protobufku import enkode, dekode, dekode_umum

SKEMA = {1: ("nama", "string"),
         2: ("umur", "uint32"),
         3: ("nilai", "sint32", {"berulang": True})}

data = enkode(SKEMA, {"nama": "Vero", "umur": 30, "nilai": [-1, 2]})
assert dekode(SKEMA, data)["nama"] == "Vero"
print(dekode_umum(data))   # tanpa skema: [(1, 2, b'Vero'), ...]
```

## Tiga hal yang menentukan

1. **Negatif itu mahal — kecuali ZigZag.** `int32`/`int64`
   negatif selalu 10 byte (komplemen dua 64-bit). `sint32`/
   `sint64` memetakan −1→1, 1→2, −2→3, jadi angka kecil
   bertanda tetap kecil di kabel. Memilih jenis = memilih
   biaya.
2. **Packed adalah bawaan, bukan hiasan.** Repeated numerik
   dikirim sebagai satu rekaman LEN berisi elemen berurutan;
   parser wajib menerima *kedua* bentuk (packed utuh, packed
   terbelah banyak rekaman, expanded berselang) — panduan
   memberinya sebagai tiga enkode sah untuk pesan yang sama,
   dan ketiganya diuji di sini.
3. **Field asing bukan sampah.** Dekoder yang membuang field
   tak dikenalnya menghancurkan data saat meneruskan pesan.
   Lapisan skema di sini menyimpannya di `_asing` dan
   menuliskannya kembali apa adanya.

## Kejujuran lingkup

Grup (SGROUP/EGROUP) didukung di lapisan umum saja — sudah
usang di bahasa `.proto`. Field singular yang muncul dua kali:
yang terakhir menang (protobuf resmi *menggabungkan* subpesan
singular; penyederhanaan ini dinyatakan terbuka). Map adalah
repeated pesan kunci/nilai biasa, tanpa gula khusus.

## Lisensi

Kode: MIT. Panduan encoding © Google (dokumentasi Protocol
Buffers). `protobuf` hanya wasit uji, tidak disertakan.
