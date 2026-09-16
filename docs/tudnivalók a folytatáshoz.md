# Tudnivalók a folytatáshoz

Frissítve: **2026-09-14** (Europe/Budapest)

Ez a fájl az `automation` projekt folytatásának belépési pontja. Nem helyettesíti
és nem másolja a részletes dokumentációt: rögzíti, hogy mi az igazság forrása,
mi működik jelenleg, melyik témát hol kell tovább olvasni, és mely eldöntött
feladatok várnak még megvalósításra.

## 1. Az igazság forrásai

Az üzemi állapot és a verziózott forrás két külön helyen él:

1. **Éles alkalmazás és adatbázis:** `think260x`, alkalmazáskönyvtár
   `/var/www/automation`, MariaDB `home_automation` adatbázis. A tényleges
   eszközállapot, mérés, helyiség-hozzárendelés és számlaadat elsődleges forrása
   az éles adatbázis és az alkalmazás UI-ja.
2. **Fejlesztési forrásigazság:** a Macen a
   `/Users/bajanp/Projects/automation` repository `main` ága. A kódot itt kell
   módosítani és tesztelni, majd innen kell célzottan telepíteni a Fedorára.
3. **Távoli Git:** `git@github.com:fenyorigo/automation.git`. A 2026-09-14-i
   ellenőrzéskor a Mac `main` ága 14 committal megelőzte az `origin/main` ágat;
   az utolsó alkalmazáskód-commit `4838354` volt, az origin csúcsa pedig
   `150ac0e`. A GitHub tehát addig **nem teljes biztonsági másolat**, amíg a
   helyi commitok nincsenek felküldve. Mindig újra ellenőrizendő:

   ```bash
   git status --short --branch
   git rev-list --left-right --count origin/main...main
   ```

Az éles `/var/www/automation` könyvtár régi Git-commitból és sok kézzel
telepített fájlból álló, módosított munkapéldány. A 2026-09-14-i alapcommitja
`3c68a1e`, miközben a v1.48-ig terjedő migrációk és az új alkalmazásfájlok
részben nem követett vagy módosított fájlként vannak jelen. **Ott nem szabad
commitolni, pullt, resetet vagy automatikus összeolvasztást futtatni.** A Fedora
üzemi célgép, nem fejlesztési forrás.

A gyökérben levő, nem követett `HANDOVER_IMAC.md` 2026. augusztus 28-i,
v1.1/v1.31 állapotot ír le, ezért elavult. Nem szabad Githez adni; ezt a
dokumentumot kell helyette használni.

Titkok és helyi azonosítók a nem verziózott `.env`, `.dashboard-secret` és
`config/devices.json` fájlokban vannak. Tartalmukat nem szabad naplóba,
dokumentációba vagy commitba másolni.

## 2. Elsőként olvasandó dokumentumok

| Kérdés | Elsődleges dokumentum vagy fájl |
|---|---|
| Mi a projekt és hogyan indul? | [`../README.md`](../README.md) |
| Mi valósult meg verziónként? | [`../CHANGELOG.md`](../CHANGELOG.md) |
| Hogyan használható az UI? | [`hasznalati-utasitas.md`](hasznalati-utasitas.md) |
| Hogyan jutnak be és hol tárolódnak a mérések? | [`polling.md`](polling.md) |
| Mi a hűtési/fűtési döntési modell? | [`dontesi-logika.md`](dontesi-logika.md) |
| Mely eszközök és helyiségek aktívak? | [`device-inventory.md`](device-inventory.md), illetve az éles **Nyilvántartás** |
| Mi van eldöntve, de még nincs kész? | [`teendok.md`](teendok.md) |
| Fedora telepítés és helyreállítás | [`porting-to-linux.md`](porting-to-linux.md) |
| Aktuális adatbázismodell | [`sql/home-automation-schema.md`](sql/home-automation-schema.md), [`../SQL/migrations/`](../SQL/migrations/) |
| Zigbee párosítás és újraindítás | [`zigbee-pairing.md`](zigbee-pairing.md) |
| Shelly H&T MQTT | [`shelly-mqtt.md`](shelly-mqtt.md) |
| Nous/Tasmota és Bosch táp | [`nous-tasmota.md`](nous-tasmota.md) |
| Computherm helyi API | [`computherm.md`](computherm.md) |
| Hisense/ConnectLife API | [`connectlife-vizsgalat-osszefoglalo-api-irassal.md`](connectlife-vizsgalat-osszefoglalo-api-irassal.md) |
| Gáz- és villanyszámlák | [`gázszámla-felvitele.md`](gázszámla-felvitele.md), [`villanyszámla-felvitele.md`](villanyszámla-felvitele.md) |

