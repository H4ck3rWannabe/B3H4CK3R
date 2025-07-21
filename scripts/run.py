import re
import requests
import unicodedata
import os
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- KONFIGURASI (DARI SKRIP ANDA) ---
CHANNEL_FILE = "channels.txt"
PRIORITY_FILE = "priority.txt"
LOG_FILE = "log.txt"
OUTPUT_FILE = "Cr4ck3rWannabe.m3u"
UNMATCHED_FILE = "notfound.txt"

# --- KONFIGURASI CHECKER ---
MAX_WORKERS = 50
TIMEOUT = 10
FALLBACK_USER_AGENTS = [
    "DENSGO/3.00.00 (Linux;Android 15.0.0;) ExoPlayerLib/2.19.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "ExoPlayerDemo/2.15.1 (Linux; Android 13) ExoPlayerLib/2.15.1",

]

# (Sisa URL_SRCS dari skrip Anda bisa ditambahkan di sini)
URL_SRCS = [
    "https://auto-update.prankgokils.workers.dev/",
    "https://raw.githubusercontent.com/mimipipi22/lalajo/refs/heads/main/playlist25",
    "https://raw.githubusercontent.com/astribugis7/Free/refs/heads/main/atex",
    "https://mahadewa666.blogspot.com/2025/04/playlist-iptv-by-zack.html",
    "https://raw.githubusercontent.com/ali-fajar/FORSAT-TV/refs/heads/main/FORSAT%20TV%20NEW%20PRO",
    "https://raw.githubusercontent.com/alkhalifitv/TV/master/playlist",
    "https://raw.githubusercontent.com/ali-fajar/FORSAT-TV/refs/heads/main/IPTV%20FORSAT%20PRO",
    "https://raw.githubusercontent.com/ali-fajar/FORSAT-TV/df22ef82b50540d090ec80e981b4893bb1398a46/iptvforsat",
    "https://github.com/mbahnunung/v3/blob/kn/m3u8/vs1.m3u8",
    "https://raw.githubusercontent.com/mbahnunung/v3/refs/heads/kn/m3u8/z.m3u8",
    "https://raw.githubusercontent.com/riagusmita182/channel/refs/heads/main/new",
    "https://raw.githubusercontent.com/hud4156/mytv/refs/heads/main/indovision.m3u",
    "https://raw.githubusercontent.com/rgieplaylist/Premium/refs/heads/main/30JUN2025",
    "https://qtvid.pw/tv_baru/malaysia/malay.m3u",
    "https://qtvid.pw/tv_baru/vidio/pilem.php",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20Github%20AFDigital-Free",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20akma.serv00.net-index.html",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20attitude.my.id-scripts-schedule.php",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20dibeli%20aktif%20selamanya%20(tvking6282.short.gy-KingRdy2606)",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20ftp.qtv.my.id-dzcrotsz.php",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20mastertv.tech-kingdanfam-pllokal1kingdanfam.php",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20mastertv.tech0909-aspalLIVE1-Petir-petir.php",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20newfamilytv.my.id-bewwbaik-aksesyuks.php",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20qtvid-utamacuk-event",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20qtvid-utamacuk-vidio",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20qtvid-utamacuk-vision",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20zonanyamantvgeulis.blogspot.com-2025-05-zona-nyaman.html%20Bckp",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/PL%20zonanyamantvgeulis.blogspot.com-2025-05-zona-nyaman.html%20Full",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/langit46.sattir.top-hasil-output.m3u%20(voly%20tv%2CSS3)",
    "https://raw.githubusercontent.com/kingRdy/TV9/refs/heads/main/Mayang%20TV%20(%20pastebin.com-raw-eEZ7KvHk%20)"
]

# --- FUNGSI-FUNGSI (SEBAGIAN BESAR DARI SKRIP ANDA) ---

def log_error(url, reason):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now}] GAGAL UNDUH: {url} - Alasan: {reason}\n")

