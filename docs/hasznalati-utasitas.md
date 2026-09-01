# Otthonklíma – használati útmutató

Ez a dokumentum az Otthonklíma webes alkalmazás napi használatát mutatja be a
menüpontok sorrendjében. Az alkalmazás ESP32/DS18B20 hőmérőket, Computherm
termosztátokat, Hisense/ConnectLife klímákat, Zigbee2MQTT/SONOFF és
Shelly H&T Gen3 MQTT-hőmérőket, Nous/Tasmota fogyasztásmérőket,
külső hőmérsékleti forrásokat, valamint kézzel rögzített üzemeltetési és
energiaadatokat kezel.

A későbbi automatikus fűtési és hűtési vezérlés elkülönített követelményeit a
[`docs/dontesi-logika.md`](dontesi-logika.md) dokumentum tartalmazza.

## 1. Elérés és bejelentkezés

Macen az alkalmazás címe:

```text
http://localhost:8081
```

Azonos helyi hálózaton levő telefonról a Mac helyi IP-címével érhető el:

```text
http://<mac-ip-címe>:8081
```

A Macnek ébren kell lennie, a dashboard szolgáltatásnak pedig futnia kell. A
Mac alvása alatt a weboldal nem érhető el és adatgyűjtés sem történik.

Minden adatoldal bejelentkezést kér. Két jogosultság van:

- **Csak olvasó (viewer):** megtekintheti az adatokat, grafikonokat és
  naplókat, de nem módosíthatja az adatbázist és nem vezérelhet eszközt.
- **Szerkesztő (editor):** adatot rögzíthet, kézi lekérdezést indíthat,
  eszközt vezérelhet, mérést törölhet és felhasználót kezelhet.

A jobb felső felhasználói területen látható a bejelentkezett felhasználó és ott
lehet kijelentkezni.

## 2. Klímaáttekintő – kezdőlap

A kezdőlap az adatbázisban levő **utolsó ismert állapotot** mutatja. Az oldal
megnyitása vagy frissítése önmagában nem kérdezi le az eszközöket.

Az ESP32-k kijelzése a **Nyers mérés** és a **Cselekedeti** hőmérséklet között
váltható. A választás az Eszközök, valamint a Zónák és helyiségek nézetben
egyaránt érvényes, tehát nem kötődik zónához. A munkamenet megőrzi a választást.
A cselekedeti érték csak kész `rézcső + doboz` kialakítással, érvényes
kalibrációval és döntési engedéllyel rendelkező ESP–DS szenzornál jelenik meg.
Más ESP32-nél a felület nem helyettesíti észrevétlenül nyers értékkel, hanem
jelzi, hogy még nincs cselekedeti adat. A kártya megmutatja az EMA
időállandóját, a kalibrációs korrekciót és a cselekedeti pont időpontját is.

### Nézetváltás

- **Eszközök:** az eszközök típus szerint csoportosítva jelennek meg
  (ESP32, Computherm, Hisense, Nous/Tasmota, Zigbee, Shelly MQTT és kézi
  eszközök). A szűrővel egy
  kiválasztott eszközcsoport önmagában is megjeleníthető. A mellette levő
  **Lekérdezési körben** jelölővel az összes vagy a kiválasztott típuson belül
  csak az automatikusan lekérdezett eszközök maradnak láthatók. A böngésző a
  típust és a jelölő állapotát is megjegyzi.
- **Zónák és helyiségek:** emelet, földszint és zónán kívüli terület szerint
  csoportosít; az eszköz nélküli helyiségeket is megmutatja. A helyiségszűrő
  egyetlen kiválasztott szobára szűkítheti a nézetet.

### Eszközkártyák értelmezése

A kártyák az eszköz típusától függően mutathatják:

- az utolsó hőmérsékletet és mérési időpontot;
- az elérhetőséget és az utolsó poll eredményét;
- a klíma be-/kikapcsolt állapotát, üzemmódját és célértékét;
- a Computherm mért és beállított hőmérsékletét;
- a Nous/Tasmota pillanatnyi teljesítményét, feszültségét, relé- és
  terheltségi állapotát, továbbá az összes fogyasztást és annak kezdőidejét;
