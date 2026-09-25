# Otthonautomatizálási eszközleltár

Frissítve az éles adatbázis és a hálózati leltár alapján: **2026-09-23**.

A tényleges, aktuális név, aktív állapot és helyiség-hozzárendelés elsődleges
forrása a `think260x` adatbázisa és az alkalmazás **Nyilvántartás** oldala. Ez a
fájl verziózott pillanatkép és az azonosítási szabályok dokumentuma; eszköz
áthelyezése vagy átnevezése után frissítendő.

Az alkalmazás a hálózati eszközöket hostname alapján éri el. Az IP-cím csak a
DHCP-foglalás vagy statikus cím ellenőrzésére és diagnosztikára szolgál.

## Zónák és helyiségek

- **Emelet:** Dolgozó, Háló, Kristófék, Rita, Veronika, Kis nappali, Emeleti
  fürdőszoba előtér.
- **Földszint:** Nappali, Vendégszoba, Ebédlő-konyha, Közlekedő, Kazánház.
- **Zónán kívüli:** Kültéri.

Minden tényleges áthelyezés időbélyeges `device_room_history` bejegyzést hoz
létre, és az eszköz aktív szenzorainak helyét is együtt frissíti.

## Aktív klíma-, termosztát- és kazáneszközök

| Forrás | Név | Hostname / azonosító | Helyiség |
|---|---|---|---|
| Computherm | `CT400 emelet` | `iot-computherm-emelet` | Emelet / Dolgozó |
| Computherm | `CT400 földszint` | `iot-computherm-foldszint` | Földszint / Vendégszoba |
| ConnectLife | `HS dolgozó` | `hisense-office` | Emelet / Dolgozó |
| ConnectLife | `HS háló` | `hisense-dorm` | Emelet / Háló |
| ConnectLife | `HS Kristófék` | `hisense-chris` | Emelet / Kristófék |
| ConnectLife | `HS Rita` | `hisense-rita` | Emelet / Rita |
| ConnectLife | `HS Veronika` | `hisense-veronica` | Emelet / Veronika |
| Kézi | `Bosch 7000i` | közvetlen tápellátás, kézzel nyilvántartott állapot | Földszint / Kazánház |

A ConnectLife adapter az AUID és a felhőben látható név együttesével ellenőrzi
az eszközazonosságot. Ezek a titkot nem tartalmazó, de telepítésspecifikus
azonosítók a nem verziózott `config/devices.json` fájlban vannak.

## Aktív hőmérsékleti és kontaktusos Zigbee-eszközök

| Típus | Név | Helyiség |
|---|---|---|
| Hőmérő | `Zb dolgozó` | Emelet / Dolgozó |
| Hőmérő | `Zb háló` | Emelet / Háló |
| Hőmérő | `Zb kisnappali` | Emelet / Kis nappali |
| Hőmérő | `Zb Kristófék` | Emelet / Kristófék |
| Hőmérő | `Zb Rita` | Emelet / Rita |
| Hőmérő | `Zb Veronika` | Emelet / Veronika |
| Hőmérő | `Zb nappali` | Földszint / Nappali |
| Hőmérő | `Zb vendégszoba` | Földszint / Vendégszoba |
| Kültéri hőmérő | `Zb ext` | Zónán kívüli / Kültéri |
| Radiátortermosztát | `TRV-G2 nappali bal` | Földszint / Nappali |
| Radiátortermosztát | `TRV-G2 Kristófék` | Emelet / Kristófék |
| Nyitásérzékelő | `Tuya dolgozó ablak` | Emelet / Dolgozó |
| Nyitásérzékelő | `Tuya erkélyajtó` | Emelet / Dolgozó |
| Nyitásérzékelő | `Tuya háló` | Emelet / Háló |
| Nyitásérzékelő | `Tuya Kristófék` | Emelet / Kristófék |
| Nyitásérzékelő | `Tuya Rita` | Emelet / Rita |
| Nyitásérzékelő | `Tuya Veronika` | Emelet / Veronika |
| Nyitásérzékelő | `Tuya nappali bal` | Földszint / Nappali |
| Nyitásérzékelő | `Tuya nappali jobb` | Földszint / Nappali |
| Nyitásérzékelő | `Tuya vendégszoba` | Földszint / Vendégszoba |

A Zigbee-eszközök stabil fizikai azonosítója az IEEE-cím, nem a szerkeszthető
friendly name. A collector automatikusan regisztrálja őket; az új eszköz
kezdetben helyiség nélkül és vezérlés nélkül jelenik meg.

A `TRV-G2 nappali bal` fizikai azonosítója `0xa4c138222cb21929`, a
`TRV-G2 Kristófék` azonosítója `0xa4c138972d1d2804`; mindkettő modellje
`TRV-ZBT`. Mindkét szelep automatikusan felismert, helyiséghez rendelt és
idősorosan gyűjtött eszköz.

## Routerek, MQTT-hőmérők és fogyasztásmérők