Az eszközspecifikus és számlafelviteli szabályokat nem ebben a fájlban kell
megismételni, hanem a táblázatban hivatkozott célzott dokumentumban kell
karbantartani.

## 3. Jelenlegi üzemi architektúra

Az éles rendszer a `think260x` Fedora gépen fut:

```text
SONOFF / Tuya Zigbee ─> SONOFF/Tasmota bridge ─> Zigbee2MQTT ─┐
Shelly H&T Gen3 ─────────────────────── Wi-Fi/MQTT ───────────┼─> Mosquitto
                                                             │       │
                                                             │       ├─> automation-zigbee2mqtt
                                                             │       └─> automation-shelly-mqtt
HTTP/UDP/ConnectLife/Tasmota eszközök ─> automation-poller ───┴─> MariaDB ─> dashboard
```

Fontos helyi végpontok:

- dashboard: `http://think260x:8082/`;
- Zigbee2MQTT UI: `http://think260x:8083/`;
- Tasmota Zigbee bridge UI: `http://think260x:1083/`;
- Mosquitto az alkalmazásnak: `127.0.0.1:1883`.

A 2026-09-14-i ellenőrzéskor mind a hat érintett szolgáltatás aktív és
engedélyezett volt:

- `automation-dashboard.service`;
- `automation-poller.service`;
- `automation-zigbee2mqtt.service`;
- `automation-shelly-mqtt.service`;
- `zigbee2mqtt.service`;
- `mosquitto.service`.

Az alkalmazásverzió **1.3.1**, az adatbázis utolsó migrációja
`v1_48_boiler_operating_states`. A migrációs lánc sorrendjének egyetlen
forrása az [`app/migrate_database.py`](../app/migrate_database.py); az SQL-ek a
[`SQL/migrations`](../SQL/migrations/) könyvtárban vannak.

## 4. Mi működik jelenleg

### Adatgyűjtés és nyilvántartás

- A periodikus poller kezeli az öt Hisense klímát, két Computhermet, három
  Nous/Tasmota dugaljat, két Linux gépet és a Xerox B235 hálózati nyomtatót.
- A Zigbee collector automatikusan felfedezi az eszközöket, cache-eli a
  tulajdonságokat, és a hőmérsékletet, páratartalmat, elemet, valamint a valódi
  kontaktusváltásokat időbélyeggel a meglévő mérési modellbe írja. A régi
  kontaktusállapot nem hiba; csak az explicit Zigbee2MQTT `offline` állapot
  jelent kiesést.
- A Shelly collector két deep-sleep H&T Gen3 eszközt kezel közvetlen MQTT-ről.
  A temperature, humidity, battery és `battery_voltage` külön idősor; az
  `/online=false` normális. A frissességi színek határa 1, 2 és 4 óra.
- Az ESP32-eszközök inaktívak és már nem vesznek részt a pollkörben; a
  jelenlegi hőmérsékleti gerinc Zigbee és Shelly.
- A 2026-09-14-i élő leltárban 20 aktív Zigbee-eszköz volt: 9
  nyitásérzékelő, 9 hőmérő és 2 router-dugalj. A pontos név- és
  helyiségkiosztást a [`device-inventory.md`](device-inventory.md) rögzíti.

### Szellőztetés, hűtés és fűtés

- A Nous/Tuya kontaktusváltozások a `sensor_readings` mellett automatikus
  szellőztetési eseményt is vezetnek. Több nyílászárónál az első nyitás indít,
  az utolsó zárás fejez be; a 30 másodperces zárási késleltetés kiszűri a
  nyitott–bukó váltás pillanatnyi csukását.
