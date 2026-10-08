# Háromhelyiséges automatikus ventilátoros klímafűtési próba – 2026. október 7.

## Cél és tervezett beállítás

A próba Rita szobájában, a dolgozóban és a hálóban egyszerre vizsgálja a
Hisense klímák fűtési viselkedését:

- üzemmód: fűtés;
- célhőmérséklet: 21 °C;
- ventilátor: Auto;
- Rita belső ajtaja csukva, ezért Rita külön hőtechnikai zónát alkot;
- a dolgozó–háló ajtó nyitott marad.

A radiátorközeli TRV-hőmérsékletek nem részei az összehasonlításnak.

## Bekapcsolás előtti alapállapot

Az időpontok Europe/Budapest helyi idő szerint értendők. A dolgozói Computherm
értéke soron kívüli közvetlen lekérdezésből származik; a Zigbee eszközöknél a
legutóbbi tényleges MQTT-jelentés időpontja szerepel.

| Forrás | Hőmérséklet | Mérési idő |
|---|---:|---:|
| Zb Rita | 20,1 °C | 19:35:17 |
| Zb dolgozó | 20,2 °C | 19:31:25 |
| CT400 emelet | 20,0 °C | 19:38:22 |
| Dolgozó cselekedeti átlag | 20,1 °C | számított |
| Zb háló | 19,8 °C | 19:36:26 |
| Zb ext | 16,2 °C | 19:32:10 |

Tájékoztató Hisense saját beltéri mérések a bekapcsolás előtti utolsó
ConnectLife-lekérdezésből, 19:31:10-kor:

| Klíma | Saját beltéri mérés | Utolsó visszaolvasott állapot |
|---|---:|---|
| HS Rita | 22,0 °C | kikapcsolva |
| HS dolgozó | 21,0 °C | kikapcsolva |
| HS háló | 21,0 °C | kikapcsolva |

Rita belső ajtaja 19:36:22-kor `contact=true`, vagyis csukott állapotot
jelentett.

## Értelmezési megjegyzés

A dolgozó a délelőtti, egyórás közepes ventilátoros próba után még nem tért
vissza a reggeli 18,4–18,6 °C-os kiindulási tartományba. Emiatt ez a mérés nem
közvetlen ismétlése a délelőtti próbának. Külön tesztként használható annak
megfigyelésére, hogyan viselkedik három klíma 21 °C-os célértékkel, automatikus
ventilátoron, eltérő ajtó- és helyiségi körülmények között.

## Folytatáskor rögzítendő

- a három klíma első igazolt bekapcsolt állapota és tényleges beállítása;
- Rita ajtajának állapota a mérési pontoknál;
- Zb Rita, Zb dolgozó, CT400 emelet, Zb háló és Zb ext;
- a három Hisense saját beltéri hőmérséklete;
- komfortérzet helyiségenként;
- a visszaszabályozás, kikapcsolás és esetleges utófutás időpontja.

## Futás közbeni megfigyelések

- A dolgozói klímánál a bekapcsolás után körülbelül 1 perccel indult meg a
  tényleges légbefúvás. Ez rövidebb a délelőtti próba hozzávetőleg 2 perces
  előfűtésénél; az eltérő kezdeti és kültéri hőmérséklet miatt a két érték még
  nem tekinthető a készülék állandó jellemzőjének.
- Az első, 19:41:21-kor készült ConnectLife-visszaolvasás nem igazolta mindhárom
  tervezett beállítást:

  | Klíma | Üzem | Cél | Ventilátor | Nyers ventilátorérték |
  |---|---|---:|---|---:|
  | HS dolgozó | fűtés, bekapcsolva | 21 °C | Közepes | `t_fan_speed=7` |
  | HS háló | fűtés, bekapcsolva | 21 °C | Auto | `t_fan_speed=0` |
  | HS Rita | fűtés, bekapcsolva | 23 °C | Auto | `t_fan_speed=0` |

  A háló Auto állapota továbbra is `0` értéket ad, ezért a dolgozó `7` értéke
  nem az Auto által választott pillanatnyi fordulatnak, hanem megmaradt közepes
  beállításnak tekintendő. Rita célértéke is eltér a tervezett 21 °C-tól; a
  próba csak a beállítások helyesbítése és újabb visszaolvasása után tekinthető
  egységes 21 °C / Auto tesztnek.
- A dolgozói klímát a hibásan megmaradt közepes fokozat miatt a felhasználó
  kikapcsolta, megvárta a leállását, majd már kiválasztott Auto ventilátorral
  kapcsolta vissza. A 19:51:44-kor végzett soron kívüli ConnectLife-lekérdezés
  igazolta: bekapcsolva, fűtés, 21 °C, Auto, `t_fan_speed=0`. A klíma saját
  beltéri érzékelője közvetlenül az újraindítás után 27 °C-ot közölt; ez a
  tranziens érték ismét alátámasztja, hogy a Hisense saját mérése nem lehet
  elsődleges helyiségi vezérlési alap.
