# Eszközpolling és MariaDB-tárolás

## Áttekintés

Az alkalmazás egy közös pollingkörben kezeli az ESP32, Computherm, ConnectLife,
Nous/Tasmota, Linux és általános hálózati eszközöket. Az eszközök elsődleges
hálózati címe a hostname; az `expected_ip` csak diagnosztikai adat.

A géppel olvasható leltár:

```text
config/devices.json
```

## Egyszeri pollingkör

Csak lekérdezés, adatbázis-mentés nélkül:

```sh
cd ~/Projects/automation
.venv/bin/python app/poll_devices.py --summary
```

Lekérdezés és MariaDB-mentés:

```sh
.venv/bin/python app/poll_devices.py --store --summary
```

## Periodikus polling

A hosszú ideig futó pollingfolyamat induláskor azonnal lekérdez minden eszközt,
majd alapértelmezés szerint 10 percenként új kört indít:

```sh
cd ~/Projects/automation
.venv/bin/python app/poll_scheduler.py
```

Az időköz másodpercben a `.env` fájl `POLL_INTERVAL_SECONDS` értékével vagy az
`--interval` kapcsolóval módosítható. A folyamat `Ctrl-C`-vel állítható le. Egy
eszköz hibája nem szakítja meg a többi lekérdezését vagy a későbbi köröket.

Ugyanez a folyamat készíti a napi automatikus adatbázismentést. A `.env`
beállításai:

- `DATABASE_BACKUP_DIR`: a mentések könyvtára;
- `DATABASE_BACKUP_TIME`: a napi mentés helyi idő szerint, `HH:MM` alakban;
- `DATABASE_BACKUP_KEEP`: ennyi automatikus mentést őriz meg.

Ha a gép a beállított időpontban alszik vagy ki van kapcsolva, a poller az
ébredés/indulás utáni első ciklus végén pótolja az aznapi mentést. A mentés a
lekérdezésekkel közös zárolást használ. A megőrzési korlát csak az automatikus,
`home_automation_auto_...` nevű mentésekre vonatkozik, a kézi exportokra nem.

A műszerfal a Klímaáttekintő cím alatt a legutóbbi adatbázisba mentett
pollingkör dátumát és idejét mutatja. Az oldal frissítése továbbra sem indít
pollingot.

Az áttekintő fejlécében található **Kézi lekérdezés** gomb egyetlen teljes
pollingkört indít és az eredményeket elmenti a MariaDB-be. A művelet végén a
felület megmutatja a sikeresen lekérdezett és elmentett eszközök számát.
Egyszerre csak egy pollingkör futhat, függetlenül attól, hogy azt a kézi gomb
vagy a periodikus poller indította. Ha már fut egy kör, a kézi kérés erről
visszajelzést ad, az esedékes automatikus kör pedig kimarad. A következő
automatikus futás az eredeti 10 perces ütemezés szerint történik.

## Automatikus indítás macOS-en

A két felhasználói `launchd` szolgáltatás:

- `hu.bajanp.automation-dashboard`: webes műszerfal;
- `hu.bajanp.automation-poller`: 10 perces adatgyűjtés.

A verziózott plist minták a `deploy/macos` könyvtárban vannak, a telepített
példányok pedig a `~/Library/LaunchAgents` könyvtárban. Bejelentkezéskor
automatikusan elindulnak, és váratlan leállás után a `launchd` újraindítja őket.
A naplók a projekt `logs` könyvtárába kerülnek.

A műszerfal induláskor ellenőrzi a gnuplot elérhetőségét és támogatott
verzióját. macOS-en a javasolt `.env` érték:

```text
GNUPLOT_BIN=/opt/homebrew/bin/gnuplot
```

Ha a függőség hiányzik, az áttekintő tovább működik, de a történeti grafikon
helyén diagnosztikai üzenet jelenik meg. A `/health` végpont a gnuplot állapotát
és feloldott elérési útját is visszaadja.

MacBook-alvás közben a gép nem szolgálja ki a weboldalt és nem pollol. Ébredés
után a folyamatok tovább futnak, a polling pedig folytatódik. Kikapcsolás vagy
újraindítás után a szolgáltatások a következő felhasználói bejelentkezéskor
indulnak el.

