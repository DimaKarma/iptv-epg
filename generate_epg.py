#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор компактного EPG (epg.json) для IPTV-плеера на Roku.

- Скачивает публичный XMLTV (epg.it999.ru) потоково.
- Сопоставляет каналы из channels.txt (имена из плейлиста, без токена) с каналами XMLTV
  по нормализованному имени (без tvg-id).
- Вырезает окно передач now-2ч .. now+18ч и пишет epg.json,
  КЛЮЧАМИ которого служат ТОЧНЫЕ имена каналов из channels.txt
  (приложению на Roku нормализация не нужна — простой lookup epg[name]).

Формат epg.json:
{
  "generated": <utc epoch>,
  "count": <число каналов с EPG>,
  "epg": { "<имя канала>": [ {"s": startEpoch, "e": stopEpoch, "t": "Заголовок"}, ... ], ... }
}
"""
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

XMLTV_URL = "http://epg.it999.ru/epg.xml.gz"
WINDOW_BEHIND = 2 * 3600     # 2 часа назад
WINDOW_AHEAD = 18 * 3600     # 18 часов вперёд
HTTP_TIMEOUT = 180

_QUALITY_RE = re.compile(r'\b(fhd|uhd|hd|sd|4k)\b')
_SHIFT_RE = re.compile(r'\+\d+')
_KEEP_RE = re.compile(r'[^0-9a-zа-яёіїєґ]')


def norm(s):
    """Нормализация имени для матчинга (используется только внутри генератора)."""
    if not s:
        return ""
    s = s.lower()
    s = _SHIFT_RE.sub('', s)
    s = _QUALITY_RE.sub('', s)
    s = _KEEP_RE.sub('', s)
    return s


def parse_xmltv_time(t):
    """'20260716120000 +0300' -> utc epoch (int)."""
    t = (t or "").strip()
    if len(t) < 14:
        return None
    dt = datetime.strptime(t[:14], "%Y%m%d%H%M%S")
    epoch = int(dt.replace(tzinfo=timezone.utc).timestamp())
    # применить смещение зоны, если есть ('+0300' / '-0500')
    rest = t[14:].strip()
    if len(rest) >= 5 and rest[0] in '+-':
        sign = 1 if rest[0] == '+' else -1
        off = int(rest[1:3]) * 3600 + int(rest[3:5]) * 60
        epoch -= sign * off
    return epoch


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ch_path = os.path.join(here, "channels.txt")
    out_path = os.path.join(here, "epg.json")

    names = [ln.strip() for ln in open(ch_path, encoding="utf-8") if ln.strip()]
    # нормализованное имя -> точное имя из плейлиста (первое совпадение выигрывает)
    norm_to_name = {}
    for nm in names:
        key = norm(nm)
        if key and key not in norm_to_name:
            norm_to_name[key] = nm

    now = int(time.time())
    lo, hi = now - WINDOW_BEHIND, now + WINDOW_AHEAD

    print("Downloading %s ..." % XMLTV_URL)
    req = urllib.request.Request(XMLTV_URL, headers={"User-Agent": "epg-gen/1.0"})
    resp = urllib.request.urlopen(req, timeout=HTTP_TIMEOUT)
    gz = gzip.GzipFile(fileobj=resp)

    chan_to_name = {}   # xmltv channel id -> точное имя канала
    name_has_cid = set()  # имена, у которых уже выбран один фид (чтобы не мержить +2/+4)
    epg = {}
    n_prog = 0

    ctx = ET.iterparse(gz, events=("end",))
    for ev, el in ctx:
        tag = el.tag
        if tag == "channel":
            cid = el.get("id")
            for dn in el.findall("display-name"):
                key = norm(dn.text or "")
                if key in norm_to_name:
                    nm = norm_to_name[key]
                    # берём только ПЕРВЫЙ фид на канал (первый в порядке XMLTV)
                    if nm not in name_has_cid:
                        chan_to_name[cid] = nm
                        name_has_cid.add(nm)
                    break
            el.clear()
        elif tag == "programme":
            cid = el.get("channel")
            nm = chan_to_name.get(cid)
            if nm is not None:
                s = parse_xmltv_time(el.get("start"))
                e = parse_xmltv_time(el.get("stop"))
                if s is not None and e is not None and e >= lo and s <= hi:
                    title_el = el.find("title")
                    title = (title_el.text if title_el is not None else "") or ""
                    epg.setdefault(nm, []).append({"s": s, "e": e, "t": title})
                    n_prog += 1
            el.clear()

    for nm in epg:
        epg[nm].sort(key=lambda p: p["s"])

    out = {"generated": now, "count": len(epg), "epg": epg}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(out_path)
    print("Matched channels with EPG: %d / %d" % (len(epg), len(names)))
    print("Programmes in window: %d" % n_prog)
    print("epg.json size: %.2f MB" % (size / 1024.0 / 1024.0))


if __name__ == "__main__":
    main()
