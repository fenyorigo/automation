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

- [x] A Computherm-kártyákon jelenjen meg a hozzájuk tartozó Bosch kazán tényleges
  be- vagy kikapcsolt állapota.
- [x] Ha a Computherm fűtést kér, de a kazán ki van kapcsolva, az UI ezt külön,
  cselekvést igénylő állapotként jelezze: távoli beavatkozás helyett a kazánt
  helyben be kell kapcsolni.
- [x] Az emeleti observer a Computherm–Bosch kapcsolatot megfigyeli, de nem
  vezérli. A földszinti fűtési döntés külön következő lépés marad.

## Bosch üzemmódok teljesítményalapú felismerése

- [ ] A következő kazánszerviz alatt nagy gyakorisággal rögzíteni a Bosch
  nyugalmi, melegvíz-indítási, fűtésindítási, tartós fűtési és leállás utáni
  teljesítményprofilját.
- [ ] Ellenőrizni, hogy a melegvíz-üzem a Nous mérésében biztosan
  felismerhető-e, vagy csak túl rövid gyújtási tüske jelenik meg.
- [ ] Csak bizonyítottan fűtésre jellemző, tartós vagy ismétlődő profilból
  következtetni automatikusan fűtésre. Egyszerű, pillanatnyi alapfogyasztás-
  növekedés önmagában ne írja át a kézi állapotokat.
- [ ] Megbízható fűtésfelismerés esetén a kimaradt kézi jelölést automatikusan
  pótolni: **Fűtés** és **Melegvíz-szolgáltatás** egyszerre váljon aktívvá,
  mert fűtés mellett a melegvíz is engedélyezett. A fordított következtetés
  tilos: felismert melegvíz-üzem nem jelenti azt, hogy a fűtés is engedélyezett.
- [ ] Az automatikus következtetéshez forrást, időpontot és lehetőség szerint
  biztonsági szintet tárolni, hogy megkülönböztethető legyen a kézi jelöléstől.
- [ ] Ellenőrizni a Bosch kezelőpaneljén, hogy feszültség alá helyezve a
  melegvíz-szolgáltatás valóban mindig automatikusan rendelkezésre áll-e. Ha
  igen, az igazolt Nous-bekapcsolás és a kb. 5 W-os panel-alapfogyasztás a
  melegvízjelölést is automatikusan állítsa aktívra; a fűtés maradjon külön
  állapot.
- [ ] A szerviz alatt megmérni a kazán leállása utáni keringetőszivattyú-
  utánfutást. A jelenlegi becslés kb. 30 másodperc; ezt az események és a
  teljesítményprofil értelmezésénél figyelembe kell venni.

## SONOFF TRV-ZBT radiátorszelepek

- [ ] A két megrendelt TRV-ZBT érkezése után Zigbee2MQTT-párosítás,
  helyiség-hozzárendelés és időbélyeges mérésgyűjtés.
- [ ] A radiátor közelében mért TRV-hőmérséklet aktív gázfűtés alatt nem lehet
  helyiségi hőigény alapja. Az egyszerű induló szabály szerint csak kikapcsolt
  Bosch/gázfűtés mellett használható kiegészítő helyiségi információként.
- [ ] A dolgozószobai radiátoron a bútorzat miatt nincs és nem lesz TRV; az
  emeleti gázstratégia azt vizsgálja majd, mennyire foghatók vissza a többi
  helyiség radiátorai a várhatóan leghűvösebb dolgozóhoz képest.

## Megfigyelő logikából automatikus vezérlés

- [ ] Az emeleti hűtési observer egyelőre ne küldjön automatikus parancsot.
  Következő lépésként a javaslatok és blokkolások üzemi megfigyelése, majd külön
  jóváhagyott fázisban a 25 °C-os célértékkorlát és a nyílászáró-kapuzás
  végrehajtása következhet.
- [ ] A későbbi kézi és időzített klímaindításnál a felhasználó külön dönthesse
  el, hogy a nyílászáró állapota blokkolja-e a műveletet. Jövőbeli indításnál
  az akkori, nem az űrlap kitöltésekor fennálló kontaktusállapotot kell
  értékelni.
- [ ] Az emeleti fűtési observer téli mérésekkel ellenőrzendő. Kevert
  klíma–gáz üzem a radiátorszelepek bizonyított vezérelhetőségéig nem készül.
- [ ] A földszint marad kizárólag Computherm/Bosch gázfűtési zóna; a rendszer
  jelenleg csak megfigyeli és jelzi az állapotot.

## Energiaoptimalizálás

- [ ] A rögzített villany- és gázszámlákból számítani a teljes becsült
  fűtési költséget. A közös energiaalap az `ENERGY_MJ_PER_KWH=3.6`.
- [ ] Felvenni a Hisense típusonkénti, külső hőmérséklettől függő COP-görbét,
  majd a klíma–gáz választást a tényleges tarifákból számított COP-határhoz
  kötni. Kiinduló képlet:
  `villany teljes Ft/kWh ÷ (gáz Ft/kWh ÷ kazánhatásfok)`.
- [ ] A szauna első becslését további méréssel ellenőrizni: az egyórás időszak
  teljes fogyasztása 3 kWh volt, amelyből az 1,07 kWh körüli hosszú távú
  alapfogyasztást levonva kb. 1,93 kWh, kerekítve 2 kWh tulajdonítható a
  szaunának.

## Teljes házas Zigbee-visszatérési próba

- [ ] Egy későbbi, tervezett áramtalanítás után minden nyitásérzékelőn
  ellenőrizni egy csukás–nyitás eseményt. A két dolgozói érzékelő kontrollált
  bridge-próbája már sikeres volt, de ez még nem helyettesíti a teljes ház
  végpontjainak ellenőrzését.
