import re
import requests
import eel
from os.path import join
from requests.exceptions import HTTPError
from utils.config import CONFIG
from utils.common import Source, clean_url, get_valid_filename
from utils.cdm import extract_pssh
from utils.auth import load_session

PLATFORM = "BROWSER"

def _session_headers():
    session = load_session()
    headers = session.get("headers") or {}
    if not headers:
        raise Exception("❌ Aby używać programu musisz się zalogować")
    return headers.copy()

def get_keys(challenge, additional):
    headers = _session_headers()
    r = requests.post(additional["license_url"], data=challenge, headers=headers)
    if r.status_code == 403:
        raise Exception("🔒 Nie masz dostępu do treści")
    r.raise_for_status()
    return r.content

def has_playerplus():
    headers = _session_headers()
    r = requests.get(
        "https://player.pl/playerapi/subscriber/detail",
        params={"platform": PLATFORM},
        headers=headers
    )
    if r.status_code != 200:
        return False
    return r.json().get("status", {}).get("subscriptionModel", "").upper() == "SVOD"

def translate_id(content_id, force_program=False):
    headers = _session_headers()
    params_list = ("programId", "articleId") if force_program else ("articleId", "programId")
    for param in params_list:
        r = requests.get(
            "https://player.pl/playerapi/item/translate",
            params={param: content_id, "platform": PLATFORM},
            headers=headers
        )
        if r.status_code == 404:
            continue
        r.raise_for_status()
        return r.json().get("id")
    return None

def get_video_data(source: Source):
    headers = _session_headers()
    content_id = source.url.split(",")[-1]
    try:
        real_id = translate_id(content_id) or content_id
    except HTTPError as e:
        if not (e.response and e.response.status_code == 404):
            raise
        real_id = content_id

    r = requests.get(
        f"https://player.pl/playerapi/product/vod/{real_id}",
        params={"4K": "true", "platform": PLATFORM},
        headers=headers
    )
    if r.status_code == 403:
        raise Exception("🔒 Nie masz dostępu do treści")
    r.raise_for_status()
    info = r.json()

    share_url = info.get("shareUrl", "")
    tid = share_url.replace("https://player.pl/", "").replace(",", "_").replace("-", "_").replace("/", "_")
    r = requests.get(
        f"https://player.pl/playerapi/item/{real_id}/playlist",
        params={"type":"MOVIE","page":tid,"4K":"true","platform":PLATFORM},
        headers=headers
    )
    if r.status_code == 403:
        raise Exception("🔒 Nie masz dostępu do treści")
    r.raise_for_status()
    movie = r.json().get("movie", {}) or {}
    if movie.get("payable") and not has_playerplus():
        raise Exception("🔒 Nie masz dostępu do treści")

    if not source.element:
        info = movie.get("info", {})
        stats = movie.get("stats", {}).get("nl_data", {})

        ep_num = info.get("episode_number")
        ep_title = stats.get("title") or info.get("title") or source.url.split("/")[-1]

        if ep_num:  # tylko jeśli istnieje numer odcinka
            full_title = f"Ep{int(ep_num):02}_{ep_title}"
        else:
            full_title = ep_title

        source.element = get_valid_filename(full_title)


    if not source.collection:
        source.collection = join(CONFIG["OUTPUT"]["DIR"], "player_pl")

    video = movie.get("video", {})
    protections = video.get("protections")
    if protections:
        license_url = protections["widevine"]["src"] or ""
        manifest = video["sources"]["dash"]["url"]
        mpd = requests.get(manifest, headers=headers).text
        pssh = extract_pssh(mpd) or extract_pssh(
            requests.get(video["sources"].get("smooth",{}).get("url",""), headers=headers).text
        )
        if not pssh:
            raise Exception("[404] Brak wspieranego PSSH")
    else:
        srcs = video.get("sources", {})
        first = next(iter(srcs.values()), {})
        manifest = first.get("url")
        license_url = ""
        pssh = None

    return manifest, pssh, {"license_url": license_url, "URL": source.url}

def get_collection_elements(url):
    headers = _session_headers()
    url = clean_url(url)

    ep_re     = r',S\d+E\d+,\d+$'
    series_re = r'-odcinki,\d+$'

    is_episode = bool(re.search(ep_re, url))
    is_movie   = "/filmy-online" in url
    is_series  = bool(re.search(series_re, url))

    if "/live/" in url:
        raise Exception("🚫 Nie można pobierać materiałów na żywo")

    # pojedynczy odcinek lub film
    if is_episode or is_movie:
        src = Source(url)
        get_video_data(src)
        return [src]

    # cała seria/program/strefa sportu
    if is_series:
        eel.update_status("🔄 Przechwytywanie całego katalogu (może to chwilę potrwać)")
        content_id = url.split(",")[-1]

        series_id = translate_id(content_id, force_program=True)
        if not series_id:
            series_id = translate_id(content_id, force_program=False)
        if not series_id:
            series_id = content_id

        # tytuł serii
        r = requests.get(
            f"https://player.pl/playerapi/product/vod/serial/{series_id}",
            params={"platform": PLATFORM},
            headers=headers
        )
        if r.status_code == 404:
            raise Exception("❌ Seria nie istnieje lub brak dostępu")
        r.raise_for_status()
        title = r.json().get("title", f"series_{series_id}")
        base = join(CONFIG["OUTPUT"]["DIR"], "player_pl", get_valid_filename(title))

        # lista sezonów
        r = requests.get(
            f"https://player.pl/playerapi/product/vod/serial/{series_id}/season/list",
            params={"platform": PLATFORM},
            headers=headers
        )
        r.raise_for_status()
        seasons = sorted(r.json(), key=lambda s: s["number"])

        episodes = []
        for season in seasons:
            sid, num = season["id"], season["number"]
            try:
                r2 = requests.get(
                    f"https://player.pl/playerapi/product/vod/serial/{series_id}/season/{sid}/episode/list",
                    params={"platform": PLATFORM},
                    headers=headers
                )
                r2.raise_for_status()
            except HTTPError as e:
                if e.response and e.response.status_code == 403:
                    eel.update_status("🔒 Nie masz dostępu do niektórych odcinków. Zablokowane sezony zostaną pominięte")
                continue

            for ep in sorted(r2.json(), key=lambda e: e["episode"]):
                ep_num = ep.get("episode", 0)
                ep_title = ep.get("title", "no-title")
                name = f'S{num:02}E{ep_num:02}_{ep_title}'
                episodes.append(Source(
                    url=ep["shareUrl"],
                    collection=join(base, f"Season_{num}"),
                    element=get_valid_filename(name)
                ))


        return episodes

    raise Exception(f"❌ Nie można przetworzyć URL: {url}")
