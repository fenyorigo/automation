# Az automation alkalmazás portolása Fedora Linuxra

## Cél és kialakítás

Az üzemszerű alkalmazás helye a `think260x` Fedora gépen:

```text
/var/www/automation
```

Az adatbázismentések helye:

```text
/var/backups/automation
```

Az alkalmazást egy külön, bejelentkezésre nem használható `automation`
rendszerfelhasználó futtatja. Az Apache-felhasználó nem futtatja közvetlenül
sem a dashboardot, sem a pollert. A dashboard a Linuxon a `8082/tcp` portot
használja, mert a `8081/tcp` porton a qBittorrent WebUI működik.

A migráció alapelve, hogy egyszerre csak egy periodikus poller írhatja az
adatbázist. A Mac pollerét ezért a végleges adatbázismentés előtt le kell
állítani, a Linux pollerét pedig csak a sikeres adatbázis-import és a dashboard
ellenőrzése után szabad elindítani.

## 1. Az alkalmazás átvitele

A forrás letölthető Gitből, vagy átvihető archívumban. A macOS alatt létrehozott
`.venv` nem másolható át Linuxra, mert operációs rendszerhez, processzor-
architektúrához, Python-verzióhoz és abszolút útvonalakhoz kötött fájlokat is
tartalmaz.

Archívum készítésekor legalább a következőket kell kihagyni:

```sh
tar --exclude='.venv' --exclude='logs' --exclude='exports' \
  -czf automation.tar.gz automation
```

A tisztább megoldás a repository klónozása:

```sh
git clone git@github.com:fenyorigo/automation.git /var/www/automation
```

## 2. Fedora-függőségek és virtuális környezet

A Python virtuális környezet Fedora alatt is szükséges az alkalmazás
függőségeinek a rendszer-Pythontól való elkülönítéséhez. Nem a Homebrew miatt
használjuk, és a Mac `.venv` könyvtárát nem hasznosítjuk újra.

Szükséges Fedora-csomagok:

```sh
dnf install python3 python3-pip python3-devel gcc \
  pkgconf-pkg-config mariadb-connector-c-devel
```

A `mariadb-connector-c-devel` biztosítja a MariaDB Python-modul fordításához
szükséges `mariadb_config` programot. Ennek hiánya a következő hibát okozza:

```text
OSError: mariadb_config not found
```

Ellenőrzése:

```sh
command -v mariadb_config
mariadb_config --cc_version
```

A Linux virtuális környezet létrehozása és feltöltése:

```sh
cd /var/www/automation
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

## 3. Linux rendszerfelhasználó és fájljogosultságok

A szolgáltatások külön, `nologin` rendszerfelhasználóval futnak:

```sh
useradd --system \
  --home-dir /var/www/automation \
  --shell /usr/sbin/nologin \
  automation
```

Ellenőrzés:

```sh
getent passwd automation
```

A könyvtárak és a `.env` jogosultságai:

```sh
mkdir -p /var/backups/automation
chown -R automation:automation /var/www/automation
chown -R automation:automation /var/backups/automation
chmod 700 /var/backups/automation
chmod 600 /var/www/automation/.env
```

A `.env` az `automation` felhasználó tulajdona, mert a dashboard Globális
beállítások oldala nemcsak olvassa, hanem atomikusan módosíthatja is.

## 4. Linux-specifikus `.env`

A Mac `.env` fájlja kiindulásként használható, de legalább az útvonalakat, a
programok helyét és a dashboard portját át kell írni. A lényeges Linux-értékek:

```dotenv
DB_HOST=localhost
DB_PORT=3306
DB_NAME=home_automation
DB_USER=automation
DB_PASSWORD=EROS_EGYEDI_JELSZO

DASHBOARD_PORT=8082
APP_TIMEZONE=Europe/Budapest
GNUPLOT_BIN=/usr/bin/gnuplot
MARIADB_DUMP_BIN=/usr/bin/mariadb-dump
DATABASE_BACKUP_DIR=/var/backups/automation
```

A titkokat tartalmazó `.env` nem kerülhet Gitbe. A `DASHBOARD_PORT` induláskor
rögzül, ezért a módosítása után újra kell indítani a dashboardot.

### 4.1. Futó eszközkonfiguráció átvitele

A tényleges `config/devices.json` szándékosan szerepel a `.gitignore` fájlban,
ezért Git-klónozáskor csak a `devices.example.json` érkezik meg. Az adatbázis
eszköznyilvántartása nem helyettesíti teljesen ezt a fájlt: a poller ebből
olvassa többek között a forrásrendszer-specifikus azonosítókat és elérési
adatokat.

A Mac aktuális konfigurációját külön kell átmásolni:

```sh
scp /Users/bajanp/Projects/automation/config/devices.json \
  root@think260x:/var/www/automation/config/devices.json