- Az emeleti hűtési és fűtési logika **megfigyelő módban** működik: megmutatja,
  mit tenne, de automatikus parancsot még nem küld. A mérvadó helyiségi adat a
  Zigbee hőmérő; a Hisense és a dolgozóban a Computherm csak kisebb súlyú
  korrekció.
- A földszinti zóna csak gázfűtéses; a vendégszobai Zigbee hőmérő és a
  földszinti Computherm információforrásként látszik. A rendszer ott sem
  vezérli még a kazánt.
- Kézi és programozott Hisense-vezérlés már működik preflighttal,
  visszaolvasással és audittal. A klíma- és gázkazánszerviz módok, valamint a
  visszaállítható Computherm szervizteszt elkészültek.

A pontos határértékeket, súlyokat és biztonsági feltételeket nem itt, hanem a
[`dontesi-logika.md`](dontesi-logika.md) és az
[`app/global_settings.py`](../app/global_settings.py) tartalmazza.

### Bosch 7000i és Nous kazándugalj

- A `nous-kazan.home` az egyetlen UI-ból kapcsolható dugalj. Kikapcsolása piros
  második megerősítést kér; az állapottal azonos kapcsológomb inaktív.
- Az igazolt Nous-lekapcsolás a Bosch táp-, melegvíz- és fűtésjelzését is
  kikapcsolja és naplózza. Visszakapcsolás jelenleg csak a tápot állítja
  aktívra; a másik két jelölés kézi.
- A friss, legalább 2 W-os fogyasztás igazolja a Bosch saját power kapcsolóját;
  a mért nyugalmi érték kb. 5 W. Bekapcsolt Nous és friss 0 W piros
  figyelmeztetés.
- A `nous-kazan` feszültsége 235,5 V referencia alapján kalibrált. A
  részletes mérési tények és óvintézkedések a
  [`nous-tasmota.md`](nous-tasmota.md) fájlban vannak.

### Energia

- A saját villany- és gázóraállások külön idősorok; a szolgáltató becsült
  fogyasztása nem keveredik velük.
- A gázszámla-modell kezeli a novemberi elszámolási ciklust, az augusztus
  1.–július 31. közötti kedvezményes évet, a korrekciós tényezőt,
  fűtőértéket, MJ-díjsávokat, fix és szolgáltatási tételeket, valamint az éves
  elszámolást.
- A villanyszámlák történeti importja elkészült. Az adatbázisban 20 villany-
  számla található 2024-12-17–2026-08-22 időszakra, a két ismert duplum nélkül.
  A használaton kívüli vezérelt mérőhöz nincs fogyasztási idősor, de a tényleges
  régi alapdíjtétele megmaradt.
- Az adatbázisban 21 gázszámla található 2024-11-09–2026-08-06 időszakra.

## 5. Biztonsági invariánsok

- Egyszerre csak egy üzemi periodikus poller futhat. A Macen nem szabad
  pollert indítani, amíg a Fedora `automation-poller.service` aktív.
- A megfigyelő hűtési/fűtési döntés nem válhat csendben automatikus
  vezérléssé. Az átállás külön, tesztelt fejlesztési lépés.
- Nyitott, ismeretlen vagy explicit offline nyílászáró blokkolja a helyiségi
  automatikát. A régi, de elérhető kontaktusadat önmagában nem offline.
- A Computhermet nem kapcsoljuk ki, napi programját a szervizteszt sem írja
  felül; a próba állapotmentés után ideiglenes kézi célt használ, majd
  visszaállít.
- A kazán tápellátása, saját power kapcsolója, melegvíz-szolgáltatása és
  fűtése külön állapot. Táp nélkül a másik három nem lehet aktív.
- A `Nous main IT`, `Nous auxiliary IT` és a Zigbee router-dugaljak nem
  kapcsolhatók az UI-ból.
- Adatbázis-migráció vagy tömeges adatmódosítás előtt mentés szükséges.
  Eszközparancs csak a felhasználó által kért körben, előellenőrzéssel,
  utóellenőrzéssel és audittal mehet.

