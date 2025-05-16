import base64, re, sys, os
from pywidevine import PSSH, Cdm, Device
from utils.config import CONFIG

def get_wvd_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, CONFIG["WVD_FILE"])
    return os.path.join(os.getcwd(), CONFIG["WVD_FILE"])

def load_cdm(pssh_b64):
    if not pssh_b64:
        return None, None, None
    device = Device.load(get_wvd_path())
    if device.security_level != 3:
        return None, None, None
    pssh = PSSH(pssh_b64)
    if pssh.system_id == PSSH.SystemId.PlayReady:
        pssh.to_widevine()
    cdm = Cdm.from_device(device)
    session = cdm.open()
    challenge = cdm.get_license_challenge(session, pssh)
    return cdm, session, challenge

def parse_license(cdm, session, license_response):
    cdm.parse_license(session, license_response)
    keys = [f"{k.kid.hex}:{k.key.hex()}" for k in cdm.get_keys(session) if "CONTENT" in k.type]
    cdm.close(session)
    return keys

def extract_pssh(mpd, default_kid=None):
    if not default_kid:
        m = re.search(r'default_KID="([a-fA-F0-9-]+)"', mpd)
        if m:
            default_kid = m.group(1).replace("-","")
    if default_kid:
        raw = f'000000387073736800000000edef8ba979d64acea3c827dcd51d21ed000000181210{default_kid}48e3dc959b06'
        try:
            return base64.b64encode(bytes.fromhex(raw)).decode()
        except:
            pass
    pssh_list = re.findall(r"<[^>]*cenc:pssh[^>]*>(.*?)</", mpd)
    if pssh_list:
        return max(pssh_list, key=len)
    m = re.findall(fr'<ProtectionHeader[^>]*{CONFIG["PLAYREADY_ID"]}[^>]*>(.*?)</', mpd, re.DOTALL|re.IGNORECASE)
    return min(m, key=len) if m else None
