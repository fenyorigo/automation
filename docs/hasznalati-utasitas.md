# Otthonklíma – használati útmutató

Ez a dokumentum az Otthonklíma webes alkalmazás napi használatát mutatja be a
menüpontok sorrendjében. Az alkalmazás ESP32/DS18B20 hőmérőket, Computherm
termosztátokat, Hisense/ConnectLife klímákat, külső hőmérsékleti forrásokat,
valamint kézzel rögzített üzemeltetési és energiaadatokat kezel.

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

### Nézetváltás

- **Eszközök:** az eszközök típus szerint csoportosítva jelennek meg
  (ESP32, Computherm, Hisense, kézi eszközök).
- **Zónák és helyiségek:** emelet, földszint és zónán kívüli terület szerint
  csoportosít; az eszköz nélküli helyiségeket is megmutatja.

### Eszközkártyák értelmezése

A kártyák az eszköz típusától függően mutathatják:

- az utolsó hőmérsékletet és mérési időpontot;
- az elérhetőséget és az utolsó poll eredményét;
- a klíma be-/kikapcsolt állapotát, üzemmódját és célértékét;
- a Computherm mért és beállított hőmérsékletét;
- a Bosch 7000i kézi állapotát és szervizadatait.

A **Bekapcsolva** klímaállapot kiemelten jelenik meg. Az elérhető jelzés nem
azonos a bekapcsolt állapottal: azt mutatja, hogy az eszköz lekérdezhető volt.

### Kézi lekérdezés

A **Kézi lekérdezés** egy teljes eszközkört indít és az eredményt elmenti a
MariaDB-be. A kör végén az oldal frissül. A kézi és a tízperces automatikus kör
nem futhat egymásra; közös zárolás védi őket. Ha már fut egy kör, a másik nem
indul el.

A kézi kör nem tolja el a periodikus poll eredeti tízperces ütemezését.

### Külső hőmérséklet

A zónán kívüli részen az aktuálisan kiválasztott, friss külső forrás értéke is
megjelenik. Ez lehet később kültéri ESP32, illetve időjárási szolgáltatás.

## 3. Mérési előzmények

Ezen az oldalon a hőmérsékleti idősorok vizsgálhatók.

1. Jelölj ki egy vagy több eszközt.
2. Válassz időtávot: **1, 2, 6, 12 vagy 24 óra**, illetve **7 vagy 30 nap**.
3. Szükség esetén adj meg kezdő időpontot. Ilyenkor a kiválasztott hosszúságú
   időablak ettől az időponttól indul; üresen hagyva az időtáv a jelenig tart.
4. Nyomd meg a **Megjelenítés** gombot.

A kijelölt eszközök közös időtengelyen, külön színű görbékkel jelennek meg. A
jelmagyarázat azonosítja a görbéket, alattuk pedig eszközönként látható:

- minimum;
- átlag;
- maximum;
- mérési pontok száma.

Ez a nézet használható például több ESP32 kalibrációjának, egy ESP32 és egy
Computherm dinamikájának, illetve klíma- és szellőztetési események hatásának
összehasonlítására.

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
- Az automatikus lekérdezés és az automatikus vezérlés külön engedélyezhető.
- A lekérdezési gyakoriság eszközönként 1–1440 perc között állítható. A közös
  gomb minden aktívan, hálózaton lekérdezett eszközt visszaállít 10 percre.

Az áthelyezés időbélyeges helytörténetet hoz létre. Korábbi mérésekkel
rendelkező eszközt törlés helyett archiválni kell, így a történeti adatok
megmaradnak.

Az UI-ban felvett eszköz csak akkor kérdezhető le ténylegesen, ha a program
támogatja a választott lekérdező illesztőt, és annak technikai konfigurációja
is rendelkezésre áll.

### Globális beállítások

A szerkesztők a főmenü **Globális beállítások** oldalán módosíthatják a
rendszerszintű működési értékeket: az alap lekérdezési időt, az időkorlátot,
az adatmentés paramétereit, a gnuplot elérési útját, valamint az
előkészített hűtési és fűtési biztonsági határokat. A mentés közvetlenül, de
atomikusan frissíti a projekt `.env` fájlját.