## 6. Eldöntött, de még nem folyamatban levő irányok

A részletes, karbantartandó lista a [`teendok.md`](teendok.md). A következő
érdemi munkák várható sorrendje:

1. A Bosch szerviz/próba alatt teljesítményprofil készítése, valamint annak
   ellenőrzése, hogy áram alá helyezve valóban mindig elérhető-e a melegvíz.
2. A két SONOFF TRV-ZBT (`TRV-G2 nappali bal`, `TRV-G2 Kristófék`) párosítása,
   helyiség-hozzárendelése és mérésgyűjtése elkészült. Következő lépés a téli
   üzemi megfigyelés; radiátorközeli hőmérsékletük aktív gázfűtés alatt nem
   lehet helyiségi vezérlési alap.
3. Az emeleti fűtési observer téli megfigyelése. A kevert klíma–gáz üzem addig
   tiltott; a dolgozó radiátorán a bútorzat miatt nincs és nem lesz TRV.
4. A hűtési observerből fokozatos, biztonságos automata vezérlés kialakítása:
   először csak javaslat/audit, majd a célérték-korlát és nyílászáró-kapuzás
   bizonyított végrehajtása.
5. A számlaadatokból villany–gáz fűtési költség-összehasonlítás, a Hisense
   külső hőmérsékletfüggő COP-görbéjével. Az ideiglenes 5 °C-os határ később
   számított COP-határra cserélendő.
6. A Zigbee2MQTT ismert leállási `write after end` upstream hibájának követése,
   és egy későbbi teljes házas áramszünet-visszatérési próba minden
   nyitásérzékelővel.

## 7. Gyors folytatási ellenőrzőlista

1. Olvasd el ezt a fájlt, majd a [`teendok.md`](teendok.md) aktuális nyitott
   pontjait és a [`../CHANGELOG.md`](../CHANGELOG.md) **Kiadatlan** részét.
2. Ellenőrizd a Mac munkapéldányát; a felhasználó változásait és az elavult,
   nem követett `HANDOVER_IMAC.md` fájlt ne írd felül és ne add commithoz.
3. Ellenőrizd az éles szolgáltatásokat:

   ```bash
   ssh -i ~/.ssh/id_ed25519_fedora root@think260x \
     'systemctl is-active automation-dashboard automation-poller automation-zigbee2mqtt automation-shelly-mqtt zigbee2mqtt mosquitto'
   ```

4. Kódmódosítás előtt az érintett célzott tesztet, utána a teljes csomagot
   futtasd:

   ```bash
   .venv/bin/python -m unittest discover -s tests
   git diff --check
   ```

   A dokumentum készítése előtti utolsó teljes futás 121 tesztből 121 sikeres
   volt.
5. Sémaváltozásnál új, következő sorszámú migráció készüljön, és az kerüljön be
   az `app/migrate_database.py` listájába. A régi migrációt ne írd át.
6. A Fedorára csak a Macen tesztelt fájlokat telepítsd; állítsd vissza az
   `automation:automation` tulajdont és az SELinux-kontextust, szükség esetén
   futtasd a migrációt, majd indítsd újra csak az érintett szolgáltatást.
7. Telepítés után ellenőrizd a service státuszt, a journalt és az érintett
   adatbázis/UI viselkedést. A Fedora dirty Git-állapotát ne próbáld „kitisztítani”.

## 8. A dokumentáció karbantartási szabálya

- Új megvalósítás: `CHANGELOG.md` **Kiadatlan** rész.
- Új vagy módosított felhasználói folyamat: `hasznalati-utasitas.md`.
- Adatút vagy tárolási szabály: `polling.md` és szükség esetén az SQL-sémadoksi.
- Hűtési/fűtési szabály: `dontesi-logika.md`.
- Eszköz vagy helyiség változása: `device-inventory.md`.
- Eldöntött, de későbbi munka: `teendok.md`.
- Speciális eszköz- vagy számlafolyamat: a már meglévő célzott dokumentum.

Ezt a fájlt csak akkor kell bővíteni, ha az architektúra, az igazság forrása,
az átadási kockázat vagy a folytatás fő sorrendje változik.