- a Bosch 7000i kézi állapotát és szervizadatait.
- a Zigbee és Shelly hőmérők páratartalmát, elemállapotát, típusát és utolsó
  tényleges mérési idejét.

A Shelly H&T Gen3 elemes, deep-sleep eszköz; az `/online=false` nem offline
hiba. A kártya a legutóbbi tényleges mérés kora alapján fokozatosan változik:

- 0–1 óra: zöld, **Friss mérés**;
- 1–2 óra: sárga, **Alvó**;
- 2–4 óra: narancs, **Jelentés késik**;
- 4 óra felett: piros, **Nincs friss mérés**.

Az utolsó hőmérséklet minden állapotban látható marad.
A hőmérséklet és a `°C` jelölés a sárga, narancs és piros állapot színét is
követi; friss állapotban fekete marad.

A **Bekapcsolva** klímaállapot kiemelten jelenik meg. Az elérhető jelzés nem
azonos a bekapcsolt állapottal: azt mutatja, hogy az eszköz lekérdezhető volt.
Az engedélyezett, de sikertelenül lekérdezett eszköz jelzése **Offline**. Ha az
eszközt kivették az automatikus körből, a kártya **Lekérdezés kikapcsolva**
jelzést mutat, és nem ismétli meg a kikapcsolás előtti hálózati hibát.

### Kézi lekérdezés

A **Kézi lekérdezés** egy teljes eszközkört indít és az eredményt elmenti a
MariaDB-be. A kör végén az oldal frissül. A kézi és a tízperces automatikus kör
nem futhat egymásra; közös zárolás védi őket. Ha már fut egy kör, a másik nem
indul el.

A kézi kör nem tolja el a periodikus poll eredeti tízperces ütemezését.

A Nous/Tasmota lekérdezés csak adatot olvas. A dugalj reléjét nem kapcsolja,
és a Tasmota konfigurációját sem módosítja. A beüzemelés és a
feszültségkalibráció részletes leírása a
[`docs/nous-tasmota.md`](nous-tasmota.md) dokumentumban található.

### Külső hőmérséklet

A zónán kívüli részen az aktuálisan kiválasztott, friss külső forrás értéke is
megjelenik. A kártya forrásbélyege megkülönbözteti a saját **Zigbee eszköz**
mérését a **Webes lekérdezés** útján érkező időjárási adattól; helyi ESP32 és
kézi forrás esetén ezek saját jelölése látható.

## 3. Mérési előzmények

Ezen az oldalon a hőmérsékleti idősorok vizsgálhatók.

1. Jelölj ki egy vagy több eszközt.
2. Válassz időtávot: **1, 2, 6, 12 vagy 24 óra**, illetve **7 vagy 30 nap**.
3. Szükség esetén adj meg kezdő időpontot. Ilyenkor a kiválasztott hosszúságú
   időablak ettől az időponttól indul; üresen hagyva az időtáv a jelenig tart.
4. Nyomd meg a **Megjelenítés** gombot.

A lekérdezési körből kivett eszközök neve narancssárga, félkövér felirattal
jelenik meg. Ezek továbbra is kijelölhetők, így a korábban eltárolt méréseik
összehasonlíthatók az aktuálisan működő eszközök adataival.

A kijelölt eszközök közös időtengelyen, külön színű görbékkel jelennek meg. A
jelmagyarázat azonosítja a görbéket, alattuk pedig eszközönként látható:

Üres kezdő időpontnál a grafikon jobb széle mindig az oldal lekérésekor
aktuális időpont. Ha egy kiválasztott eszköz lekérdezése korábban megszűnt, az
utolsó mérésétől a jelenig üres szakasz marad; az időtengely nem rövidül az
utolsó rendelkezésre álló adatponthoz.

- minimum;
- átlag;
- maximum;
- mérési pontok száma.

Ez a nézet használható például több ESP32 kalibrációjának, egy ESP32 és egy
Computherm dinamikájának, illetve klíma- és szellőztetési események hatásának
összehasonlítására. A Shelly MQTT-hőmérsékletek közvetlenül a
`sensor_readings` idősorba kerülnek, ezért ugyanitt kiválaszthatók és
exportálhatók.

### CSV-export

