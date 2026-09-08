# Teendők

## Zigbee újraindítási megbízhatóság

- [x] Kontrollált Sonoff/Tasmota Zigbee bridge-áramtalanítási próba. A teszt előtt
  a Zigbee2MQTT szabályosan leállítandó, a bridge visszatérése és a 8888/TCP
  port elérhetősége után indítandó újra. Ezután ellenőrizni kell, hogy a két
  dolgozói Nous/Tuya nyitásérzékelő párosítás nélkül küld-e új állapotot.
  A 2026-09-07-i próba sikeres volt: mindkét eszköz nyitás- és záráseseménye
  megérkezett, és egy közös, szabályosan lezárt szellőztetési esemény készült.
- [x] Kivizsgálni, miért éri el a Zigbee2MQTT leállítása a systemd 90 másodperces
  időkorlátját. A TCP-n elért Z-Stack koordinátor mentése mérve 96,745
  másodpercig tartott, ezért a 90 másodperces alapérték megszakította a
  zigbee-herdsman leállását. A szolgáltatás drop-inja 3 perces leállási határt
  és időtúllépéskor coredump nélküli `kill` módot állít be. Az ellenőrző
  leállás 95–96 másodperc alatt végigment és a koordinátormentés elkészült.
- [ ] Követni a Zigbee2MQTT `write after end` leállási hibáját. A tiszta
  zigbee-herdsman leállás után későn érkező TCP `Port closed` naplósor már
  lezárt Winston transportba ír, ezért a folyamat `1/FAILURE` kóddal távozik.
  Ez upstream hiba; `SuccessExitStatus=1` nem használható, mert valódi
  futási hibákat is sikeresnek minősítene és kikapcsolná a restartvédelmet.
- [x] A nyitásérzékelő régi, de a Zigbee2MQTT szerint elérhető állapota
  önmagában nem vezérlési hiba. Nyitott vagy ismeretlen állapot, illetve az
  explicit `availability=offline` blokkolja a hűtési javaslatot.

## Fűtési állapotkapcsolat a Computherm-kártyákon

- A Computherm-kártyákon jelenjen meg a hozzájuk tartozó Bosch kazán tényleges
  be- vagy kikapcsolt állapota.
- Ha a Computherm fűtést kér, de a kazán ki van kapcsolva, az UI ezt külön,
  cselekvést igénylő állapotként jelezze: távoli beavatkozás helyett a kazánt
  helyben be kell kapcsolni.
- Az emeleti és földszinti Computherm–kazán kapcsolatot a fűtési vezérlés
  tervezésekor kell véglegesíteni; ez nem része az 1.3.0 hűtési observernek.
