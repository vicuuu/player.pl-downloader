import random, string, re
from os.path import join
from urllib.parse import urlparse
from itertools import chain
from unidecode import unidecode

def is_http_url(url):
    return isinstance(url,str) and url.startswith(("http://","https://"))

def clean_url(url):
    return url.split("?")[0].split("#")[0].rstrip("/")

def rand_str(length=7):
    return ''.join(random.choices(string.ascii_letters+string.digits,k=length))

def get_valid_filename(name):
    if not name:
        return None
    s = unidecode(name)
    s = re.sub(r"[^\w\s.-]","",s).strip().replace(" ","_")
    s = re.sub(r"_+","_",s).strip("._")
    return s or None

def split_chunks(lst,n):
    k = max(1,len(lst)//n)
    return [lst[i:i+k] for i in range(0,len(lst),k)]

def list_to_file(path,lines):
    with open(path,"w",encoding="utf-8") as f:
        for l in lines:
            f.write(l.strip()+"\n")

class Source:
    def __init__(self,url,collection=None,element=None):
        self.url, self.collection, self.element = url, collection, element