## Későbbi Fedora-üzem

Az alkalmazáskód platformfüggetlen. A Fedora számára előkészített systemd user
unitok a `deploy/systemd` könyvtárban vannak. Ezek ugyanazt a `dashboard.py` és
`poll_scheduler.py` programot indítják, automatikus hibautáni újraindítással.

Az üzemszerű Fedora-telepítéskor még el kell végezni:

- a projekt és a Python-környezet telepítését a Fedora gépre;
- a `.env` biztonságos létrehozását;
- a MariaDB helyének és indulási sorrendjének véglegesítését;
- a systemd unitok telepítését és engedélyezését;
- szükség esetén a 8081/TCP port helyi tűzfalszabályának beállítását.

## Kért eszközbeállítások

A `/settings` felület a Hisense és Computherm eszközökhöz kézi kívánt
beállításokat rögzít a `device_setting_requests` táblába. Ezek a kérések nem
kerülnek elküldésre a fizikai eszközöknek. Minden új kérés időbélyeges sor; a
korábbi várakozó kérés `superseded` állapotot kap, ezért az előzmény megmarad.

## Időprofilok és napi terv

A `/schedules` felületen eszközönként három munkanapi és egy ünnepnapi profil
konfigurálható, profilként legfeljebb hat nem átfedő időablakkal. A heti
napokhoz profil rendelhető, konkrét dátum pedig előre felülírhatja a heti rendet.
Az ablakok közötti hézag explicit kikapcsolt időszakká válik. A rendszer minden
változáskor verziózott `resolved_daily_plans` sort készít a mai napról. Ez még
nem vezérel eszközt; a későbbi döntési logika egyértelmű bemenete.

A teljes, normalizált JSON megtekintéséhez hagyjuk el a `--summary` kapcsolót.

## Adapterek

- ESP32: `http://<hostname>/api/v1/measurements`
- Computherm: helyi BroadLink/Hysen UDP API, hostname és MAC alapján
- ConnectLife: egyetlen felhős bejelentkezés és eszközlista-lekérés; az öt
  eredmény AUID és ConnectLife-név alapján kerül a saját hostname-ekhez
- Zigbee2MQTT: a külön `automation-zigbee2mqtt.service` folyamatosan figyeli
  a helyi Mosquitto broker `zigbee2mqtt/#` témáit. A `bridge/devices`
  leírásból IEEE-cím alapján automatikusan létrehozza az eszközöket és az
  olvasható mérési csatornákat. Az új eszköz csak olvasható, vezérlése
  kikapcsolt, helyisége pedig nincs, amíg a Nyilvántartásban hozzá nem rendelik.
- Shelly H&T Gen3: a külön `automation-shelly-mqtt.service` a helyi Mosquitto
  broker `+/status/temperature:0`, `+/status/humidity:0`,
  `+/status/devicepower:0` és `+/online` témáit figyeli. Csak a
  `shellyhtg3-` kezdetű első topicszintet fogadja el. A hőmérsékletet,
  páratartalmat, elemszázalékot és elemfeszültséget egymástól független,
  időbélyeges `sensor_readings` sorokként tárolja.
- Hálózati eszköz: a `network_device` illesztő minden esedékes körben feloldja
  a hostnevet, egy ICMP-pinget küld és lekéri a `http://<hostname>/` címet.
  Az eszköz akkor számít elérhetőnek, ha a webfelület 2xx vagy 3xx választ ad;
  a ping eredménye ettől független diagnosztikai adat. Minden próba időpontja,
  futási ideje és esetleges hibája a `poll_attempts` táblába kerül, a sikeres
  állapot részletei pedig a `device_states.raw_state` mezőbe.

Az első ilyen eszköz a Xerox B235 nyomtató: `xeroxb235.home`
(`192.168.0.2`). Az alapértelmezett lekérdezési időköz 10 perc.