A kijelölt eszközök és a megadott időablak a **CSV letöltése** gombbal széles
formátumban exportálható: az első oszlop a budapesti helyi idő, a további
oszlopok egy-egy kiválasztott eszköz mért hőmérsékletei. Az egy lekérdezési
körön belül legfeljebb 45 másodperc eltéréssel érkező eszközadatok közös sorba
kerülnek. Hiányzó mérés esetén a cella üres; a rendszer nem interpolál és nem
viszi tovább a korábbi értéket.

### Mérési kedvencek

Legfeljebb négy, felhasználónként külön tárolt kedvenc menthető. A kedvenc a
kiválasztott eszközöket és a relatív időtávot (1, 2, 6, 12 vagy 24 óra, illetve
7 vagy 30 nap) őrzi meg. Kezdő időpontot nem tárol: visszatöltéskor az időablak
mindig a jelenlegi időpontig tart. A kedvenc ugyanúgy használható grafikonhoz és
CSV-exporthoz, és szükség esetén törölhető vagy azonos néven felülírható.
Mentés előtt nevet kell adni az összeállításnak. Ha ez elmarad, az oldal
figyelmeztetést ad; a grafikon megjelenítéséhez és a CSV letöltéséhez viszont
nem kötelező kedvencnevet kitölteni.

### Szenzormérések nullázása

Szerkesztőként a lap alján jelölőnégyzetekkel kiválaszthatók a törlendő
szenzorok. A művelet:

- végleg törli a kijelölt szenzorok összes `sensor_readings` adatát;
- nem törli az eszközt, szenzort, állapotokat vagy pollnaplót;
- nem futhat adatgyűjtéssel egy időben;
- nem vonható vissza az alkalmazásból.

Nullázás előtt mindig készíts adatbázismentést. Kalibráció indításakor javasolt
a törlés után rögtön egy kézi lekérdezést futtatni, hogy az idősorok közös
kezdőpontot kapjanak.

## 4. Kért beállítások

Itt a Hisense és Computherm eszközök kívánt beállításai rögzíthetők az
adatbázisban.

**Fontos:** ez a menüpont jelenleg nem programozza át a fizikai eszközt. A
bejegyzés a későbbi döntési logika számára rögzített kérés. Az új kérés
időbélyeget kap, a korábbi függő kérés pedig felülírt (`superseded`) állapotba
kerül, ezért az előzmény megmarad.

## 5. Időprofilok

Eszközönként négy napi profil áll rendelkezésre:

- Munkanap 1;
- Munkanap 2;
- Munkanap 3;
- Ünnepnap.

Profilonként legfeljebb hat időablak adható meg. Az egymást nem érintő ablakok
közötti időben az eszköz kikapcsolt állapotúnak tekintendő.

### Heti hozzárendelés

A hét minden napjához külön profil rendelhető. A szombat és vasárnap is
felülírható például áthelyezett munkanap esetén.

### Dátum szerinti felülírás

Konkrét jövőbeli dátumhoz külön profil rendelhető. Ez elsőbbséget élvez a heti
hozzárendeléssel szemben, ezért ünnepnapok és rendkívüli munkanapok előre
rögzíthetők.

A lap megmutatja a mai, feloldott napi tervet is.

**Fontos:** az időprofil jelenleg tervet és kívánt állapotot készít; még nem
küld automatikusan parancsot a fizikai eszközöknek.

## 6. Nyilvántartás

Ez az oldal kezeli a zónákat, helyiségeket, eszköztípusokat, gyártókat és az
eszközök műszaki adatait.

- A zónák felvehetők, átnevezhetők és archiválhatók.
- A helyiségek felvehetők, átnevezhetők, archiválhatók és másik zónához
  rendelhetők.
- Új eszköztípus és gyártó vehető fel.
- Új eszköz helyiséghez vagy – helyiség nélkül – közvetlenül zónához
  rendelhető. Helyiség választásakor a zóna automatikusan követi a helyiséget.
- Nyilvántartható az elérési mód, a képesség, a hálózati címzés, az integrációs
  szerep, a támogatott üzemmódok, ventilátorfokozatok és kiegészítő programok.
- A **Lekérdezési körben** kapcsoló ideiglenesen kiveszi az eszközt az
  automatikus és kézi pollkörökből, de az eszköz és korábbi adatai megmaradnak.
  Az **Aktív nyilvántartási elem** ezzel szemben archiválásra szolgál.
