> [!IMPORTANT]
> **This repository has moved.** The EPG generator now lives in the app monorepo
> **https://github.com/DimaKarma/iptv-roku** under `epg/`. EPG data is published to that
> repo's `epg-data` branch:
> `https://raw.githubusercontent.com/DimaKarma/iptv-roku/epg-data/epg.json`.
> This repository is archived and no longer updated.

# iptv-epg — компактный EPG для IPTV-плеера на Roku

Генератор программы передач (EPG) для домашнего IPTV-приложения на Hisense Roku TV.

## Зачем
Провайдерский плейлист не содержит `url-tvg` и `tvg-id`, а полный XMLTV (десятки МБ gzip,
сотни МБ распакованного) телевизор Roku не может ни распаковать, ни распарсить.
Поэтому конвертация вынесена в GitHub Actions, а на ТВ отдаётся компактный `epg.json`.

## Как работает
1. `generate_epg.py` потоково скачивает публичный XMLTV `http://epg.it999.ru/epg.xml.gz`.
2. Сопоставляет каналы из `channels.txt` (только имена из плейлиста, без токенов/подписки)
   с каналами XMLTV по нормализованному имени (совпадение ~99%).
3. Вырезает окно `now-2ч .. now+18ч` и пишет `epg.json`, где ключ — ТОЧНОЕ имя канала из плейлиста.
4. Workflow `.github/workflows/epg.yml` запускает генератор по расписанию (каждые 2 часа)
   и коммитит свежий `epg.json`.

## Использование в приложении
В настройках IPTV-плеера указать URL EPG:
```
https://raw.githubusercontent.com/<USER>/iptv-epg/main/epg.json
```
Приложение тянет маленький JSON и показывает «сейчас/далее» по имени канала.

## Формат epg.json
```json
{
  "generated": 1721140000,
  "count": 1045,
  "epg": {
    "Первый канал FHD": [ {"s": 1721140000, "e": 1721143600, "t": "Новости"} ]
  }
}
```
`s`/`e` — Unix-время (UTC) начала/конца передачи, `t` — заголовок.

## Приватность
В репозитории только публичные данные: имена каналов и готовый EPG. Токен подписки и URL плейлиста НЕ хранятся.

## Ручной запуск
Вкладка **Actions → Generate EPG → Run workflow**. Или локально: `python generate_epg.py`.

## Источник EPG
`epg.it999.ru` — публичный XMLTV для русскоязычных каналов. При смене источника — поправить `XMLTV_URL` в `generate_epg.py`.