```

Az X260-on:

```sh
chown automation:automation /var/www/automation/config/devices.json
chmod 600 /var/www/automation/config/devices.json
```

Ellenőrzés:

```sh
sudo -u automation test -r /var/www/automation/config/devices.json
echo $?
```

A várt eredmény `0`. A fájl hiányában a kézi és a periodikus lekérdezés is a
`No such file or directory: '/var/www/automation/config/devices.json'` hibával
leáll.

## 5. MariaDB-adatbázis és alkalmazásfelhasználó

A Linux rendszerfelhasználó és a MariaDB-felhasználó két külön azonosító,
akkor is, ha mindkettő neve `automation`.

Belépés MariaDB-adminisztrátorként:

```sh
mariadb
```

Az adatbázis és a kizárólag ahhoz hozzáférő felhasználó létrehozása:

```sql
CREATE DATABASE IF NOT EXISTS home_automation
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'automation'@'localhost'
  IDENTIFIED BY 'EROS_EGYEDI_JELSZO';

GRANT ALL PRIVILEGES
  ON home_automation.*
  TO 'automation'@'localhost';

FLUSH PRIVILEGES;
```

A MariaDB-jelszónak egyeznie kell a `.env` `DB_PASSWORD` értékével. A fenti
jogosultság csak a `home_automation` adatbázisra vonatkozik, nem ad általános
MariaDB-adminisztrátori hozzáférést.

Üres telepítésnél az aktuális séma az ismételten futtatható migrációs
programmal hozható létre:

```sh
cd /var/www/automation
sudo -u automation .venv/bin/python app/migrate_database.py
```

A migrációkat a `schema_migrations` tábla tartja nyilván.

## 6. A dashboard első, helyi tesztje

A dashboard kézzel, az üzemi felhasználó nevében indítható:

```sh
cd /var/www/automation
sudo -u automation .venv/bin/python app/dashboard.py
```

A validált Linux-kimenet:

```text
Running on http://127.0.0.1:8082
Running on http://192.168.1.102:8082
```

A Flask minden IPv4-interfészen figyel; a helyi LAN-ról az alkalmazást a
`think260x` LAN-címén kell elérni:

```text
http://192.168.0.1:8082/
```

Helyi ellenőrzés:

```sh
curl -I http://127.0.0.1:8082/
```

A várt eredmény `HTTP/1.1 302 FOUND`, `Location: /login`. Az üres adatbázis
esetén a felület az első szerkesztő helyi létrehozását kéri. Migráció közben
nem kell ideiglenes felhasználót létrehozni, mert a Mac adatbázis-dumpja a
meglévő felhasználókat és jelszóhasheket is átviszi.

## 7. Firewalld

A `think260x` releváns interfészei és zónái:

| Szerep | Interfész | Cím | firewalld-zóna |
| --- | --- | --- | --- |
| helyi LAN | `enp0s31f6` | `192.168.0.1/24` | `internal` |
| DMZ | `enp0s20f0u1c2` | `192.168.10.1/24` | `dmz` |
| Telekom/WAN | `enp0s20f0u3` | `192.168.1.102/24` | `public` |
| Yettel | `enp0s20f0u6` | `192.168.100.2/24` | `public` |

A dashboard portját csak az `internal` zónában kell megnyitni:

```sh
firewall-cmd --permanent --zone=internal --add-port=8082/tcp
firewall-cmd --reload
```

Ellenőrzés:

```sh
firewall-cmd --zone=internal --query-port=8082/tcp
firewall-cmd --zone=public --query-port=8082/tcp
```

A kívánt válasz sorrendben `yes`, majd `no`. Így a dashboard a helyi LAN-ról
elérhető, a Telekom és a Yettel irányából azonban nincs megnyitva.

## 8. A Mac pollerének leállítása

A poller leállításához nem szabad az eszközöket egyenként kivenni a
lekérdezési körből, mert ez a kikapcsolt konfiguráció kerülne át Linuxra is.
Ehelyett egy befejezett pollkör után csak a launchd pollerszolgáltatást kell
kivenni:

```sh
launchctl bootout \
  gui/$(id -u) \
  "$HOME/Library/LaunchAgents/hu.bajanp.automation-poller.plist"