- Az automatikus lekérdezés és az automatikus vezérlés külön engedélyezhető.
- A lekérdezési gyakoriság eszközönként 1–1440 perc között állítható. A közös
  gomb minden aktívan, hálózaton lekérdezett eszközt visszaállít a globális
  alapértékre (jelenleg 10 percre).
- Az eszköz összecsukott fejlécében is látható a beállított lekérdezési idő,
  ezért ellenőrzéséhez nem kell megnyitni az eszköz teljes adatlapját.

Az áthelyezés időbélyeges helytörténetet hoz létre. Korábbi mérésekkel
rendelkező eszközt törlés helyett archiválni kell, így a történeti adatok
megmaradnak.

Az UI-ban felvett eszköz csak akkor kérdezhető le ténylegesen, ha a program
támogatja a választott lekérdező illesztőt, és annak technikai konfigurációja
is rendelkezésre áll.

ESP32 és Tasmota eszköz mentésekor a hostname, IP-cím, MAC-cím és a
lekérdezési engedély automatikusan, atomikus fájlcserével átkerül a
`config/devices.json` pollerkonfigurációba is. A ConnectLife és Computherm
illesztők további, speciális technikai adatokat igényelnek; meglévő
konfigurációjuk közös mezőit a mentés frissíti, új integrációjukhoz viszont
továbbra is külön beállítás szükséges.

Az **Integrációs azonosító** nem tetszőleges leltári szám. ESP32 esetén
pontosan egyeznie kell a firmware `/api/v1/measurements` válaszának `device_id`
mezőjével; a jelenlegi konfigurációban ez a hostname. A panelre írt gyári
azonosítót ettől elkülönítve kell nyilvántartani.

### Lekérdezési idők

A kezdőlapi eszközkártyákon minden eszköznél látszik a beállított gyakoriság,
vagy az, hogy az automatikus lekérdezés ki van kapcsolva. A főmenü
**Lekérdezési idők** oldala egy helyen felsorolja az összes eszközt. A globális
alapértéktől eltérő, automatikusan lekérdezett eszközök a lista elejére kerülnek
és **Egyedi** jelölést kapnak. A **Módosítás** hivatkozás a Nyilvántartás
megfelelő eszközéhez vezet.

### Globális beállítások

A szerkesztők a főmenü **Globális beállítások** oldalán módosíthatják a
rendszerszintű működési értékeket: az alap lekérdezési időt, az időkorlátot,
az adatmentés paramétereit, a gnuplot elérési útját, valamint az
előkészített hűtési és fűtési biztonsági határokat. A mentés közvetlenül, de
atomikusan frissíti a projekt `.env` fájlját, és a kezelt értékeket azonnal
átvezeti a dashboard futó folyamatába. A periodikus poller minden ciklusban
újraolvassa a `.env` fájlt.

Ha a `.env` fájlt kézzel szerkesztették, a **A .env újratöltése** gombbal a
fájlban szereplő értékek betölthetők a futó dashboard folyamatába. A művelet
visszajelzi a megváltozott értékek számát. Az alkalmazás portja
(`DASHBOARD_PORT`), időzónája (`APP_TIMEZONE`) és munkamenet-titka
(`DASHBOARD_SECRET_KEY`) induláskor rögzül; ezek módosításakor az újratöltés
figyelmeztet, hogy teljes alkalmazás-újraindítás is szükséges. A fájlból kézzel
törölt kulcsot az újratöltés biztonsági okból nem törli a folyamat örökölt
környezetéből; ilyen változtatás szintén újraindítással érvényesíthető teljesen.

Az adatbázis és a ConnectLife felhasználónevei, jelszavai, illetve más titkok
nem jelennek meg és nem szerkeszthetők ezen a felületen.

## 7. Elemzések és jelentések

Az oldalon legfeljebb hét napos időablakból készíthető automatikus jelentés.
A számításokat és a magyar mondatokat is determinisztikus Python-szabályok
állítják elő; nyelvi modell nem vesz részt a folyamatban. Opcionálisan kézi
operátori megfigyelés is rögzíthető, amelyet a rendszer elkülönít a műszeres
tényektől.

