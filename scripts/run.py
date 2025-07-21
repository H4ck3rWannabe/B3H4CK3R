import re
import requests
import unicodedata
import os
import time
from datetime import datetime
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# --- KONFIGURASI ---
CHANNEL_FILE = "channels.txt"
PRIORITY_FILE = "priority.txt"
OUTPUT_FILE = "Cr4ck3rWannabe.m3u"
UNMATCHED_FILE = "notfound.txt"
LOG_FILE = "log.txt"
MAX_WORKERS = 50
TIMEOUT = 10

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

# --- FUNGSI-FUNGSI ---

def log_error(url, reason):
    """Mencatat error ke dalam file log."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{now}] GAGAL: {url} - Alasan: {reason}\n")

def download_text(url):
    """Mengunduh konten teks dari URL dengan penanganan error dan logging."""
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
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = name.lower().replace('hd', '').replace('fhd', '').replace('uhd', '').replace('sd', '')
    name = name.replace('v+', '').replace('r+', '').replace('+', '')
    name = re.sub(r'\W+', '', name)
    return name.strip()

def extract_field(block_text):
    for line in block_text.splitlines():
        if line.strip().startswith("#EXTINF"):
            match = re.search(r',(.+)', line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    return ''

def parse_m3u_to_blocks(text):
    entries = []
    current_block = []
    url_pattern = re.compile(r'^(https?://.+|rtmp://.+)', re.IGNORECASE)
    for line in text.splitlines():
        line = line.strip()
        if not line: continue
        
        is_url_line = url_pattern.match(line)
        is_extinf_line = line.startswith('#EXTINF')

        if is_extinf_line and current_block and any(url_pattern.match(l) for l in current_block):
            entries.append("\n".join(current_block))
            current_block = [line]
        else:
            if not current_block and is_extinf_line:
                current_block = [line]
            elif current_block:
                current_block.append(line)
        
        if is_url_line and current_block:
            entries.append("\n".join(current_block))
            current_block = []
            
    if current_block and any(url_pattern.match(l) for l in current_block):
        entries.append("\n".join(current_block))
        
    return entries

def parse_channel_file(path):
    channel_order, channel_meta = [], {}
    current_group = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if line.startswith("====="):
                current_group = re.search(r'group-title="([^"]+)"', line).group(1)
                continue
            
            name_match = re.search(r'Name="([^"]+)"', line)
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            name = name_match.group(1).strip() if name_match else line.split('tvg-logo=')[0].strip()
            if not name: continue
            logo = logo_match.group(1) if logo_match else ""
            norm = normalize_name(name)
            
            if norm not in channel_meta:
                channel_order.append(norm)
                channel_meta[norm] = {"display_name": name, "group-title": current_group, "tvg-logo": logo}
    return channel_order, channel_meta

def parse_priority_file(path):
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
    
def check_and_return_block(block_text):
    lines = block_text.splitlines()
    url = ""
    headers = {'User-Agent': 'Mozilla/5.0'}
    for line in lines:
        line = line.strip()
        if '#EXTVLCOPT:http-user-agent=' in line:
            headers['User-Agent'] = line.split('=', 1)[1].strip()
        elif '#EXTVLCOPT:http-referrer=' in line:
            headers['Referer'] = line.split('=', 1)[1].strip()
        elif line.startswith('http'):
            url = line.split('|')[0].strip()
    if not url: return None
    try:
        with requests.get(url, headers=headers, timeout=TIMEOUT, stream=True) as r:
            if 200 <= r.status_code < 300:
                return block_text
    except requests.exceptions.RequestException:
        pass
    return None

# --- SKRIP UTAMA ---

print("➡️ Membaca file konfigurasi (channels.txt & priority.txt)...")
channel_order, channel_meta = parse_channel_file(CHANNEL_FILE)
priority_map = parse_priority_file(PRIORITY_FILE)

print("\n➡️ Mengunduh semua sumber playlist...")
src_texts = [text for u in URL_SRCS if (text := download_text(u))]

src_dict = {}
for text in src_texts:
    for block in parse_m3u_to_blocks(text):
        if '.mpd' in block.lower() and 'license_key' not in block.lower():
            continue
        name = extract_field(block)
        bad_keywords = ['like gecko', 'chrome', 'android', 'dalvik', 'safari']
        if not name or any(bad in name.lower() for bad in bad_keywords):
            continue
        norm = normalize_name(name)
        src_dict.setdefault(norm, []).append(block)

print(f"\n➡️ Menemukan {sum(len(v) for v in src_dict.values())} total stream. Memulai pengecekan...")

working_blocks_map = {}
all_blocks_to_check = [(norm, block) for norm, blocks in src_dict.items() for block in blocks]

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_info = {executor.submit(check_and_return_block, block): norm for norm, block in all_blocks_to_check}
    
    for future in tqdm(as_completed(future_to_info), total=len(all_blocks_to_check), desc="Mengecek Channel"):
        norm = future_to_info[future]
        result_block = future.result()
        if result_block:
            working_blocks_map.setdefault(norm, []).append(result_block)

print("\n➡️ Menyusun playlist akhir dari channel yang berfungsi...")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n\n")
    unmatched_channels = set()
    used_streams = set()

    for norm in channel_order:
        if norm in working_blocks_map:
            meta = channel_meta[norm]
            
            preferred_domain = priority_map.get(norm, "sysln.id")
            def domain_priority(block):
                url = next((line.split('|')[0].strip() for line in block.splitlines() if line.startswith("http")), "")
                hostname = urlparse(url).hostname or ""
                return 0 if preferred_domain in hostname else 1
            
            sorted_blocks = sorted(working_blocks_map[norm], key=domain_priority)

            for block in sorted_blocks:
                lines = block.strip().splitlines()
                stream_url = next((line.split('|')[0].strip() for line in lines if line.startswith("http")), "")
                if not stream_url: continue
                
                license_key_line = next((line for line in lines if "license_key" in line.lower()), "")
                uniq_id = f"{stream_url}|{license_key_line}"
                if uniq_id in used_streams: continue
                used_streams.add(uniq_id)

                new_block_lines = []
                has_user_agent = "user-agent" in block.lower()
                
                extinf_written = False
                for line in lines:
                    if line.startswith("#EXTINF") and not extinf_written:
                        tvg_id = meta['display_name'].replace(" ", "") + ".id"
                        logo_str = f' tvg-logo="{meta["tvg-logo"]}"' if meta["tvg-logo"] else ""
                        new_line = f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{meta["group-title"]}"{logo_str},{meta["display_name"]}'
                        new_block_lines.append(new_line)
                        if not has_user_agent:
                            new_block_lines.append('#EXTVLCOPT:http-user-agent=ExoPlayerDemo/2.15.1 (Linux; Android 13) ExoPlayerLib/2.15.1')
                        extinf_written = True
                    elif not line.startswith("#EXTINF"):
                        new_block_lines.append(line)
                
                f.write("\n".join(new_block_lines) + "\n\n")
        else:
             unmatched_channels.add(meta.get("display_name", norm))

if unmatched_channels:
    with open(UNMATCHED_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(list(unmatched_channels))))
    print(f"⚠️ {len(unmatched_channels)} channel tidak ditemukan. Lihat {UNMATCHED_FILE}")

print(f"✅ Playlist selesai. Hasil disimpan di '{OUTPUT_FILE}'.")