Az adatbázis és a ConnectLife felhasználónevei, jelszavai, illetve más titkok
nem jelennek meg és nem szerkeszthetők ezen a felületen.

## 7. Elemzések

Az oldal a determinisztikus elemzési réteg állapotát mutatja:

- a szöveges AI, az Ollama és a modell kikapcsolt állapota;
- elemzési futások;
- felismert anomáliák;
- napi összefoglalók.

A számításokat determinisztikus Python-folyamat végzi. A korábban kipróbált
Llama 3.2 1B nem adott elég megbízható, validálható válaszokat, ezért töröltük.
Az Ollama az UI-ból nem kapcsolható be, de a Python-alapú ténycsomag továbbra is
elkészíthető. Egy későbbi nyelvi modell **soha nem vezérelhet eszközt**.

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

Ez az oldal tényleges eszközvezérlést, automatikus időzítést, eseménynaplót és
auditot is tartalmaz.

### 12.1 Közvetlen klímavezérlés

1. Válaszd ki a helyiséget.
2. Ellenőrizd a legutóbb lekérdezett állapotot és annak időpontját.
3. Kikapcsolt eszköznél add meg a célhőmérsékletet és válaszd a
   **Klíma bekapcsolása** gombot.
4. Bekapcsolt eszköznél a **Klíma kikapcsolása** gomb jelenik meg.

A rendszer bekapcsolást csak kikapcsolt, kikapcsolást csak bekapcsolt eszköznél
küld. A parancs előtt és után ConnectLife-lekérdezés történik. Az igazolt
eredmény rögtön bekerül az állapot- és klímaesemény-naplóba, ezért nem kell
megvárni a következő tízperces pollt.

Bekapcsoláskor csak a bekapcsolási állapot és a célhőmérséklet változik. Az
üzemmódot, ventilátorsebességet és kiegészítő programokat ez a funkció nem
módosítja.

### 12.2 Időzített klímafutás

Az időzítő kontrollált, automatikusan lezáruló futást készít.

1. Válaszd ki a helyiséget.
2. Add meg a kezdési dátumot és időt. Az aktuális idő megadásával az indítás
   gyakorlatilag azonnali.
3. Add meg a futásidőt percben.
4. Add meg a célhőmérsékletet (jelenleg 25–30 °C).
5. Nyomd meg a **Futás időzítése** gombot.

Az időzítés adatbázisban marad, ezért az oldal bezárható. A poller körülbelül
10 másodpercenként ellenőrzi az esedékes műveleteket. Az indítás és leállítás
is visszaolvasással ellenőrzött és auditált.

Állapotok:

- **ütemezve:** még nem indult el, törölhető;
- **indítás / leállítás:** a parancs végrehajtása folyamatban;
- **fut:** a klíma bekapcsolt, az automatikus leállítás várható;
- **befejezve:** az automatikus leállítás igazolt;
- **törölve:** a még el nem indult időzítést kézzel törölték;
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
2. A Klíma menüben készíts időzített futást kezdéssel, célértékkel és
   futásidővel.
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

- Az UI-ban látható időpontok helyi idő szerint jelennek meg; az adatbázis UTC
  időt tárol.
- A nyers DS18B20-adat gyors légáramra erősebben reagálhat, mint a burkolt
  Computherm. A nyers értékeket megőrizzük; a vezérlési szűrés külön feladat.
- A Hisense beltéri hőmérséklet információs adat, nem elsődleges helyiségi
  vezérlési mérés, mert a beltéri egység magasan és saját légáramában van.
- A Kért beállítások és Időprofilok jelenleg nem vezérlik a fizikai eszközt.
- A Klíma közvetlen és időzített vezérlése viszont valódi eszközparancsot küld.
- Az Ollama nem kaphat eszközvezérlési jogosultságot.
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
