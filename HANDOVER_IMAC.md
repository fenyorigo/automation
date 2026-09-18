# Fejlesztői handover az iMac Codex számára

Frissítve: 2026-08-28 (Europe/Budapest)

## Küldetés és jelenlegi állapot

Ez a repository egy helyi otthonautomatizálási rendszer: Flask dashboard,
MariaDB-adattárolás, periodikus eszközlekérdezés, auditált klímavezérlés,
determinisztikus riportok és egy ESP32/DS18B20 firmware-prototípus.

A fejlesztést ezentúl az iMacen kell folytatni. A forrás aktuális Git-állapota a
handover készítésekor:

```text
remote: git@github.com:fenyorigo/automation.git
branch: main
HEAD:   69cafd9 Add Linux deployment and remote system monitoring
sync:   main == origin/main
worktree: tiszta a HANDOVER_IMAC.md létrehozása előtt
```

Az alkalmazás kiadása a `README.md` és `CHANGELOG.md` szerint **1.1.0**, viszont
a `VERSION` fájl még **1.0.0**. Ez ismert inkonzisztencia; a következő
verziózási munka részeként rendezendő.

A legutóbbi nagy változás a Fedora telepítés és a helyi/távoli Linux
rendszermetrikák támogatása volt. Az adatbázis migrációs lánca jelenleg
`v1_31_linux_system_metrics`-ig tart.

## Fontos üzemeltetési kép

A `docs/porting-to-linux.md` alapján az üzemszerű futtatás átkerült/átkerül a
`think260x` Fedora gépre, `/var/www/automation` alá, a dashboard 8082-es
portjára. Ezt az iMacen az első munka előtt ellenőrizd; ne feltételezd, hogy az
iMacnek kell éles pollert futtatnia.

A forrásgépen a handover készítésekor:

- a macOS `hu.bajanp.automation-dashboard` LaunchAgent futott;
- a `hu.bajanp.automation-poller` LaunchAgent nem volt betöltve;
- a dokumentált végleges adatbázis-dump:
  `exports/home_automation_20260827T070417Z.sql.gz`;
- a tényleges `config/devices.json`, `.env`, `.dashboard-secret`, `exports/`
  és `logs/` nincs Gitben.

**Biztonsági invariáns:** egyszerre csak egy üzemi periodikus poller fusson.
Költözés vagy adatbázis-visszaállítás alatt kézi pollingot se indíts. Az iMacen
a pollert csak akkor töltsd be, ha bizonyítottan ez lesz az új üzemi gép és a
régi/Fedora poller már leállt. A dashboard önmagában futhat poller nélkül.

## Mit kell átvinni az iMacre

### 1. Verziózott forrás

```sh
git clone git@github.com:fenyorigo/automation.git ~/Projects/automation
cd ~/Projects/automation
git status --short --branch
git log -1 --oneline --decorate
```

Ha ez a handover fájl még nincs commitolva és pusholva, külön másold át vagy
előbb commitold a forrásgépen.

### 2. Nem verziózott, szükséges helyi állományok

Biztonságos csatornán másolandó, a Gitbe továbbra sem tehető:

- `.env` — adatbázis- és ConnectLife-hitelesítők, futási beállítások;
- `config/devices.json` — valós eszközazonosítók és hálózati adatok;
- `.dashboard-secret` — akkor másold, ha a meglévő Flask munkamenetek/titok
  megtartása kívánatos; különben az alkalmazás létre tud hozni újat;
- szükség esetén a legfrissebb adatbázis-dump az `exports/` könyvtárból;
- kizárólag ha fejlesztési szempontból kell: korábbi exportok és naplók.

Ajánlott jogosultságok az iMacen:

```sh
chmod 600 .env .dashboard-secret config/devices.json
```

A `.venv` könyvtárat ne másold: géphez, Python-verzióhoz és abszolút
útvonalakhoz kötött. A naplókat és generált exportokat sem szükséges teljes
egészében átvinni.

## iMac fejlesztői környezet felépítése

Előfeltételek: Python 3, MariaDB kliens/Connector C, MariaDB szerver vagy elért
adatbázis, továbbá gnuplot. Apple Silicon Homebrew esetén a gnuplot tipikus
helye `/opt/homebrew/bin/gnuplot`; Intel iMacen ez gyakran
`/usr/local/bin/gnuplot`. Mindig `command -v gnuplot` alapján állítsd be.

```sh
cd ~/Projects/automation
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env                 # csak ha a valódi .env még nincs átmásolva
cp config/devices.example.json config/devices.json  # csak üres fejlesztői induláshoz
```

Az átmásolt `.env` abszolút útvonalait igazítsd az iMachez, különösen:

- `GNUPLOT_BIN`;
- `MARIADB_DUMP_BIN`;
- `DATABASE_BACKUP_DIR`;
- szükség esetén `DB_HOST`, `DB_SOCKET` és `DASHBOARD_PORT`.

Ne írj valódi titkot dokumentációba, commitba vagy Codex-válaszba.

## Adatbázis

Üres fejlesztői adatbázis létrehozásához/felépítéséhez:

```sh
.venv/bin/python app/migrate_database.py
```

A migráló idempotens, az alkalmazott lépéseket a `schema_migrations` táblában
tartja nyilván. Egy éles dump visszaállítása adatokat és hitelesítési hasheket
is tartalmazhat; csak megfelelően védett helyi adatbázisba importáld. A
visszaállítás pontos menete és a 2026-08-27-i dump részletei:
`docs/porting-to-linux.md`.

Adatbázis-módosítás előtt készíts mentést. A generált `*.sql`, `*.sql.gz` és
az `exports/` szándékosan ignorált.

## Indítás és ellenőrzés

Fejlesztői dashboard:

```sh
.venv/bin/python app/dashboard.py
```

Alapértelmezett macOS cím: `http://localhost:8081`; a `/health` végpont a
gnuplot állapotát is jelzi.

Csak olvasó, adatbázisba nem mentő eszközteszt:

```sh
.venv/bin/python app/poll_devices.py --summary
```

Az alábbi parancs már **ír az adatbázisba**, ezért csak tudatosan használd:

```sh
.venv/bin/python app/poll_devices.py --store --summary
```

A tesztek `unittest` alapúak; a jelenlegi környezetben a `pytest` nincs a
projekt követelményei között. Függőségek telepítése után a hordozható ellenőrzés:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

ESP32 firmware ellenőrzéséhez PlatformIO szükséges:

```sh
cd esp32/poc-ds18b20
pio run
```

## macOS LaunchAgentek

A minták:

- `deploy/macos/hu.bajanp.automation-dashboard.plist`
- `deploy/macos/hu.bajanp.automation-poller.plist`

Jelenleg abszolút `/Users/bajanp/Projects/automation/...` útvonalakat
tartalmaznak. Ha az iMacen más a felhasználónév vagy a checkout helye, telepítés
előtt minden `ProgramArguments`, `WorkingDirectory` és naplóútvonalat át kell
írni. A módosított plist a `~/Library/LaunchAgents/` könyvtárba kerül.

A szolgáltatások kezelésének és ellenőrzésének részletes parancsai:
`docs/polling.md`. A poller betöltésére továbbra is érvényes az egyetlen üzemi
poller szabály.

## Kódtérkép

- `app/dashboard.py` — Flask alkalmazás és route-ok;
- `app/database.py` — MariaDB elérés és adatkezelés;
- `app/poll_devices.py` — eszközadapterek és egy pollingkör;
- `app/poll_scheduler.py` — periodikus polling és napi backup;
- `app/climate_control.py`, `app/scheduled_climate.py` — auditált klímaműveletek;
- `app/temperature_derivation.py` — kalibrált/cselekedeti hőmérséklet;
- `app/deterministic_report.py` — LLM nélküli, csak olvasó riportok;
- `app/templates/`, `app/static/` — webes UI;
- `SQL/migrations/` — egymásra épülő adatbázis-migrációk;
- `esp32/poc-ds18b20/` — PlatformIO firmware;
- `deploy/` — macOS LaunchAgent és Fedora systemd minták;
- `tests/` — regressziós tesztek;
- `docs/` — üzemeltetési, használati és döntési dokumentáció.

Elsőként olvasandó: `README.md`, `CHANGELOG.md`, `docs/polling.md`,
`docs/hasznalati-utasitas.md`, `docs/porting-to-linux.md` és az adott feladathoz
kapcsolódó célzott dokumentum.

## Ismert kockázatok és nyitott ellenőrzések

1. Döntsd el és dokumentáld, hogy az iMac csak fejlesztői gép, vagy később
   üzemi host is lesz. Ez határozza meg a poller és az éles adatbázis sorsát.
2. Ellenőrizd a `think260x` aktuális éles állapotát, mielőtt bármely másik
   gépen pollert indítasz.
3. Rendezd a `VERSION` (1.0.0) és a dokumentált release (1.1.0) eltérését.
4. A `requirements.txt` nincs verziókra rögzítve; reprodukálható telepítéshez
   vizsgáld meg a `requirements-lock.txt` aktualitását.
5. A plist minták abszolút útvonalai gépfüggők.
6. Valós eszközök vezérlése előtt ellenőrizd a jogosultságot, a preflightot és
   az utóellenőrzést; a riportkód maradjon csak olvasó és vezérlésképtelen.

## Ajánlott első iMac Codex-menet

1. `git status`, `git log -1`, Python- és architektúra-ellenőrzés.
2. A nem verziózott fájlok meglétének ellenőrzése az értékük kiírása nélkül.
3. Új `.venv`, függőségek, majd teljes `unittest` futtatás.
4. Adatbázis-kapcsolat és `schema_migrations` ellenőrzése.
5. Dashboard kézi indítása és `/health` ellenőrzése.
6. Csak ezután célzott fejlesztés; pollert és eszközvezérlést ne indíts
   automatikusan.

Minden munkánál őrizd meg a felhasználó nem commitolt változtatásait, a
titkokat ne jelenítsd meg, adatbázis- vagy eszközmódosítás előtt pedig jelezd a
hatást és készíts visszaállítási pontot.
