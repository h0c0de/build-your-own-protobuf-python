# Rencana — Build 32: Protobuf Wire Format

Sumber: panduan *Encoding* resmi Protocol Buffers
(developers.google.com/protocol-buffers/docs/encoding) — contoh
terkerjakannya (Test1–Test4, tabel ZigZag) jadi jangkar statis.
Wasit: pustaka `protobuf` resmi 7.36.2 (venv
`../protobuf-ref/venv`) lewat pesan DINAMIS (descriptor dibangun
programatik, tanpa protoc).

## Irisan

- [x] Irisan 1 — Varint + ZigZag + tipe skalar: tag
      (nomor<<3)|tipe, varint base-128, int negatif 10 byte
      (komplemen dua 64-bit), sint ZigZag, fixed/float/double
      little-endian. Uji: jangkar panduan — Test1 `089601`,
      Test2, Test3 byte-exact; tabel ZigZag panduan utuh.
- [x] Irisan 2 — Lapisan umum (tanpa skema) + grup + lapisan
      skema: dekode_umum/enkode_umum (grup bersarang termasuk),
      enkode/dekode ber-skema (proto3: nilai bawaan tak
      dikirim, packed bawaan untuk repeated numerik, kedua
      bentuk packed & expanded diterima), field asing
      dipertahankan untuk enkode ulang. Uji: TIGA enkode Test4
      dari panduan (packed utuh, packed terbelah, expanded
      berselang) terdekode sama; semua bentuk malformed ditolak.
- [x] Irisan 3 — Diferensial melawan protobuf resmi: pesan
      dinamis berisi semua tipe skalar + pesan bersarang +
      repeated packed; byte serialisasi mereka == byte-ku dua
      arah (mereka mengurai punyaku, aku mengurai punyanya).

## Keputusan lingkup

- Map = repeated pesan kunci/nilai biasa di lapisan skema
  pemanggil; tidak ada gula sintaks khusus map.
- Field singular yang muncul dua kali: yang terakhir menang
  (skalar maupun pesan) — protobuf resmi menggabungkan pesan
  singular; penyederhanaan ini dinyatakan terbuka.
- Grup (SGROUP/EGROUP, usang) didukung di lapisan umum saja.

## Pagar selesai

- [x] Semua uji irisan 1–3 hijau.
- [x] README.md + CATATAN.md lengkap.
- [x] Terbit di github.com/h0c0de/build-your-own-protobuf-python
