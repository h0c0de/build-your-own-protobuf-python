# Catatan — Build 32: Protobuf Wire Format

## Irisan 1 — Varint, ZigZag, jangkar panduan (50 cek)

Panduan resmi kini memakai edisi 2023, tetapi contoh klasiknya
utuh: Test1 `089601`, Test2 `1207…`, Test3 `1a03089601` —
ketiganya byte-exact dari enkoder skema-ku. Tabel ZigZag
panduan disalin utuh (0→0 … −0x80000000→0xFFFFFFFF) plus
contoh protoskopnya −500z = varint 999. Kontras yang menjadi
judul build ini terbukti dalam dua baris uji: `int32 −2` =
tag + **10 byte**, `sint32 −2` = tag + **1 byte** (`0803`).

Varint overlong (0 ditulis `8000`) diterima — parser resmi
pun menerimanya; yang ditolak hanya >10 byte dan terpotong.

## Irisan 2 — Umum, grup, Test4 (20 cek)

Lapisan umum bolak-balik semua tipe kabel termasuk grup
bersarang. Test4 adalah uji parser terpenting build ini:
panduan menyatakan tiga enkode berbeda — packed utuh
`…2a03010203`, packed terbelah dua rekaman berselang field
lain, dan expanded satu-satu — adalah pesan yang SAMA.
Ketiganya terdekode ke dict yang sama, dan enkode-ku
menghasilkan bentuk packed panduan persis.

Satu bug desain asli tertangkap irisan ini: lapisan umum
menyerahkan muatan I32/I64 sebagai *int* (sudah di-unpack),
sementara penafsir jenis fixed/float membutuhkan byte
mentahnya untuk ditafsir ulang (bit yang sama, makna beda:
fixed32 1 vs float 1.4e-45). Perbaikannya satu titik di
`_baca_rekaman`: bungkus ulang int ke byte sebelum ditafsir.

Field asing dipertahankan dan ditulis ulang byte-identik;
field dikenal yang datang dengan tipe kabel salah
diperlakukan sebagai asing (parser resmi menolaknya — beda
perilaku yang dicatat: di sini penerusan data lebih penting
daripada penolakan ketat, dan nilainya tidak dikarang).

## Irisan 3 — Diferensial protobuf resmi (12 cek)

Descriptor dibangun programatik (FileDescriptorProto ->
message_factory), pesan `Lengkap` berisi 20 field: semua
skalar, enum, subpesan, repeated int32/string/double. Tiga
baterai nilai (termasuk −2⁶³, uint64 maks, string unicode
beremoji, subpesan bernilai bawaan) menghasilkan **byte
serialisasi identik** dengan pustaka resmi, dan penguraian
silang dua arah sama. Total build: 50 + 20 + 12 = **82 cek**.
