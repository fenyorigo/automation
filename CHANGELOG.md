# Változásnapló

A projekt a szemantikus verziózás elvét követi. A kiadás dátumai budapesti
helyi dátumok.

## 1.1.0 — 2026-08-22

Kalibrált ESP32/DS18B20 hőmérsékleti feldolgozás és programozott klímaüzem.

### Új funkciók

- Többlépéses programozott klímafutás, lépésenkénti célhőmérséklettel,
  ventilátorfokozattal, maximális futásidővel és szenzorfeltétellel.
- Időben verziózott ESP–DS fizikai konfigurációk és kalibrációs korrekciók.
- A nyers adatok változatlan megőrzése mellett EMA-szűrt, önálló cselekedeti
  hőmérsékleti idősor és teljes forráskövetés.
- A főoldalon zónafüggetlen váltás a nyers és cselekedeti ESP32-hőmérséklet
  között, az ofszet, időállandó és mérési időpont kijelzésével.
- A még nem kalibrált vagy nem kész szenzorok egyértelmű elkülönítése.

### Dokumentáció és adatbázis

- A kalibrációs jegyzőkönyv kiegészült a doboz–rézcső kontrollmérésekkel, az
  első üzemi korrekciókkal és a további érzékelők kalibrációs láncával.
- Új v1.26–v1.29 adatbázis-migrációk a programozott klímaüzemhez és a
  származtatott hőmérsékleti adatokhoz.
- Frissített használati, polling-, adatbázis- és döntési logika dokumentáció.

## 1.0.0 — 2026-08-18

Az első egységesen verziózott, napi használatra alkalmas kiadás.

### Fő funkciók

- ESP32/DS18B20, Computherm, Hisense/ConnectLife és Nous/Tasmota eszközök
  periodikus és kézi lekérdezése, közös futási zárral.
- MariaDB-alapú mérés-, állapot-, esemény-, energia- és auditnapló.
- Reszponzív, mobiltelefonról is használható Flask kezelőfelület viewer és
  editor jogosultsággal.
- Eszköztípus, illetve zóna és helyiség szerinti főoldali nézet.
- Eszköztípus-szűrés, valamint azzal kombinálható **Lekérdezési körben** szűrő.
- Egyedi lekérdezési gyakoriság és eszközönként kapcsolható polltagság; a
  nyilvántartás mentése szinkronizálja a futó eszközkonfigurációt.
- Többes hőmérsékleti grafikon, rövid időablakok, széles CSV-export és
  felhasználónként legfeljebb négy mérési kedvenc.
- Hisense klíma közvetlen és időzített vezérlése, célhőmérséklettel,
  ventilátorfokozattal, állapot-ellenőrzéssel és auditálással.
- Szellőztetési és klímaüzem-események kezdő- és záróértékeinek naplózása.
- Kézi hőmérők, karbantartási események, kazánállapot és energiaóra-állások
  rögzítése; hibás energiaóra-adat helyben javítható.
- Külső hőmérsékleti források prioritása és Open-Meteo-integráció.
- Nous/Tasmota pillanatnyi teljesítmény-, feszültség- és kumuláltenergia-kártyák.
- Determinisztikus, kereshető Python-jelentések; a jelentéskészítő nem adhat
  vezérlési utasítást.
- Automatikus adatbázismentés, migrációk, valamint macOS launchd- és Fedora
  szolgáltatásminták.

### Dokumentáció

- Használati útmutató, ESP32 huzalozási és konfigurációs leírás.
- Polling-, Nous/Tasmota-, helyi elemzési és döntési logika dokumentáció.
- Verziózott ESP32/DS18B20 kalibrációs jegyzőkönyv az első és második
  szenzorsorozattal.