A jelentés tartalmazza az értékelt szenzorok számát, szenzoronként a minimumot,
maximumot, átlagot és nettó változást, a külső referencia tartományát, valamint
az időablakkal átfedő klíma- és szellőztetési események számát. A több ESP32-n
egyidejűleg jelentkező eséseket összesítve jelzi.

Minden jelentés bekerül az adatbázisba az alábbiakkal:

- jelentési időablak és létrehozási időbélyeg;
- készítő felhasználó és generátorverzió;
- összesített minősítés;
- teljes, kereshető jelentésszöveg;
- szabályazonosítók és az egyes állítások bizonyítékai;
- az eredeti determinisztikus ténycsomag.

A tárolt jelentések szabad szöveggel, minősítéssel és létrehozási
dátumtartománnyal szűrhetők. A jelentés kizárólag tájékoztat: eszközt nem
vezérel és beállítást nem módosít.

## 8. Külső hőmérséklet

Az oldal tetején az aktuálisan kiválasztott külső mérés látható. Alatta
forrásonként beállítható:

- aktív vagy inaktív állapot;
- prioritási sorrend (a kisebb szám erősebb prioritás);
- legnagyobb elfogadható adatkor percben.

A rendszer az aktív és még friss források közül a legjobb prioritásút
választja. Tervezett/használható források:

- kültéri ESP32;
- Weather Underground helyi PWS;
- Open-Meteo;
- kézi külső adat.

Ha egy magasabb prioritású forrás inaktív vagy elavult, a rendszer a következő
használható forrásra vált.

## 9. Energia

Az oldal a villany- és gázóra kumulatív állását kezeli.

### Új óraállás rögzítése

1. Válaszd ki a mérőt.
2. Add meg a dátumot és időt.
3. Írd be az óra állását, ne az időszaki fogyasztást.
4. Szükség esetén adj megjegyzést.
5. Nyomd meg a **Rögzítés** gombot.

A rendszer az egymást követő óraállások különbségéből számítja a fogyasztást.
A havi gázadatokhoz egységesen 09:00 használható.

### Téves óraállás javítása

Szerkesztői jogosultsággal a korábbi óraállások listájában minden sor végén
megjelenik egy toll ikon. Erre kattintva javítható a mérő, a mérés időpontja,
az óraállás és a megjegyzés. A **Javítás mentése** után az érintett, valamint
az időrendben utána következő sor fogyasztási különbsége automatikusan az új
értékből számolódik. A javított rekord forrása kézi bejegyzésre változik, és a
rendszer eltárolja a javítást végző felhasználót.

### Kézi hőmérsékletmérések

A **Kézi mérések** oldalon alkalmi ellenőrző hőmérsékletek vihetők fel. A
választható műszert előbb a Nyilvántartásban hőmérőként, kézi/vizuális eléréssel
és kézzel leolvasható képességgel kell felvenni. A méréshez megadható az eszköz,
a tényleges mérési időpont, a hőmérséklet és egy opcionális megjegyzés.

A kézi adat ugyanabba a hőmérsékleti idősorba kerül, de alkalmi jellege miatt
nem jelenik meg a Mérési előzmények grafikonján. A Kézi mérések naplójában és az
eszköz kezdőlapi kártyáján látható. Ellenőrző adatként használható, de önmagában
nem indít automatikus vezérlést. A kezdőlapon az egy óránál régebbi legutolsó
mérési érték piros, félkövér jelzést kap.

## 10. Adatmentés

Ez a menüpont csak szerkesztőként látható.

A **Mentés készítése** teljes, tömörített MariaDB-exportot hoz létre. A mentés:

- megvárja a futó lekérdezés végét;
- a teljes export idejére blokkolja a pollt és a klímavezérlést;
- ideiglenes fájlba készül;
- csak sikeres befejezés után válik letölthetővé.

A korábbi mentések listából letölthetők. Az automatikus napi mentést a poller
készíti a `.env` beállításai szerint. Az automatikus megőrzési korlát nem törli
a kézi vagy átnevezett mentéseket.

## 11. Szellőztetés

A szellőztetés két külön műveletből áll.

### Indítás

1. Válaszd ki a helyiséget vagy helyiségeket.
2. Add meg az indítás időpontját és opcionális megjegyzést.
3. Indítsd el az eseményt.

