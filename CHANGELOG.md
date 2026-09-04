# Változásnapló

A projekt a szemantikus verziózás elvét követi. A kiadás dátumai budapesti
helyi dátumok.

## Kiadatlan

### Új funkciók

- Új `docs/gázszámla-felvitele.md` gyakorlati útmutató készült a
  részszámlákhoz, az augusztus 1-jei jogosultsági évváltással, számításokkal
  és ellenőrző összegekkel; az elszámolószámla külön későbbi folyamat marad.
- A gázszámla-útmutató külön ellenőrző pontokat kapott a kategóriákhoz,
  dátumokhoz, mértékegységekhez, páros mérőállásmezőkhöz és kerekítésekhez.
- Új v1.35 kedvezményes gázjogosultsági modell az augusztus 1.–július 31.
  közötti, idő- és fogyasztásarányosan elszámolt 63 645 MJ-os kerethez; ez a
  szolgáltatói számlázási ciklustól és a havi részszámla-becsléstől külön adat.
- A gázszámla fogyasztási részleteinél a korrigált mennyiség és a hőmennyiség
  automatikusan számolódik, de a számlán szereplő kerekített érték felülírható.
- A 2025.07.07–2025.08.06 számlaidőszak `1,0000` korrekciós tényezője és
  `35,37 MJ/m³` fűtőértéke bekerült a gázátváltási törzsadatok közé.
- A számlafejek, fogyasztási részletek és számlatételek ceruza ikonnal,
  közvetlenül az Energia oldalon javíthatók.
- Új globális `ENERGY_MJ_PER_KWH=3.6` átváltási állandó és kWh-egyenérték
  segíti a gáz- és villamos fűtés összehasonlítását.
- A számlafej és a számlatételek bruttó összege automatikusan számolódik a
  megadott nettó és ÁFA-adatokból, szerveroldali ellenőrző számítással.
- A számlatételek nettó összege a mennyiség és egységár szorzatából, a bruttó
  ebből és az ÁFA-kulcsból egész forintra kerekítve készül; a szolgáltatás
  kategória 0%, minden más kategória 27% alapértéket kap.
- Javítva az Energia oldal üres URL-hivatkozásnál fellépő JavaScript-hibája,
  amely megakadályozta a számlatételek automatikus ÁFA- és összegszámítását.
- A számlatétel kategóriája automatikusan kitölti a szabványos megnevezést és
  mértékegységet; szolgáltatásnál legördülőből választhatók az OtthonSOS
  Komfort és Garancia Médium tételek.
- Új v1.34 energia-számlázási modell elszámolási ciklusokkal, időben érvényes
  gázátváltással, tarifákkal, sávmegosztással, fix becslési díjakkal, valamint
  szolgáltatói számla-, fogyasztási és tételsorokkal.
- Az Energia oldalon felviteli és áttekintő felület készült minden új
  számlázási törzsadathoz; a saját leolvasás és az MVM becsült fogyasztása
  külön adatsor marad.
- Automatikus Zigbee2MQTT eszközfelfedezés és legutolsóérték-kijelzés SONOFF
  routerekhez, beltéri és kültéri hőmérőkhöz.
- Zigbee temperature, humidity és battery jelentések időbélyeges mentése a
  közös `sensor_readings` táblába, stabil duplikációvédelemmel és egyszeri
  cache-kezdőponttal.
- Az egypontos hőmérsékleti idősorok látható pontként jelennek meg; két vagy
  több mérésnél marad a vonalgrafikon.
- Külön, eseményvezérelt Shelly H&T Gen3 MQTT collector temperature, humidity,
  battery és `battery_voltage` idősorokkal a meglévő mérési modellben.
- Deep-sleep-tudatos Shelly UI zöld/sárga/narancs/piros, 1/2/4 órás
  frissességi fokozatokkal; az `/online=false` nem minősül hibának.
- A kézi `shelly-dolgozo` és `shelly-nappali` fizikai utódjainak automatikus,
  történetmegőrző párosítása.
- A kültéri hőmérséklet-kártyán külön forrásbélyeg jelzi a Zigbee eszközt,
  webes lekérdezést, helyi szenzort vagy kézi adatot.
- A Nyilvántartásból eszközönként új mérési élet indítható: az összes kapcsolódó
  idősor törlődik, miközben az eszköz-, szenzor- és helyiségelőzmény megmarad.
- Az ESP32 nyers/cselekedeti hőmérsékletválasztó aktív ESP32 eszköz nélkül nem
  jelenik meg a kezdőlapon.
- Az Energia oldalon a korábbi óraállások villany- és gázórára szűrhetők, a
  mérőkártyák pedig mutatják az aktuális év kumulált fogyasztását és kezdőpontját.
- A 31 napnál későbbi első éves óraállásnál az előző mérésből időarányosan
  becsült január 1-jei kezdőértékkel számolható az éves fogyasztás.
- A gázóra naptári éves összesítése helyett a legutóbbi novemberi leolvasással
  kezdődő aktuális számlázási időszak kumulált fogyasztása jelenik meg.

### Üzemeltetés

- Új `automation-zigbee2mqtt.service` és `automation-shelly-mqtt.service`
  Fedora systemd egységek, Mosquitto- és MariaDB-függőséggel.
- A teljes Fedora mentés Mosquitto/Zigbee2MQTT állapotot ment, és visszaállítja
  az MQTT collectorok mentés előtti futási állapotát.

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