```

Ellenőrzés:

```sh
launchctl print gui/$(id -u)/hu.bajanp.automation-poller
```

A `Could not find service` üzenet ebben az esetben a kívánt eredmény. A Mac
dashboardja működhet tovább, de az átállás alatt kézi lekérdezést sem szabad
indítani.

Szükség esetén a Mac pollere így tölthető vissza:

```sh
launchctl bootstrap \
  gui/$(id -u) \
  "$HOME/Library/LaunchAgents/hu.bajanp.automation-poller.plist"
```

## 9. Végleges adatbázismentés és átvitel

A 2026-08-27-én, a Mac pollerének leállítása után készített kézi mentés:

```text
/Users/bajanp/Projects/automation/exports/
home_automation_20260827T070417Z.sql.gz
```

A dump teljes adatbázismentés: tartalmazza az adatbázis létrehozását, a táblák
eldobását és újralétrehozását, valamint az adatokat.

Átmásolása a Macről:

```sh
scp \
  /Users/bajanp/Projects/automation/exports/home_automation_20260827T070417Z.sql.gz \
  root@think260x:/var/backups/automation/
```

Integritásellenőrzés Linuxon:

```sh
gzip -t /var/backups/automation/home_automation_20260827T070417Z.sql.gz
echo $?
```

A `gzip -t` nem ír ki semmit, az `echo $?` várt eredménye `0`.

## 10. A dump visszatöltése

A Linux-dashboard és poller ne fusson import közben. Rootként:

```sh
set -o pipefail
gzip -cd \
  /var/backups/automation/home_automation_20260827T070417Z.sql.gz \
  | mariadb
```

A dump a `home_automation` adatbázis tábláit lecseréli a Macről mentett
állapotra. A `mysql` rendszeradatbázist és az `automation@localhost`
MariaDB-felhasználót nem módosítja.

Az import után:

```sh
chown automation:automation \
  /var/backups/automation/home_automation_20260827T070417Z.sql.gz
chmod 600 \
  /var/backups/automation/home_automation_20260827T070417Z.sql.gz
```

Adatellenőrzés:

```sql
SELECT COUNT(*) AS users FROM app_users;
SELECT COUNT(*) AS devices FROM devices;
SELECT COUNT(*) AS readings FROM sensor_readings;
SELECT COUNT(*) AS migrations FROM schema_migrations;

SELECT version, applied_at
FROM schema_migrations
ORDER BY applied_at DESC
LIMIT 5;
```

A felhasználók száma legalább egy, az eszközök és mérések száma pedig nem nulla.

## 11. Átállás utáni sorrend

1. Az importált adatbázissal kézzel el kell indítani a Linux-dashboardot.
2. A meglévő Mac-felhasználóval be kell jelentkezni.
3. Ellenőrizni kell a nyilvántartást, a grafikonokat, az eseményeket és a
   globális beállításokat.
4. Ellenőrizni kell a hostnevek feloldását (`getent hosts ESZKOZNEV.home`) és
   az eszközök hálózati elérhetőségét. Az AdGuard DNS-ben minden lekérdezett
   eszközhöz `nev.home` alakú helyi rekord tartozik. A 2026-08-27-i átállási
   próbán a DNS-rekordok kiegészítése után mind a 17 eszköz elérhető volt.
5. Létre kell hozni és engedélyezni kell a systemd dashboard-szolgáltatást.
6. Csak ezután indítható egyetlen kézi Linux-pollkör.
7. Ha az eredmény hibátlan, létrehozható és engedélyezhető a Linux periodikus
   pollerszolgáltatása.
8. A Mac pollere kikapcsolva marad.

A Mac ettől függetlenül továbbra is használható az ESP32-k USB-s
firmware-feltöltésére, soros diagnosztikájára és konfigurálására. Ezek a
műveletek nem indítják el a Mac periodikus pollerét. Az új ESP32-k részletes
üzembe helyezési folyamata az `esp32.md` „Firmware-kezelés a Linuxra költözés
után” szakaszában található.

## 12. Systemd pollerszolgáltatás

A periodikus lekérdezést az alábbi
`/etc/systemd/system/automation-poller.service` egység futtatja:

```ini
[Unit]
Description=Automation periodic device poller
After=network-online.target mariadb.service
Wants=network-online.target
Requires=mariadb.service