A rendszer automatikusan eltárolja az akkor aktív külső hőmérsékleti forrást és
annak értékét. Egy helyiséghez egyszerre csak egy aktív szellőztetés tartozhat.

### Lezárás

Az aktív eseménynél add meg a befejezési időt, majd nyomd meg a
**Szellőztetés lezárása** gombot. A lezáráskor a rendszer ismét eltárolja az
akkori külső forrást és hőmérsékletet. Így a mérési görbéken látható gyors
változások később értelmezhetők.

## 12. Klíma

Ez az oldal tényleges eszközvezérlést, programozott futást, eseménynaplót és
auditot is tartalmaz.

### 12.1 Közvetlen klímavezérlés

1. Válaszd ki a helyiséget.
2. Ellenőrizd a legutóbb lekérdezett állapotot és annak időpontját.
3. Kikapcsolt eszköznél add meg a célhőmérsékletet és válaszd ki a
   ventilátorsebességet, majd válaszd a
   **Klíma bekapcsolása** gombot.
4. Bekapcsolt eszköznél a **Klíma kikapcsolása** gomb jelenik meg.

A rendszer bekapcsolást csak kikapcsolt, kikapcsolást csak bekapcsolt eszköznél
küld. A parancs előtt és után ConnectLife-lekérdezés történik. Az igazolt
eredmény rögtön bekerül az állapot- és klímaesemény-naplóba, ezért nem kell
megvárni a következő tízperces pollt.

Bekapcsoláskor a bekapcsolási állapot, a célhőmérséklet és a kiválasztott
ventilátorsebesség változik. Az üzemmódot és a kiegészítő programokat ez a
funkció nem módosítja. A sikeres visszaellenőrzéshez a ventilátorfokozatnak is
egyeznie kell a kéréssel.

### 12.2 Programozott klímafutás

A programozott futás egy vagy több, automatikusan egymás után végrehajtott
klímalépést készít.

1. Válaszd ki a helyiséget.
2. Add meg a kezdési dátumot és időt. Az aktuális idő megadásával az indítás
   gyakorlatilag azonnali.
3. Az első lépéshez add meg a futásidőt, célhőmérsékletet (25–30 °C) és a
   ventilátorfokozatot. A **Csendes** is választható.
4. Válaszd ki a továbblépést:
   - **A futásidő végén**: a megadott idő elteltével indul a következő lépés;
   - **Szenzor a küszöb alatt**: válassz az adott helyiség aktív hőmérői közül,
     majd válaszd ki, hogy a mérés érje el a célértéket, vagy a célérték és a
     mérés különbsége legyen legalább 0,5 °C, legalább 1,0 °C, illetve szigorúan
     1,5 °C-nál nagyobb.
5. Szenzoros váltásnál a futásidő biztonsági maximumként működik. Csak a lépés
   kezdete után készült, legfeljebb 15 perces mérés válthat tovább.
6. A **+ Új lépés** gombbal adj hozzá további sorokat. Legfeljebb nyolc lépés
   menthető; az utolsó feltételének teljesülésekor a klíma kikapcsol.
7. Nyomd meg a **Program mentése** gombot.

A program és minden lépése adatbázisban marad, ezért az oldal bezárható. A
poller körülbelül 10 másodpercenként ellenőrzi az esedékes műveleteket. Az
indítás, minden paraméterváltás és a leállítás is visszaolvasással ellenőrzött
és auditált.

Állapotok:

- **ütemezve:** még nem indult el, törölhető;
- **indítás / leállítás:** a parancs végrehajtása folyamatban;
- **fut:** a klíma bekapcsolt; a listában az aktuális programlépés is látszik;
- **befejezve:** az automatikus leállítás igazolt;
- **törölve:** a még el nem indult programot kézzel törölték;
- **hiba:** a parancs vagy annak visszaellenőrzése sikertelen.

Ha a Mac az indulás idején alszik, de ébredéskor az eredeti futási ablak még
tart, a klíma késve elindul, és a tényleges indulástól számított futásidő után
áll le. Ha a teljes ablak alvás közben lejárt, nem indul el utólag.

### 12.3 Kézi esemény rögzítése