A Shelly H&T Gen3 deep-sleep működése miatt az `/online=false` nem hiba. A
dashboard a legutóbbi tényleges mérésből számít négylépcsős frissességet:
0–1 óra zöld, 1–2 óra sárga, 2–4 óra narancs, 4 óra felett piros.
Retained üzenetnél stabil topic+payload hash védi az idősorokat az
újraindításkori duplikációtól; azonos payloadú későbbi élő üzenet mindig új
mérési pont. Részletes üzemeltetés: [`docs/shelly-mqtt.md`](shelly-mqtt.md).

A Zigbee2MQTT adapter nem küld rendszeres `/get` parancsokat az elemes
eszközöknek. Az MQTT-üzenetek legutó ismert tulajdonságait a
`zigbee2mqtt_property_cache` táblában tartja, a Zigbee2MQTT `last_seen`
időpontját pedig a fogadás idejétől külön tárolja. A temperature, humidity és
battery jelentések emellett külön, időbélyeges `sensor_readings` sorokként is
megmaradnak. Az eseményazonosító a fizikai IEEE-címből, tulajdonságból és
forrásoldali `last_seen` időből készül, ezért retained vagy ismételt üzenet nem
duplázza ugyanazt a mintát.

A nyitásérzékelők `contact` értéke nem periodikus pillanatképként, hanem csak
az első ismert állapotnál és valódi állapotváltáskor kerül a `sensor_readings`
táblába. Értéke `0 = nyitva`, `1 = csukva`; az `observed_at` a Zigbee2MQTT
`last_seen` időpontja, ennek hiányában az MQTT-üzenet fogadási ideje.

A nyitásérzékelőknél a régi `last_seen` önmagában nem jelent kiesést, mert az
elemes eszköz változatlan állapotban órákig vagy akár egy napnál tovább sem
feltétlenül küld üzenetet. Két óránál régebbi állapotjelzés ezért sárga,
**Régi állapotjelzés** bélyeget kap, miközben az utolsó ismert nyitva/csukva
érték megmarad. Piros, **Zigbee eszköz nem elérhető** állapotot csak a
Zigbee2MQTT explicit `availability=offline` jelzése okoz. Ez a kivétel csak a
nyitásérzékelőkre vonatkozik; a periodikusan jelentő Zigbee hőmérők meglévő
frissességi ellenőrzése változatlan.

A Zigbee2MQTT availability-figyelése engedélyezett. Az aktív, hálózati
táplálású eszközök határa 10 perc, a passzív, elemes eszközöké 2880 perc
(48 óra). A passzív eszközt a Zigbee2MQTT nem tudja felébreszteni vagy
megbízhatóan pingelni, ezért az `offline` állapotot az elmaradt jelentésekből,
késleltetve állapítja meg. A Nous/Tuya nyitásérzékelőknél a
`batteryPercentageRemaining` és `batteryVoltage` attribútumok jelenlegi
reporting beállítása `min=3600`, `max=65000` másodperc és `change=0`; ezek az
akkumulátor-jelentések akkor is életjelet adhatnak, ha a `contact` állapot nem
változik. A 48 órás határ több mint két maximális akkumulátor-jelentési ciklust
hagy. Ez nem jelenti azt, hogy a nyitva/csukva állapot periodikusan ismétlődik,
és nem helyettesíti a tényleges események, illetve a Zigbee2MQTT availability
figyelését.

Az idősoros mentés bevezetésekor a collector a cache aktuális értékeiből
eszközönként és tulajdonságonként egy kezdőpontot készít. A cache nem tartalmaz
előzményeket, ezért a bevezetés előtti teljes Zigbee-idősor nem rekonstruálható.

Az SNZB-02WD kültéri hőmérő jelentései ezen felül időbélyeges
`outdoor_temperature_observations` sorokat hoznak létre. A hozzá tartozó
Zigbee2MQTT-forrás automatikusan aktív, 1. prioritású és 120 percig friss;
az alacsonyabb prioritású Open-Meteo forrás ennek kiesésekor tartalék marad.

A ConnectLife felhasználónév és jelszó kizárólag a nem verziózott `.env`
fájlban szerepelhet.

## Hibaisoláció

Minden eszköz külön `PollResult` eredményt kap. Egy timeout, DNS-hiba, hibás JSON,
BroadLink-protokollhiba vagy ConnectLife-hiba nem állítja le a többi eszköz
lekérdezését.

