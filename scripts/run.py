import re
import requests
import unicodedata
import os
from datetime import datetime, timezone, timedelta
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

FALLBACK_USER_AGENTS = [
    "ExoPlayerDemo/2.15.1 (Linux; Android 13) ExoPlayerLib/2.15.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
]

if not os.path.exists(LOG_FILE):
    open(LOG_FILE, "w", encoding="utf-8").close()

URL_SRCS = [
    "https://raw.githubusercontent.com/mimipipi22/lalajo/refs/heads/main/playlist25",
    # Tambahkan URL sumber lain di sini
]

# --- FUNGSI-FUNGSI ---

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
    emoji_pattern = re.compile("["
        "\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    name = emoji_pattern.sub(r'', name)
    name = re.sub(r'\(.*?\)|\[.*?\]', '', name)
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = name.lower()
    for word in ['hd', 'fhd', 'uhd', 'sd', 'v+', 'r+', '+', '|', 'cignal', 'th', 'id', 'my']:
        name = name.replace(word, '')
    name = re.sub(r'\W+', '', name)
    return name.strip()

def extract_field(block_text):
    for line in block_text.splitlines():
        if line.strip().startswith("#EXTINF"):
            match = re.search(r',(.+)', line, re.IGNORECASE)
            if match: return match.group(1).strip()
    return ''

def parse_m3u_to_blocks(text):
    entries, current_block = [], []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    current_block_start_index = -1
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            if current_block_start_index != -1:
                block = "\n".join(lines[current_block_start_index:i])
                if any(l.startswith('http') for l in block.splitlines()):
                    entries.append(block)
            
            temp_start = i
            while temp_start > 0 and not lines[temp_start - 1].startswith('http') and not lines[temp_start - 1].startswith('#EXTINF'):
                temp_start -= 1
            current_block_start_index = temp_start
    if current_block_start_index != -1:
        block = "\n".join(lines[current_block_start_index:])
        if any(l.startswith('http') for l in block.splitlines()):
            entries.append(block)
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
    
def check_and_return_block(block_text):
    lines = block_text.splitlines()
    url = ""
    original_headers = {}
    for line in lines:
        if '#EXTVLCOPT:http-user-agent=' in line: original_headers['User-Agent'] = line.split('=', 1)[1].strip()
        elif '#EXTVLCOPT:http-referrer=' in line: original_headers['Referer'] = line.split('=', 1)[1].strip()
        elif line.startswith('http'): url = line.split('|')[0].strip()
    if not url: return None
    def try_request(headers):
        try:
            with requests.get(url, headers=headers, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
                return 200 <= r.status_code < 300
        except requests.exceptions.RequestException: return False
    def build_new_block(working_ua):
        new_lines, ua_line_found = [], False
        for line in lines:
            if '#EXTVLCOPT:http-user-agent=' in line:
                new_lines.append(f'#EXTVLCOPT:http-user-agent={working_ua}')
                ua_line_found = True
            else: new_lines.append(line)
        if not ua_line_found:
            extinf_index = next((i for i, s in enumerate(new_lines) if s.startswith('#EXTINF')), -1)
            if extinf_index != -1: new_lines.insert(extinf_index + 1, f'#EXTVLCOPT:http-user-agent={working_ua}')
        return "\n".join(new_lines)
    current_ua = original_headers.get('User-Agent', 'Mozilla/5.0')
    if try_request(original_headers): return block_text
    for ua in FALLBACK_USER_AGENTS:
        if ua == current_ua: continue
        temp_headers = original_headers.copy()
        temp_headers['User-Agent'] = ua
        if try_request(temp_headers): return build_new_block(ua)
    return None

# --- SKRIP UTAMA ---
if __name__ == "__main__":
    print("➡️ Membaca file konfigurasi (channels.txt)...")
    channel_order, channel_meta = parse_channel_file(CHANNEL_FILE)
    
    print("\n➡️ Mengunduh semua sumber playlist...")
    src_texts = [text for u in URL_SRCS if (text := download_text(u))]

    src_dict = {}
    for text in src_texts:
        for block in parse_m3u_to_blocks(text):
            # ===== FILTER DIKEMBALIKAN SESUAI PERMINTAAN =====
            if '.mpd' in block.lower() and 'license_key' not in block.lower():
                continue
            
            name = extract_field(block)
            if not name: continue
            norm = normalize_name(name)
            src_dict.setdefault(norm, []).append(block)

    print(f"\n➡️ Menemukan {sum(len(v) for v in src_dict.values())} total stream. Memulai pengecekan...")
    working_blocks_map = {}
    all_blocks_to_check = [(norm, block) for norm, blocks in src_dict.items() for block in blocks]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_info = {executor.submit(check_and_return_block, block): norm for norm, block in all_blocks_to_check}
        for future in tqdm(as_completed(future_to_info), total=len(all_blocks_to_check), desc="Mengecek Channel"):
            norm, result_block = future_to_info[future], future.result()
            if result_block:
                working_blocks_map.setdefault(norm, []).append(result_block)

    print("\n➡️ Menyusun playlist akhir dari channel yang berfungsi...")
    
    final_blocks_to_write, unmatched_channels, used_streams = [], set(), set()

    for norm in channel_order:
        if norm in working_blocks_map:
            meta = channel_meta[norm]
            for block in working_blocks_map[norm]:
                lines = block.strip().splitlines()
                stream_url = next((line.split('|')[0].strip() for line in lines if line.startswith("http")), "")
                if not stream_url: continue
                license_key_line = next((line for line in lines if "license_key" in line.lower()), "")
                uniq_id = f"{stream_url}|{license_key_line}"
                if uniq_id in used_streams: continue
                used_streams.add(uniq_id)
                output_lines = []
                extinf_replaced = False
                for line in lines:
                    if line.startswith("#EXTINF") and not extinf_replaced:
                        tvg_id = meta['display_name'].replace(" ", "") + ".id"
                        logo_str = f' tvg-logo="{meta["tvg-logo"]}"' if meta["tvg-logo"] else ""
                        new_line = f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{meta["group-title"]}"{logo_str},{meta["display_name"]}'
                        output_lines.append(new_line)
                        extinf_replaced = True
                    elif not line.startswith("#EXTINF"):
                        output_lines.append(line)
                final_blocks_to_write.append("\n".join(output_lines))
        else:
             unmatched_channels.add(meta.get("display_name", norm))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(generate_header(len(final_blocks_to_write)))
        for block_str in final_blocks_to_write:
            f.write(block_str + "\n\n")

    if unmatched_channels:
        with open(UNMATCHED_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(list(unmatched_channels))))
        print(f"⚠️ {len(unmatched_channels)} channel tidak ditemukan. Lihat {UNMATCHED_FILE}")

    print(f"✅ Playlist selesai. {len(final_blocks_to_write)} channel berfungsi disimpan di '{OUTPUT_FILE}'.")