Ez korrekciós lehetőség távirányítóval vagy más felületről végzett kapcsolás
naplózására; önmagában nem vezérli a klímát. A periodikus poll a külső
állapotváltozást egyébként automatikusan felismeri, legfeljebb egy pollciklusnyi
késéssel.

### 12.4 Klímanapló és audit

A klímanapló az üzemeseményeket, azok kezdő és záró célértékét mutatja. Az
audit minden UI-ból vagy időzítőből indított kísérletet megőriz:

- kérés időpontja;
- eszköz és parancs;
- célérték;
- siker, elutasítás vagy hiba;
- kezdeményező felhasználó.

## 13. Felhasználók

Csak szerkesztőként érhető el.

Új felhasználónál meg kell adni:

- legalább három karakteres felhasználónevet;
- legalább tíz karakteres jelszót;
- viewer vagy editor szerepkört.

Meglévő felhasználó szerepköre, aktív állapota és jelszava módosítható. Az
utolsó aktív szerkesztő nem kapcsolható ki, és a rendszer védi a saját
szerkesztői hozzáférés véletlen megszüntetését.

## 14. Gyakori napi munkafolyamatok

### Friss állapot ellenőrzése

1. Nyisd meg a Klímaáttekintőt.
2. Nézd meg az utolsó lekérdezés időpontját.
3. Ha azonnali adat kell, indíts kézi lekérdezést.
4. Várd meg a kör végét és az oldal frissülését.

### Kontrollált klímateszt

1. Ellenőrizd, hogy nincs aktív szellőztetés vagy más zavaró esemény.
2. A Klíma menüben készíts programozott futást kezdéssel és egy vagy több,
   célértéket, ventilátorfokozatot, futásidőt és továbblépési feltételt tartalmazó
   lépéssel.
3. Ne mozgasd a szenzorokat.
4. A futás és visszaállás után a Mérési előzményekben jelöld ki együtt az
   érintett ESP32-ket, Computhermet és szükség szerint Hisense eszközt.
5. A klímanapló időpontjai alapján értékeld a le- és felfutást.

### Szenzorkalibráció

1. Helyezd az érzékelőket azonos körülmények közé.
2. Hagyd őket 45–60 percig stabilizálódni.
3. Készíts adatbázismentést.
4. Nullázd a kiválasztott szenzorokat.
5. Indíts azonnal kézi lekérdezést.
6. Legalább 24 órán át ne mozdítsd el őket.
7. Többes grafikonon hasonlítsd össze az idősorokat.

## 15. Fontos biztonsági és értelmezési szabályok

- Az UI-ban és a grafikonokon látható időpontok `Europe/Budapest` helyi idő
  szerint jelennek meg (télen CET, nyáron CEST); az adatbázis UTC
  időt tárol.
- A nyers DS18B20-adat gyors légáramra erősebben reagálhat, mint a burkolt
  Computherm. A nyers értékeket megőrizzük; a vezérlési szűrés külön feladat.
- A Hisense beltéri hőmérséklet információs adat, nem elsődleges helyiségi
  vezérlési mérés, mert a beltéri egység magasan és saját légáramában van.
- A Kért beállítások és Időprofilok jelenleg nem vezérlik a fizikai eszközt.
- A Klíma közvetlen és időzített vezérlése viszont valódi eszközparancsot küld.
- Az automatikus jelentéskészítő nem kaphat eszközvezérlési jogosultságot.
- Törlés, klímavezérlés és mentés előtt mindig ellenőrizd a kiválasztott
  eszközt, állapotot és időpontot.

## 16. Ha valami nem működik

- Ellenőrizd, hogy a Mac ébren van-e.
- Nézd meg a kezdőlapon az utolsó poll időpontját és a hibás eszköz jelzését.
- Indíts kézi lekérdezést.
- ESP32 esetén próbáld meg a hostnevet pingelni, majd ellenőrizd a
  `/health` és `/api/v1/measurements` végpontot.
- Ha klímaparancs sikertelen, ne ismételd gyorsan egymás után; nézd meg az
  auditbejegyzést és a ConnectLife állapotát.
- Ha mentés vagy vezérlés alatt más művelet nem indul, várd meg a közös zár
  felszabadulását.
- Rendszerszintű diagnosztikához a projekt `logs` könyvtárában találhatók a
  dashboard és a poller naplói.