- A dolgozónál az Auto fokozatot az első bekapcsolás után választották ki a
  közepes helyett. Az iPhone ConnectLife alkalmazás ezután Auto állapotot
  mutatott, a készülék nyers visszaolvasása azonban továbbra is
  `t_fan_speed=7`, vagyis közepes maradt. A háló és Rita már Auto beállítással
  kapcsolt be, és náluk az első visszaolvasás is `t_fan_speed=0` volt. Ez arra
  utal, hogy az alkalmazás kijelzése lehet optimista vagy gyorsítótárazott,
  illetve az indulási szakaszban küldött fokozatváltást a készülék felülírhatja.
  A későbbi automation-parancsoknál ezért a célértéket és ventilátorfokozatot
  lehetőleg bekapcsolás előtt kell beállítani, majd a bekapcsolás után nyers
  állapot-visszaolvasással ellenőrizni; eltéréskor a parancs nem tekinthető
  sikeresnek.

## Utófutás utáni végállapot

A felhasználó 21:13 körül kikapcsolta mindhárom klímát, majd megvárta az
utófutás végét. A soron kívüli ConnectLife-visszaolvasás 21:13:57-kor mindhárom
készüléket kikapcsolt, online állapotúnak mutatta. Rita ajtaja továbbra is
`contact=true`, vagyis csukott volt.

| Forrás | Indulás | Végállapot | Változás |
|---|---:|---:|---:|
| Zb Rita | 20,1 °C | 23,7 °C (21:09:06) | +3,6 °C |
| Zb dolgozó | 20,2 °C | 23,4 °C (21:11:56) | +3,2 °C |
| CT400 emelet | 20,0 °C | 22,3 °C (21:13:22) | +2,3 °C |
| Dolgozó cselekedeti átlag | 20,1 °C | 22,85 °C | +2,75 °C |
| Zb háló | 19,8 °C | 22,4 °C (21:11:38) | +2,6 °C |
| Zb ext | 16,2 °C | 14,4 °C (21:07:05) | −1,8 °C |

A klímaesemények periodikus állapotészlelés szerinti időablakai:

| Klíma | Észlelt kezdet | Észlelt vég | Visszaolvasott cél |
|---|---:|---:|---:|
| HS Rita | 19:41:21 | 21:13:00 | 23 °C |
| HS háló | 19:41:21 | 21:13:00 | 21 °C |
| HS dolgozó | 19:41:21 | 21:13:10 | 21 °C |

A dolgozó futása közben történt egy kikapcsolás és Auto fokozattal végzett
újraindítás, ezért annak folyamata nem tekinthető megszakítás nélküli azonos
beállítású futásnak. Rita célértéke az első és az utolsó visszaolvasásban is
23 °C volt, így a tervezett 21 °C-os érték nem érvényesült.

A kikapcsolás utáni Hisense saját beltéri értékek: Rita 28 °C, dolgozó 27 °C,
háló 25 °C. Ezek a helyiségi Zigbee-méréseknél 1,3–4,3 °C-kal magasabbak, ezért
ismét nem használhatók elsődleges helyiségi hőmérsékletként.

## Előzetes értékelés

- A háló 21 °C-os cél és Auto ventilátor mellett 2,6 °C-ot melegedett, miközben
  a kültér 1,8 °C-ot hűlt. Az Auto üzem tehát ebben a helyiségben is jelentős
  felfűtést végzett.
- A dolgozó cselekedeti hőmérséklete 2,75 °C-kal emelkedett. A Zigbee és a
  Computherm végső eltérése 1,1 °C, kisebb a délelőtti közepes ventilátoros
  próba 2,2 °C-os végső eltérésénél, de a futás eltérő kezdeti állapotú és
  hosszabb volt, ezért ez még nem tiszta fokozat-összehasonlítás.
- Rita zárt ajtó mellett 3,6 °C-ot melegedett, de 23 °C-os célértékkel ment;
  eredménye nem hasonlítható közvetlenül a két 21 °C-os helyiséghez.
- A szobai Zigbee-mérések mindhárom helyiségben a beállított 21 °C fölé
  kerültek. Ez azt jelzi, hogy a klíma saját, magasabb és saját légáramában
  levő érzékeléséhez tartozó 21 °C-os cél nem azonos 21 °C-os helyiségi
  komforttal.

Egy következő összehasonlító próbán mindhárom beállítást indulás előtt kell
megadni, majd azonnal visszaellenőrizni. Rita is 21 °C / Auto értékkel induljon,
a dolgozó futását pedig ne szakítsa meg fokozatkorrekció.