[Service]
Type=simple
User=automation
Group=automation
WorkingDirectory=/var/www/automation
ExecStart=/var/www/automation/.venv/bin/python /var/www/automation/app/poll_scheduler.py
Restart=on-failure
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Az egységben szándékosan nincs `EnvironmentFile` sor. Fedora alatt a systemd
az `/var/www/automation/.env` közvetlen beolvasását jogosultsági hibával
elutasította; az alkalmazás viszont a fájlt saját maga, az `automation`
felhasználóként szabályosan betölti.

Aktiválás és ellenőrzés:

```sh
systemctl daemon-reload
systemctl enable --now automation-poller.service
systemctl status automation-poller.service --no-pager -l
journalctl -u automation-poller.service -n 30 --no-pager
```

A 2026-08-27-i átállás végén a dashboard és a poller is a think260x gépen
futott, a Mac periodikus pollere pedig kikapcsolva maradt.

### Shelly MQTT collector

A Shelly H&T Gen3 nem része a periodikus pollkörnek. A helyi Mosquitto broker
üzeneteit külön systemd szolgáltatás dolgozza fel:

```bash
chown automation:automation /var/www/automation/app/shelly_mqtt_service.py
chmod 0755 /var/www/automation/app/shelly_mqtt_service.py
install -o root -g root -m 0644 \
  /var/www/automation/deploy/systemd/automation-shelly-mqtt.service \
  /etc/systemd/system/automation-shelly-mqtt.service
restorecon -R /var/www/automation/app
restorecon /etc/systemd/system/automation-shelly-mqtt.service
systemctl daemon-reload
systemctl enable --now automation-shelly-mqtt.service
```

Ellenőrzés:

```bash
systemctl status automation-shelly-mqtt.service --no-pager -l
journalctl -u automation-shelly-mqtt.service -n 50 --no-pager
```

Az unit a MariaDB és Mosquitto után indul, és mindkettővel `PartOf`
kapcsolatban áll. A Fedora teljes mentőscriptjének is meg kell őriznie és vissza
kell állítania az `automation-shelly-mqtt.service` futási állapotát.

A részletes topic-, deep-sleep-, duplikáció- és SQL-ellenőrzési leírás a
[`docs/shelly-mqtt.md`](shelly-mqtt.md) dokumentumban található.

### A Fedora szerver saját metrikái

A `thinkpad260x` nyilvántartási eszközt a `linux_system` illesztő kérdezi le
10 percenként. A lekérdezés helyben, shellparancs indítása nélkül olvassa:

- a CPU csomaghőmérsékletét a Linux `hwmon`, szükség esetén `thermal` sysfs
  felületéről;
- az 1, 5 és 15 perces rendszerterhelést (`load average`).

A nyers értékek külön szenzor-idősorokként kerülnek az adatbázisba. A
főoldali eszközbélyeg a CPU-hőmérséklet mellett mindhárom load értéket
megjeleníti; a CPU-hőmérséklet a mérési előzményekben is kiválasztható.

A konfiguráció `local_hostname` mezője `think260x`. Helyi lekérdezéskor az
illesztő csak akkor engedélyezi a mérést, ha a futó gép rövid hostneve ezzel
egyezik. Ez megakadályozza, hogy egy Macen véletlenül elindított poller a Mac
saját terhelését a Fedora szerverhez rögzítse.

### Távoli Linux-gép monitorozása korlátozott SSH-val

A `think220x` tapasztalatai alapján a távoli Linux-gépekhez nem telepítünk
külön ügynököt, és az alkalmazás nem kap általános vagy root SSH-hozzáférést.
A távoli gépen egy kizárólag mérési JSON kiírására használható felhasználó és
egy SSH forced command működik:

```text
automation poller (think260x)
  -> SSH kulcs, BatchMode, PTY nélkül
  -> automation-monitor@think220x
  -> kötelező /usr/local/libexec/automation-system-metrics parancs
  -> egyetlen JSON-válasz
```

A távoli script a CPU-hőmérsékletet, az 1/5/15 perces load értékeket, a
hostnevet, a kernelverziót és a CPU-k számát adja vissza. Az alkalmazás
ellenőrzi a séma verzióját és azt is, hogy a válaszban kapott rövid hostname
megegyezik-e a konfigurált `local_hostname` értékkel. A nyers SSH-parancssor
nem használ shellt, nem fogad jelszót, és nem kapcsolja ki a hostkulcs
ellenőrzését.

#### A távoli gép előkészítése

A `think220x` gépen létrejött az `automation-monitor` felhasználó, valamint a
csak JSON-t kiíró, root jogosultságot nem igénylő
`/usr/local/libexec/automation-system-metrics` program. A publikus kulcs
`authorized_keys` sora a következő korlátozással szerepel:

```text
restrict,command="/usr/local/libexec/automation-system-metrics" ssh-ed25519 … automation-system-metrics
```

A `restrict` tiltja többek között a shellt, PTY-t és porttovábbítást. Ha az
`sshd_config` vagy valamelyik `/etc/ssh/sshd_config.d/` fájl `AllowUsers`
beállítást tartalmaz, abba az `automation-monitor` felhasználót is fel kell
venni. Enélkül a naplóban ez jelenik meg:

```text
User automation-monitor ... not allowed because not listed in AllowUsers
```

Módosítás után:

```sh
sshd -t
systemctl reload sshd
sshd -T | grep -i '^allowusers'
```

A think220x `internal` firewalld zónája csak a routerként működő think260x
DMZ-címéről (`192.168.10.1`) engedi az SSH-t. A jogosultságok és az SELinux
címkék ellenőrzése:

```sh
chown -R automation-monitor:automation-monitor /var/lib/automation-monitor/.ssh
chmod 700 /var/lib/automation-monitor /var/lib/automation-monitor/.ssh
chmod 600 /var/lib/automation-monitor/.ssh/authorized_keys
restorecon -RFv /var/lib/automation-monitor
```

#### A gyűjtőgép és a poller konfigurációja

A privát kulcs helye a think260x gépen:

```text
/var/lib/automation/.ssh/id_ed25519_system_metrics
```

A kulcs és a `known_hosts` fájl az `automation` rendszerfelhasználó számára
olvasható. Az első, kézi próba (a `-T` elkerüli a felesleges PTY-figyelmeztetést):

```sh
sudo -u automation ssh -T \
  -i /var/lib/automation/.ssh/id_ed25519_system_metrics \
  -o BatchMode=yes \
  automation-monitor@192.168.10.2
```

A helyes válasz egyetlen JSON-objektum, például:

```json
{"schema_version":1,"hostname":"think220x","cpu_temperature_c":60.0,"load_1m":0.123,"load_5m":0.054,"load_15m":0.008}
```

Fontos, hogy a kézi próba is ugyanazt a `known_hosts` fájlt használja, mint
az alkalmazás. Ha az első kapcsolat csak az SSH alapértelmezett fájljába
mentette a kulcsot, a poller szigorú ellenőrzése helyesen megtagadja a
kapcsolatot. Az alkalmazás saját fájljának egyszeri, ellenőrzött feltöltése:

```sh
sudo -u automation ssh -T \
  -i /var/lib/automation/.ssh/id_ed25519_system_metrics \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=/var/lib/automation/.ssh/known_hosts \
  automation-monitor@192.168.10.2
```

Ezután az alkalmazás már `StrictHostKeyChecking=yes` beállítással dolgozik.
A sikeres 2026-08-27-i üzemi próbában a think220x 60 °C CPU-hőmérsékletet
jelzett, miközben a helyben mért think260x 47 °C-ot; a két gép adatai külön
idősorokba kerültek.

A `config/devices.json` távoli bejegyzésében fontos, hogy a nyilvántartási
név (`thinkpad220x`) és az operációs rendszer valódi hostneve (`think220x`)
nem azonos:

```json
{
  "source_system": "linux_system",
  "hostname": "thinkpad220x",
  "local_hostname": "think220x",
  "expected_ip": "192.168.10.2",
  "mac_address": "",
  "device_id": "thinkpad220x",
  "metrics_transport": "ssh",
  "ssh_user": "automation-monitor",
  "ssh_identity_file": "/var/lib/automation/.ssh/id_ed25519_system_metrics",
  "ssh_known_hosts_file": "/var/lib/automation/.ssh/known_hosts",
  "enabled": true
}
```

Az `expected_ip` az SSH célpontja, ezért a távoli mérés nem függ a DNS-től.
Az `auto` mód azonos hostname esetén helyben mér, eltérő hostname esetén
SSH-t használ; üzemszerű távoli eszköznél mégis az explicit `ssh` ajánlott.
Sikeres kézi próba és konfiguráció után a nyilvántartásban visszakapcsolható
a `thinkpad220x` lekérdezése, majd egy kézi körrel ellenőrizhető. Ezután a
10 perces automatikus lekérdezés is engedélyezhető.

## 13. Még hátralevő feladatok

- a napi backup futásának és megőrzési szabályának ellenőrzése;
- újraindítási próba;
- szükség esetén Apache reverse proxy kialakítása.

Az átállás mindaddig visszafordítható, amíg a Mac launchd pollerének plistje és
a végleges Mac-adatbázismentés megmarad.
