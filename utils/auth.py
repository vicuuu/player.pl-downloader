import requests, json, os, eel
from utils.config import CONFIG

AUTH_URL="https://oauth.account.tvn.pl/"
BASE_URL="https://player.pl/"
CLIENT_ID="Player_TV_Android_28d3dcc063672068"
PLATFORM="ANDROID_TV"
UA="playerTV/2.2.2 (455) (Linux; Android 8.0.0; Build/sdk_google_atv_x86)"
SESSION_FILE="output/session.json"
HEADERS={"User-Agent":UA,"accept-encoding":"gzip"}
login_state={"code":None}

def save_session(data):
    with open(SESSION_FILE,"w",encoding="utf-8") as f:
        json.dump(data,f,indent=2)
    eel.update_status("✅ Zapisano dane sesyjne")

def load_session():
    if not os.path.exists(SESSION_FILE):
        return {}
    with open(SESSION_FILE,"r",encoding="utf-8") as f:
        return json.load(f)

def logout():
    with open(SESSION_FILE,"w",encoding="utf-8") as f:
        f.write("{}")
    eel.update_status("🚪 Wylogowano")

def generate_code():
    r = requests.post(f"{AUTH_URL}tvn-reverse-onetime-code/create?platform={PLATFORM}", headers=HEADERS, data={"scope":"/pub-api/user/me","client_id":CLIENT_ID})
    r.raise_for_status()
    return r.json().get("code")

def exchange_code_for_token(code):
    r = requests.post(
        f"{AUTH_URL}token?platform={PLATFORM}",
        headers=HEADERS,
        data={
            "grant_type": "tvn_reverse_onetime_code",
            "code": code,
            "client_id": CLIENT_ID
        }
    )
    eel.update_status(f"📡 Wymiana kodu na token... ({r.status_code})")
    if r.status_code != 400:
        r.raise_for_status()
    return r.json()


def get_profile_info(token):
    headers = {**HEADERS, "api-authentication":token, "api-deviceuid":"test-device-id", "api-deviceinfo":"sdk_google_atv_x86;unknown;Android;8.0.0;Unknown;2.2.2 (455);"}
    r = requests.post(f"{BASE_URL}playerapi/subscriber/login/token?4K=true&platform={PLATFORM}", headers=headers, json={"agent":"sdk_google_atv_x86","agentVersion":UA,"appVersion":"2.2.2 (455)","maker":"Unknown","os":"Android","osVersion":"8.0.0","token":token,"uid":"test-device-id"})
    r.raise_for_status()
    return r.json(), headers

def refresh_token():
    session=load_session()
    token=session.get("refresh_token")
    if not token:
        logout()
        raise Exception("Brak refresh_token — zaloguj się ponownie.")
    r = requests.post(f"{AUTH_URL}token?platform={PLATFORM}", headers=HEADERS, data={"grant_type":"refresh_token","refresh_token":token,"client_id":CLIENT_ID})
    if r.status_code!=200:
        logout()
        raise Exception("Nie udało się odświeżyć tokena")
    t=r.json()
    session.update({"access_token":t["access_token"],"refresh_token":t["refresh_token"],"user_hash":t.get("user_hash",""),"user_pub":t.get("user_pub","")})
    save_session(session)
    return session

def auth_check(r):
    if isinstance(r,dict) and r.get("code") in ("OAUTH_TOKEN_INVALID","AUTHENTICATION_REQUIRED"):
        if r["code"]=="OAUTH_TOKEN_INVALID":
            eel.update_status("🔁 Access token wygasł — odświeżam...")
            refresh_token()
            return False
        logout()
        raise Exception("🔒 Sesja wygasła — zaloguj się ponownie")
    return True

@eel.expose
def login():
    code=generate_code()
    if not code:
        eel.update_status("❌ Nie udało się wygenerować kodu")
        return
    login_state["code"]=code
    eel.update_status(f"➡️ Wejdź na: https://player.pl/generuj-kod-tv Kod: {code}")
    eel.update_status("🕐 Kliknij '✅ Potwierdziłem' po aktywacji kodu")

@eel.expose
def confirm_login():
    code=login_state.get("code")
    if not code:
        eel.update_status("❌ Brak aktywnego kodu")
        return
    tokens=exchange_code_for_token(code)
    if "access_token" not in tokens:
        eel.update_status("❌ Nie udało się uzyskać tokena")
        eel.update_status(str(tokens))
        return
    profile_data, headers = get_profile_info(tokens["access_token"])
    if "profile" not in profile_data:
        eel.update_status("❌ Błąd pobierania profilu")
        eel.update_status(str(profile_data))
        return
    session = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "user_hash": tokens.get("user_hash",""),
        "user_pub": tokens.get("user_pub",""),
        "profile_uid": profile_data["profile"]["externalUid"],
        "headers": headers
    }
    save_session(session)
    eel.update_status("✅ Zalogowano pomyślnie!")
    user = player_login()
    eel.on_login_success(user["username"])

def player_login():
    session=load_session()
    if not session.get("access_token") or not session.get("headers"):
        raise Exception("Brak aktywnej sesji")
    r = requests.get(f"{BASE_URL}playerapi/subscriber/detail?platform=BROWSER", headers=session["headers"])
    data=r.json()
    if not auth_check(data):
        session=refresh_token()
        r=requests.get(f"{BASE_URL}playerapi/subscriber/detail?platform=BROWSER", headers=session["headers"])
        r.raise_for_status()
        data=r.json()
    profiles=data.get("profiles",[])
    if not profiles:
        logout()
        raise Exception("❌ Sesja wygasła lub użytkownik nie istnieje")
    username="Nieznany użytkownik"
    for p in profiles:
        if p.get("externalUid")==session.get("profile_uid"):
            username=p.get("name",username)
            break
    return {"username":username}