Minden próbálkozás bekerül a `poll_attempts` táblába:

- eszköz és hostname;
- kezdési és befejezési idő UTC-ben;
- időtartam milliszekundumban;
- sikeresség;
- hibatípus és hibaüzenet.

A sikeres hőmérsékletek a `sensor_readings`, az eszközállapotok a
`device_states` táblába kerülnek. Hibás ESP32-szenzor esetén `value = NULL`,
`quality = invalid` és kitöltött `error_code` kerül mentésre.

## Adatbázis létrehozása és migrációja

```sh
.venv/bin/python app/migrate_database.py
```

A migrációk nyilvántartása a `schema_migrations` táblában történik, ezért a
parancs ismételten is futtatható.

## Külső hőmérséklet-források

A `/outdoor-sources` felületen kézzel állítható, hogy mely források aktívak,
milyen prioritási sorrendben követik egymást, és legfeljebb hány perces adat
fogadható el tőlük. A rendszer az aktív, friss adatok közül a legkisebb
prioritásszámút választja.

Az alapértelmezett sorrend:

1. saját kültéri ESP32 (`esp32_ext`, kezdetben inaktív),
2. Weather Underground PWS (helyi állomásazonosítóval konfigurálva),
3. Open-Meteo (a telepítés közelítő koordinátájával konfigurálva),
4. kézi külső hőmérséklet (kezdetben inaktív).

Az Open-Meteo lekérdezése a periodikus és a kézi pollkör közös zárolásán belül
fut. A mérés időpontja és a lekérés időpontja külön mezőben tárolódik. A
Weather Underground integráció csak API-kulcs és PWS-jogosultság birtokában
aktiválandó.

## Szellőztetési napló

A `/ventilation` oldalon az indítás helyiségenként aktív eseményt hoz létre,
amely csak a befejezés külön rögzítésével válik lezárttá. Egy helyiségben
egyszerre legfeljebb egy aktív szellőztetés lehet. Az indításkor a rendszer az
aktív, friss külső források prioritása alapján automatikusan rögzíti a forrást
és a külső hőmérsékletet; ezeket nem kell kézzel kiválasztani. Az időpontok az
adatbázisban UTC-ben tárolódnak, az UI helyi időben jeleníti meg őket.

A helyiséghez rendelt aktív Zigbee/Nous nyitásérzékelő nyitása automatikusan
elindítja ugyanezt a szellőztetési eseményt. Ha több érzékelő tartozik egy
helyiséghez, az első nyitás indít, és csak az utolsó nyílászáró zárása zárhatja
le. A csukott jelzést a collector alapból 30 másodpercig visszaellenőrzi. Ha
közben ismét nyitott állapot érkezik, az esemény folytatódik: így a nyitott és
bukó állás közötti rövid, kényszerű becsukás nem darabolja fel a naplót.
Ha a helyiségben már fut kézzel indított esemény, az megőrzi kézi eredetét és
kezdőadatait, de a rendszer hozzárendeli az érzékelőt, így a tényleges zárás
attól kezdve automatikusan lezárhatja.

A `VENTILATION_LONG_THRESHOLD_MINUTES` (alapból 5 perc) választja szét a rövid
és hosszú szellőztetést. A határ eseményenként is eltárolódik. A
`VENTILATION_CONTACT_CLOSE_DELAY_SECONDS` (alapból 30 másodperc) a zárási
késleltetés. Mindkettő szerkeszthető a Globális beállítások oldalon; a Zigbee
collector legfeljebb öt másodpercen belül újraolvassa őket a `.env` fájlból.
A `/ventilation` lista alapból az aktív eseményekre szűr; a felületen az összes
esemény és külön helyiség is kiválasztható.

## Kézi klímahasználati napló