| Forrás | Név | Hostname / azonosító | Helyiség | Szerep |
|---|---|---|---|---|
| Zigbee2MQTT | `SP emelet` | `0xa4c138115783ffff` | Emelet / Emeleti fürdőszoba előtér | Zigbee router |
| Zigbee2MQTT | `SP lépcső` | `0xa4c138115778ffff` | Földszint / Közlekedő | Zigbee router |
| Zigbee2MQTT | `SP közlekedő` | `0xa4c13811554dffff` | Földszint / Közlekedő | Zigbee router |
| Zigbee2MQTT | `SP ebédlő` | `0xa4c13811bed2ffff` | Földszint / Ebédlő-konyha | Klarstein-mérés, UI-kapcsolás és Zigbee router |
| Kézi / külső mérés | `Klarstein Norderney` | helyi API nélkül | Földszint / Ebédlő-konyha | 2000 W-os villanyfűtő; a SONOFF méri |
| Shelly MQTT | `Sh ebédlő` | `shellyhtg3-48f6eebb92d4` | Földszint / Ebédlő-konyha | Deep-sleep hőmérő |
| Shelly MQTT | `Sh közlekedő` | `shellyhtg3-48f6eebb5c50` | Földszint / Közlekedő | Deep-sleep hőmérő |
| Tasmota | `Nous main IT` | `nous-mainit` | Emelet / Kis nappali | IT fogyasztásmérő |
| Tasmota | `Nous auxiliary IT` | `nous-auxit` | Emelet / Dolgozó | IT fogyasztásmérő |
| Tasmota | `Nous bojler` | `nous-bojler` / `192.168.0.46` / `C8:C9:A3:2B:34:11` | Földszint / Télikert WC | 1,8 kW-os villanybojler tápja, fogyasztásmérés és automation-időzítés |
| Tasmota | `Nous kazán` | `nous-kazan` / `192.168.0.47` / `C8:C9:A3:2B:35:60` | Földszint / Kazánház | Bosch tápellátása, kapcsolása és fogyasztásmérése |

A `.47` címes dugalj reléje az áramkimaradások után hibásnak látszott, de a
teljes Tasmota-reset és újrakonfigurálás után ismét működik. 2026. szeptember
24-én `Nous kazán` néven új mérési életet kezdett; a hibásként nyilvántartott
régi rekordot és annak 180 mérését a felhasználó kérésére töröltük.

A SONOFF S60ZBTPF Zigbee router-dugaljak `power`, `current`, `voltage` és
`energy` értékei idősorosan is bekerülnek a `sensor_readings` táblába. A
reléállapot a Zigbee állapotcache része, nem mérési idősor. Közülük csak az
`SP ebédlő` kapcsolható az UI-ról; a többi router védetten megfigyelési célú.

A Shelly stabil azonosítója a topic-prefix 12 hexadecimális karaktere. A két
MQTT-eszköz a korábbi kézi Shelly-rekord fizikai utódja; a régi device- és
szenzorrekordok inaktívak, történeti méréseik és helytörténetük megmaradtak.

## Rendszer- és hálózati eszközök

| Forrás | Név | Hostname | Helyiség |
|---|---|---|---|
| Linux | `260x` | `think260x.home` | Emelet / Kis nappali |
| Linux | `t470` | `t470` (`192.168.10.2`) | Emelet / Kis nappali |
| Hálózati felügyelet | `Xerox B235` | `xeroxb235.home` | Emelet / Kis nappali |

### Deco Wi-Fi mesh

| MAC-cím | Statikus DHCP-cím | Név |
|---|---|---|
| `e4:fa:c4:b7:ec:54` | `192.168.0.38` | `deco-main` |
| `e4:fa:c4:b7:bc:b0` | `192.168.0.39` | `deco-office` |
| `e4:fa:c4:b7:d1:80` | `192.168.0.40` | `deco-stair` |
| `ac:a7:f1:d0:6d:78` | `192.168.0.48` | `deco-konyha` |
| `ac:a7:f1:d0:2b:08` | `192.168.0.200` | `deco-telikert` |

Mind az öt egységet az automation `network_device` illesztője ICMP-pinggel
figyeli. A `deco-konyha` és a `deco-telikert` vezeték nélküli mesh-tag; a
télikerti egység a bojler és a napelemes inverter irányában is javítja a
lefedettséget.

A korábbi `thinkpad220x` nyilvántartási rekordot 2026-09-16-án a helyére
került `t470` vette át. Az eszköz- és szenzorrekordok azonosítói, a korábbi
mérések, a helyiség-hozzárendelés, a `192.168.10.2` cím, a 10 perces poll és a
korlátozott SSH-hozzáférés változatlan maradt; csak a gép neve és a forrás-
azonosítók változtak.

## Inaktív eszközök

- Nyolc korábbi ESP32/DS18B20 eszköz inaktív; már nem vesz részt a pollkörben
  vagy a vezérlési nézetben.
- Két korábbi kézi Shelly device és a hozzájuk tartozó kézi szenzorok inaktívak.
  A történeti adatok megőrzése miatt ezeket nem szabad törölni vagy az új MQTT-
  eszközhöz áthelyezni.

## Konfigurációs határok

A periodikus HTTP/UDP/ConnectLife poller fizikai elérési adatai a nem
verziózott `config/devices.json` fájlban vannak. A Zigbee2MQTT és Shelly MQTT
eszközök nem kerülnek ebbe a fájlba: saját collector szolgáltatásuk az MQTT-
üzenetekből hozza létre és tartja karban a nyilvántartási rekordokat.