def download_text(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        print(f"✅ Berhasil unduh: {url}")
        return r.text
    except requests.exceptions.RequestException as e:
        reason = f"Status: {e.response.status_code}" if e.response else str(e)
        print(f"❌ Gagal unduh: {url} ({reason})")
        log_error(url, reason)
        return None

def normalize_name(name):
    # Logika normalisasi dari skrip Anda
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = name.lower().replace('hd', '').replace('fhd', '').replace('uhd', '').replace('sd', '')
    name = name.replace('v+', '').replace('r+', '').replace('+', '')
    name = re.sub(r'\W+', '', name)
    return name.strip()

def extract_field(text):
    # Logika ekstraksi dari skrip Anda
    pattern = r'#EXTINF:[^,]+,(.*)'
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else ''

def split_entries(text):
    # Logika parsing blok dari skrip Anda
    url_pattern = re.compile(r'^(https?://|rtmp://).*(?:\.m3u8|\.mpd)', re.IGNORECASE)
    all_entries = []
    current_block_lines = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line: continue
        if url_pattern.search(line):
            current_block_lines.append(line)
            all_entries.append("\n".join(current_block_lines))
            current_block_lines = []
        else:
            current_block_lines.append(line)
    return all_entries

def parse_channel_file(path):
    # Logika dari skrip Anda
    channel_order, channel_meta = [], {}
    current_group = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("====="):
                current_group = re.search(r'group-title="([^"]+)"', line).group(1)
                continue
            if line.startswith("Name="):
                name_match = re.search(r'Name="([^"]+)"', line)
                logo_match = re.search(r'tvg-logo="([^"]*)"', line)
                if name_match:
                    display_name = name_match.group(1).strip()
                    norm = normalize_name(display_name)
                    if norm not in channel_meta:
                        channel_order.append(norm)
                        channel_meta[norm] = {"display_name": display_name, "group-title": current_group, "tvg-logo": logo_match.group(1) if logo_match else ""}
    return channel_order, channel_meta

def parse_priority_file(path):
    # Logika dari skrip Anda
    priomap = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    ch, dom = map(str.strip, line.strip().split("=", 1))
                    priomap[normalize_name(ch)] = dom
    except FileNotFoundError:
        print(f"⚠️ File {path} tidak ditemukan.")
    return priomap
    
# --- FUNGSI CHECKER & HEADER (DARI SAYA) ---

def generate_header(channel_count):
    wib = timezone(timedelta(hours=7))
    now = datetime.now(wib)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S (WIB)")
    epg_urls = "https://warningfm.github.io/x1/epg/guide.xml.gz, https://raw.githubusercontent.com/AqFad2811/epg/refs/heads/main/indonesia.xml"
    header = f'#EXTM3U url-tvg="{epg_urls}"\n'
    header += '#################################################################\n'
    header += '#                📺 OANTEK PLAYLIST GENERATOR 📺                #\n'
    header += '#      Playlist ini diperbarui secara otomatis via script       #\n'
    header += '#         yang memverifikasi dan menyusun ulang channel.        #\n'
    header += '#################################################################\n'
    header += f'# 🕒 Last Updated : {timestamp}\n'
    header += f'# 📡 Total Channels: {channel_count} (terverifikasi)\n'
    header += '# 📜 Note          : Untuk penggunaan pribadi & edukasi.\n\n'
    return header

def check_and_return_block(block_info):
    block_text, original_name = block_info
    lines = block_text.splitlines()
    url = ""
    original_headers = {}
    for line in lines:
        if '#EXTVLCOPT:http-user-agent=' in line: original_headers['User-Agent'] = line.split('=', 1)[1].strip()
        elif '#EXTVLCOPT:http-referrer=' in line: original_headers['Referer'] = line.split('=', 1)[1].strip()
        elif line.startswith('http'): url = line.split('|')[0].strip()
    if not url: return None, None
    
    def try_request(headers):
        try:
            with requests.get(url, headers=headers, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
                return r.status_code < 400
        except requests.exceptions.RequestException: return False
    
    # Prioritas 1: Coba dengan header asli
    if 'User-Agent' in original_headers:
        if try_request(original_headers): return block_text, original_name
    
    # Prioritas 2: Coba dengan User-Agent populer
    for ua in FALLBACK_USER_AGENTS:
        temp_headers = original_headers.copy()
        temp_headers['User-Agent'] = ua
        if try_request(temp_headers):
            # Membangun blok baru dengan UA yang berfungsi
            new_lines, ua_found = [], False
            for line in lines:
                if '#EXTVLCOPT:http-user-agent=' in line:
                    new_lines.append(f'#EXTVLCOPT:http-user-agent={ua}')
                    ua_found = True
                else: new_lines.append(line)
            if not ua_found:
                extinf_index = next((i for i, s in enumerate(new_lines) if s.startswith('#EXTINF')), -1)
                if extinf_index != -1: new_lines.insert(extinf_index + 1, f'#EXTVLCOPT:http-user-agent={ua}')
            return "\n".join(new_lines), original_name

    return None, None

# --- SKRIP UTAMA (GABUNGAN) ---
if __name__ == "__main__":
    print("➡️ Membaca file konfigurasi...")
    channel_order, channel_meta = parse_channel_file(CHANNEL_FILE)
    priority_map = parse_priority_file(PRIORITY_FILE)

    print("\n➡️ Mengunduh semua sumber playlist...")
    src_texts = [text for u in URL_SRCS if (text := download_text(u))]

    src_dict = {}
    for text in src_texts:
        for entry in split_entries(text):
            if '.mpd' in entry.lower() and 'license_key' not in entry.lower():
                continue
            name = extract_field(entry)
            bad_keywords = ['like gecko', 'chrome', 'android', 'dalvik', 'safari']
            if not name or any(bad in name.lower() for bad in bad_keywords):
                continue
            norm = normalize_name(name)
            src_dict.setdefault(norm, []).append((entry, name))

    print(f"\n➡️ Menemukan {sum(len(v) for v in src_dict.values())} total stream. Memulai pengecekan...")
    
    # LANGKAH PENGECEKAN
    working_src_dict = {}
    all_blocks_to_check = [(norm, block_info) for norm, blocks in src_dict.items() for block_info in blocks]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_norm = {executor.submit(check_and_return_block, block_info): norm for norm, block_info in all_blocks_to_check}
        for future in tqdm(as_completed(future_to_norm), total=len(future_to_norm), desc="Mengecek Channel"):
            norm = future_to_norm[future]
            result_block, original_name = future.result()
            if result_block:
                working_src_dict.setdefault(norm, []).append((result_block, original_name))

    # LANJUTKAN DENGAN LOGIKA ASLI ANDA, TAPI GUNAKAN working_src_dict
    print("\n➡️ Menyusun playlist akhir dari channel yang berfungsi...")
    out = []
    used_streams = set()
    unmatched_channels = set()

    for norm in channel_order:
        if norm not in working_src_dict:
            unmatched_channels.add(channel_meta[norm]["display_name"])
            continue

        preferred_domain = priority_map.get(norm, "sysln.id")
        def domain_priority(block_entry):
            block, _ = block_entry
            url = next((line.split('|')[0].strip() for line in block.splitlines() if line.startswith("http")), "")
            hostname = urlparse(url).hostname or ""
            return 0 if preferred_domain in hostname else 1
        
        sorted_blocks = sorted(working_src_dict[norm], key=domain_priority)
        
        meta = channel_meta[norm]
        final_name, group_title, logo = meta["display_name"], meta["group-title"], meta["tvg-logo"]

        for block, original_name in sorted_blocks:
            lines = block.strip().splitlines()
            stream_url = next((line for line in lines if line.startswith("http")), None)
            if not stream_url: continue
            
            license_key_line = next((line for line in lines if "license_key" in line), "")
            uniq_id = f"{stream_url.strip()}|{license_key_line.strip()}"
            if uniq_id in used_streams: continue
            used_streams.add(uniq_id)

            new_block_lines = []
            has_user_agent = "user-agent" in block.lower()
            
            for line in lines:
                if line.startswith("#EXTINF"):
                    tvg_id = final_name.replace(" ", "") + ".id"
                    extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{group_title}"'
                    if logo: extinf += f' tvg-logo="{logo}"'
                    extinf += f',{final_name}'
                    new_block_lines.append(extinf)
                    
                    if not has_user_agent:
                        new_block_lines.append('#EXTVLCOPT:http-user-agent=ExoPlayerDemo/2.15.1 (Linux; Android 13) ExoPlayerLib/2.15.1')
                else:
                    new_block_lines.append(line)
            out.append("\n".join(new_block_lines))

    # Tulis hasil akhir ke file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_header(len(out)))
        f.write("\n\n".join(out))

    if unmatched_channels:
        with open(UNMATCHED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(list(unmatched_channels))))
        print(f"⚠️ {len(unmatched_channels)} channel tidak ditemukan. Lihat {UNMATCHED_FILE}")

    print(f"✅ Playlist selesai. {len(out)} stream berfungsi disimpan di '{OUTPUT_FILE}'.")
