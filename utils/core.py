from os.path import join
from utils.config import CONFIG
from utils.common import Source, is_http_url, rand_str, list_to_file, split_chunks
from utils.cdm import load_cdm, parse_license
from service import get_keys, get_video_data, get_collection_elements

def generate_download_command(source, manifest, keys):
    t = CONFIG["TOOL"]
    cmd = t["BASE"].replace("[!manifest!]", manifest).replace("[!collection!]", source.collection).replace("[!element!]", source.element)
    key_args = " ".join(t["KEY"].format(value=k) for k in keys) if keys else ""
    return cmd.replace("[!keys!]", key_args).strip()

def process_source(src):
    manifest, pssh, additional = get_video_data(src)

    # fallback na tytuł z URL
    if src.element and "_" not in src.element:
        ep_title = src.url.split("/")[-1].split(",")[0].replace("-", "_")
        src.element = f"{src.element}_{ep_title}"

    keys = []
    if pssh:
        cdm, session, challenge = load_cdm(pssh)
        if cdm:
            resp = get_keys(challenge, additional)
            keys = parse_license(cdm, session, resp)
    return generate_download_command(src, manifest, keys)


def run(urls):
    download_cmds, failed = [], []
    all_src = []
    for url in urls:
        if is_http_url(url):
            all_src += get_collection_elements(url)
        else:
            failed.append(url)
    for batch in split_chunks(all_src, CONFIG["THREADS"]["SCRAPER"]):
        for src in batch:
            try:
                cmd = process_source(src)
                download_cmds.append(cmd)
            except:
                failed.append(src.url)
    list_to_file(CONFIG["OUTPUT"]["CMD_FILE"], download_cmds)
    list_to_file(CONFIG["OUTPUT"]["FAILED_FILE"], failed)
    print(f"- Zapisano {len(download_cmds)}")
    if failed:
        print(f"- {len(failed)} nie zapisano")
