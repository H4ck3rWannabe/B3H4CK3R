# 🎯 B3H4CK3R - IPTV Cracker & Filter Tool

**B3H4CK3R** adalah alat otomatis berbasis Python yang dirancang untuk membantu menyaring dan mengelola file playlist IPTV (`.m3u`) dari berbagai sumber publik. Tool ini mampu mengekstrak channel yang valid dan memprioritaskan domain tertentu sesuai preferensi Anda.

## 🔧 Fitur Utama

- 🔍 Filter channel IPTV berdasarkan domain prioritas
- ⚡ Proses multithread cepat menggunakan `ThreadPoolExecutor`
- 🌐 Dukungan banyak sumber URL playlist `.m3u`
- 📦 Output file `.m3u` yang bisa langsung digunakan pada pemutar IPTV
- 🧹 Menyimpan channel yang tidak cocok dalam file `notfound.txt`
- 📊 Progress bar interaktif dengan `tqdm`

## 📁 Struktur File

| File / Folder                  | Deskripsi |
|-------------------------------|-----------|
| `scripts/run.py`              | Skrip utama pemrosesan IPTV |
| `channels.txt`                | Daftar channel yang ingin Anda cocokkan |
| `priority.txt`                | Daftar domain prioritas |
| `Cr4ck3rWannabe.m3u`          | Hasil file playlist yang valid |
| `notfound.txt`                | Channel yang tidak ditemukan atau tidak cocok |
| `.github/workflows/main.yml` | Workflow GitHub Actions (otomatisasi) |
| `requirements.txt`           | Dependensi Python |
| `LICENSE`                    | Lisensi proyek |
| `.gitignore`                 | File yang diabaikan oleh Git |

## 🚀 Cara Penggunaan

### 1. Instalasi

```bash
git clone https://github.com/your-username/B3H4CK3R.git
cd B3H4CK3R/scripts
pip install -r ../requirements.txt
```

### 2. Jalankan Script

```bash
python run.py
```

### 3. Hasil

- Playlist valid akan muncul di `Cr4ck3rWannabe.m3u`
- Jika ada channel yang tidak cocok, akan disimpan ke `notfound.txt`
- Progres akan tampil secara real-time di terminal

## 📥 Sumber Playlist yang Didukung

Tool ini mengambil data dari berbagai repositori publik seperti:
- GitHub raw link
- Blogspot
- CDN Workers

Anda dapat menambah atau mengedit daftar URL sumber di dalam file `run.py` bagian `URL_SRCS`.

## ✅ Lisensi

Proyek ini dilindungi oleh lisensi MIT. Silakan lihat [LICENSE](./LICENSE) untuk detail.

## 🙏 Kredit

Dibuat dengan ❤️ oleh komunitas IPTV enthusiast. Berkontribusi? Pull request selalu terbuka!