A `/climate-log` oldalon az öt ConnectLife/Hisense klímához kézzel rögzíthető
az indítás, majd egy külön művelettel a leállítás. Az indítás aktív eseményt
hoz létre, és egy klímához egyszerre csak egy aktív esemény tartozhat. A napló
nem küld parancsot az eszköznek; a tényleges vezérlés későbbi fejlesztés.
A klíma kiválasztásakor a felület bekapcsolás nélkül megjeleníti a legutóbbi
ConnectLife-lekérdezés célhőmérsékletét. Az indítás eseménye ezt az értéket
pillanatfelvételként eltárolja, így utólag is látható, milyen célértékkel indult.
A klíma leállításakor a rendszer ismét kiolvassa és külön eltárolja a legutóbbi
célhőmérsékletet. A szellőztetés lezárásakor ugyanígy új pillanatfelvétel készül
az akkor aktív külső szolgáltató hőmérsékletéről és magáról a forrásról. Így a
kezdési és befejezési állapotok expliciten, egymástól függetlenül megmaradnak.

### Közvetlen klímavezérlés

A Klíma oldalon az öt Hisense eszköz ténylegesen ki- és bekapcsolható. A
bekapcsoláskor a célhőmérséklet, a ventilátorfokozat és a bekapcsolási állapot
kerül elküldésre; más üzemmódot vagy kiegészítő programot a rendszer nem módosít.
Minden parancs előtt friss ConnectLife-lekérdezés ellenőrzi az előfeltételt:
bekapcsolás csak kikapcsolt, kikapcsolás csak bekapcsolt klímán engedélyezett.
A parancs után ismételt visszaolvasás a ventilátorfokozatot is igazolja. Minden kérés,
elutasítás, hiba és igazolt siker a `climate_control_attempts` táblába kerül.

## Jelenlegi állapot

Az első teljes, tárolással végzett hardverteszt eredménye:

- 8 eszköz;
- 8 szenzor;
- 8 sikeres mérés;
- 7 eszközállapot (5 ConnectLife és 2 Computherm);
- 8 sikeres pollingkísérlet.

Az ESP32 jelenleg csak mérést szolgáltat, ezért hozzá nem készül külön
`device_states` sor.

## Mobilbarát webes áttekintő

Az első, csak olvasásra szolgáló felület az adatbázis utolsó ismert adatait
mutatja. Az oldal megnyitása nem indít új pollingkört.

```sh
cd ~/Projects/automation
.venv/bin/python app/dashboard.py
```

Macen a `http://localhost:8081`, azonos helyi hálózaton levő telefonon pedig a
Mac helyi IP-címével összeállított `http://<mac-ip>:8081` cím nyitható meg. A
kiszolgáló minden hálózati interfészen figyel, ezért a macOS tűzfal első
indításkor engedélyt kérhet a bejövő kapcsolatokhoz.

Az áttekintő tartalma:

- eszközönként az utolsó hőmérséklet és elérhetőség;
- választható eszköz-, illetve zóna–helyiség szerinti csoportosítás, az üres
  helyiségek megjelenítésével;
- a Computherm és Hisense eszközök célhőmérséklete és állapota;
- hostname és az utolsó lekérdezés időpontja;
- az utolsó 40 pollingkísérlet diagnosztikai listája.

A Bosch 7000i a földszinti zóna **Kazánház** helyiségéhez tartozik.

Az **Elemzések** oldal elő van készítve a determinisztikus napi statisztikák,
anomáliák és egy esetleges későbbi, validált szöveges összefoglaló számára. Az
elsőként kipróbált Llama 3.2 1B modell alkalmatlannak bizonyult és törölve lett.
Az Ollama kikapcsolt, az UI-ból nem engedélyezhető, és nem kap vezérlési
jogosultságot. A részletes tapasztalat a
`docs/local-analytics.md` dokumentumban található.

A **Mérési előzmények** oldal karbantartási részében jelölőnégyzetekkel
kiválaszthatók és nullázhatók az egyes hőmérséklet-szenzorok korábbi mérési
értékei. A művelet csak a `sensor_readings` sorokat törli; az eszközök,
szenzorok, állapotok és pollingnapló megmaradnak. A törlés közös pollingzárat
használ, ezért nem futhat egy időben adatgyűjtéssel.

## Felhasználók és jogosultságok

A dashboard minden adatoldala bejelentkezést igényel. Két szerepkör van:

- `viewer` (csak olvasó): minden áttekintő és előzmény megtekinthető, de az
  adatbázist vagy eszközállapotot módosító műveletek szerveroldalon tiltottak;
- `editor` (szerkesztő): kézi pollt indíthat, méréseket nullázhat, helyiséget,
  kért beállítást, időprofilt, kazánállapotot és szervizadatot módosíthat,
  továbbá felhasználókat kezelhet.

Üres `app_users` tábla esetén az első szerkesztő kizárólag a Mac saját
`http://localhost:8081/setup` címén hozható létre. A beállítás után ez az
útvonal automatikusan lezár. További felhasználók a **Felhasználók** oldalon
hozhatók létre, kapcsolhatók ki, illetve ott módosítható a szerepkörük és
jelszavuk. Az utolsó aktív szerkesztő és a saját szerkesztői hozzáférés nem
kapcsolható ki.

A jelszavak csak Werkzeug által készített erős hash formájában kerülnek az
adatbázisba. A munkamenetsüti `HttpOnly` és `SameSite=Lax`. Ha nincs beállítva
`DASHBOARD_SECRET_KEY`, az alkalmazás első induláskor létrehoz egy jogosultság
szerint védett, nem verziózott `.dashboard-secret` fájlt. Fedora-telepítésnél
javasolt külön tartós `DASHBOARD_SECRET_KEY` értéket megadni a környezetben.

A Bosch 7000i kézzel kezelt eszköz: a műszerfalon állítható, hogy a kazán
bekapcsolt vagy kikapcsolt állapotban van-e. A Hisense klímákhoz és a kazánhoz
megadható az utolsó szerviz dátuma. Az adatok és a korábbi szervizek története a
MariaDB-ben maradnak meg. A következő szerviz időpontja a szerelővel való
egyeztetéstől függ, ezért azt a rendszer nem számítja és nem tartja nyilván.

A kazán kézi állapotváltozásai és a szervizesemények külön naplózódnak:

- a `manual_state_events` minden tényleges be-/kikapcsolást a régi és az új
  állapottal, valamint az adatbázis időbélyegével tárol;
- a `service_events` a szerviz dátumát és a rögzítés időpontját tárolja.

Azonos kazánállapot ismételt mentése nem hoz létre hamis állapotváltozást. A
szerviz külön űrlapon menthető, ezért a szerelői próba és az azt követő kézi
kikapcsolás egymástól független esemény marad.

## Programozott klímafutás

A Klíma oldalon egy–nyolc egymás után végrehajtott lépés adható meg. A program
közös kezdési idővel és helyiséggel rendelkezik; minden lépéshez külön
futásidő, célhőmérséklet, ventilátorfokozat és továbblépési feltétel tartozik.
A normál fokozatok mellett a ConnectLife külön `t_fan_mute` tulajdonságával
vezérelt **Csendes** mód is választható.

A továbblépés történhet a futásidő végén, vagy a helyiség kiválasztott aktív
hőmérőjének friss értéke alapján. Négy feltétel választható: a mérés elérte a
célértéket, illetve a célérték és a mért érték különbsége elérte a 0,5 °C-ot,
elérte az 1,0 °C-ot, vagy szigorúan nagyobb 1,5 °C-nál. Csak a lépés indulása
után mért, legfeljebb 15 perces, jó
vagy érvényes mérés fogadható el. Szenzoros
feltételnél a futásidő biztonsági maximum: ha nincs megfelelő mérés vagy nem
teljesül a küszöb, annak lejártakor akkor is továbblép, illetve az utolsó
lépésnél leáll.

A program adatbázisban marad, a poller pedig legfeljebb körülbelül
10 másodperces ellenőrzési időközzel indítja, módosítja és állítja le az
eszközt. Minden parancs ConnectLife-visszaolvasással ellenőrzött, bekerül a
vezérlési auditba és a klímaesemény-naplóba is.

Ha a gép alszik az induláskor, de ébredéskor a lépések összes maximális
futásidejéből képzett teljes ablak még tart, a program késve elindul. Ha a
teljes ablak alvás közben lejárt, a rendszer nem kapcsolja be utólag a klímát,
hanem hibásként jelöli a programot.
