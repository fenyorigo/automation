# Fűtési és hűtési döntési logika

## A dokumentum célja

Ez a dokumentum a későbbi automatikus vezérlés döntési szabályait rögzíti.
Jelenleg terv és követelményrendszer: az itt leírt logika még nincs teljes
egészében implementálva.

A vezérlés minden esetben determinisztikus. Nyelvi modell elemezhet és embernek
szóló észrevételt készíthet, de eszközt nem vezérelhet és döntési értéket nem
módosíthat.

## Fogalmak és döntési szintek

### Nyers mérés

Az eszköztől változtatás nélkül eltárolt érték. Auditálásra és későbbi
újraszámításra mindig megmarad.

### Elfogadott mérés

A nyers mérésből adatminőségi ellenőrzés, szenzorkorrekció és szükség esetén
időbeli szűrés után előálló érték. A vezérlési logika ezt használhatja.

### Helyiségi hőigény

Annak megállapítása, hogy egy helyiség elfogadott mérése tartósan a rá érvényes
célérték alatt vagy felett van-e. A helyiségi hőigény önmagában még nem jelent
eszközparancsot.

### Zónaigény

Az azonos zónába tartozó helyiségek hőigényéből és a zóna referenciahelyiségének
adataiból képzett fűtési vagy hűtési igény. Másik zóna mérése nem szólhat bele.

### Beavatkozási döntés

A zónaigény, a biztonsági korlátok, a külső hőmérséklet és az eszközök aktuális
állapota alapján meghozott, naplózott döntés. Parancs csak az állapot ismételt
ellenőrzése után küldhető, majd az eredményt vissza kell olvasni.

## Zónák és referenciahelyiségek

- **Emeleti zóna:** a Computherm termosztát jelenleg a dolgozóban van. A
  dolgozói Computherm és a mellette elhelyezett ESP együtt alkotja a zóna
  referenciahelyét.
- **Földszinti zóna:** a Computherm termosztát jelenleg a vendégszobában van. A
  mellette elhelyezett ESP-vel együtt alkotja majd a referenciahelyet.
- **Zónán kívüli:** elsősorban kültéri mérés; nem önálló fűtési zóna.

A Computherm eszközök hordozhatók. Áthelyezéskor a helyiség-hozzárendelést és
érvényességének kezdetét naplózni kell; a referenciahely is ennek megfelelően
változik.

## Szenzorok elfogadása és egymáshoz igazítása

Az ESP32 + DS18B20 érzékelők esetében az abszolút laboratóriumi pontosság nem
követelmény. A cél a szenzorok zónán belüli, egymással konzisztens viselkedése.

1. Az új ESP-ket közös körülmények között kell összehasonlítani.
2. Az állandónak bizonyuló relatív eltérés eszközönkénti korrekcióként
   rögzíthető.
3. A nyers érték változatlanul megmarad; a korrekció csak az elfogadott értékre
   vonatkozik.
4. Klíma, huzat, kézi megfogás vagy áthelyezés által okozott átmeneti eltérést
   nem szabad állandó szenzorhibaként korrigálni.
5. A korrekció verzióját és érvényességének kezdetét naplózni kell.

Az egy helyiségben lévő Computherm és ESP lehetőleg azonos magasságban és
hasonló légáramlási körülmények között mérjen. A Computherm burkolata és belső
szűrése miatt lassabban reagálhat, mint a szabad DS18B20; ez önmagában nem hiba.

## Adatminőségi feltételek

Egy mérés csak akkor lehet döntési bemenet, ha legalább az alábbi feltételeket
teljesíti:

- az eszköz és a szenzor aktív és döntési forrásként engedélyezett;
- a mérés sikeres, érvényes és nem régebbi a megengedett kornál;
- nincs szenzorhiba vagy irreális érték;
- az eszköz ismert helyiséghez, azon keresztül pedig zónához tartozik;
- nincs folyamatban kalibráció, áthelyezés vagy kizárást igénylő esemény.

Hiányzó vagy hibás adatot nem szabad nullával, utolsó ismert értékkel vagy másik
zóna mérésével észrevétlenül helyettesíteni. A bizonytalanságot külön állapotként
kell kezelni és naplózni.

## Időbeli szűrés és tranziens események

A DS18B20 gyors reakciója miatt egyetlen mérésből nem szabad kapcsolási döntést
hozni. A végleges szűrési paramétereket a kalibrációs és eseménymérések alapján
kell meghatározni.

Figyelembe veendő események:

- klíma indítása, leállítása, üzemmódja, célértéke és ventilátorfokozata;
- szellőztetés kezdete és vége;
- kültéri hőmérséklet és annak forrása;
- szenzor áthelyezése vagy megérintése;
- lekérdezési kimaradás és újracsatlakozás.

A klíma légárama által okozott gyors lehűlés vagy felmelegedés nem egyszerű
futóátlaggal javítandó szenzorhiba. Ismert klímaesemény esetén külön tranziens
állapotot kell alkalmazni. A nyers adat ilyenkor is megmarad és megjeleníthető.

## Kapcsolási holtsáv és időbeli megerősítés

A célérték közvetlen közelében sem fűtési, sem hűtési parancs nem indítható
egyetlen mérés alapján. Szükséges:

- be- és kikapcsolási hiszterézis;
- több egymást követő elfogadott mérés;
- vagy konfigurálható minimális fennállási idő;
- minimális be- és kikapcsolva tartási idő a sűrű kapcsolgatás ellen.

A Computherm ismert kapcsolási érzékenysége jelenleg `0,2 °C`, de a pontos
bekapcsolási és kikapcsolási viselkedést mérésből kell igazolni. Nem szabad
automatikusan feltételezni, hogy a beállított célérték körül szimmetrikusan
`−0,2/+0,2 °C` szerint működik.

## Fűtési döntés

Az 1.4.0 verzió az emeleti fűtés megfigyelő modelljét vezeti be. Kiszámolja a
helyiségi igényeket és a zónaszintű hőforrás-javaslatot, de sem a Hisense
klímákat, sem a Computhermet nem vezérli.

Minden klimatizált emeleti helyiségben az aktív Zigbee hőmérő a mérvadó. A
Hisense saját mérése `0,20`, a dolgozóban lévő Computherm mérése `0,10` súllyal
korrigálhatja a helyiségi cselekedeti hőmérsékletet. Az alapértelmezett fűtési
igény `20,0 °C` alatt indulna, aktív fűtésnél pedig `20,5 °C`-ig maradna fenn.
Az értékek, súlyok és a mérési adatok legnagyobb kora a Globális beállításokban
módosítható.

A hőforrás-választás zónaszintű és kölcsönösen kizáró:

1. ha nincs végrehajtható emeleti hőigény, egyik hőforrás sem indulna;
2. ha minden végrehajtható hőigényű helyiség Hisense klímája használható, és a
   kültéri hőmérséklet eléri az ideiglenes alsó határt, a klímás fűtés az
   elsődleges;
3. ha legalább egy ilyen helyiség klímája nem használható, vagy a kültéri
   hőmérséklet a határ alá esik, a teljes emeletre a gázfűtés kerül előtérbe;
4. klíma és gáz egyidejű használatát az observer nem javasolja. Helyiségenként
   szabályozható kevert üzem csak későbbi Zigbee radiátorszelepekkel lehetséges.

A klímás fűtés alsó kültéri határa kezdetben, mérési tapasztalat hiányában
`5,0 °C`. Ez módosítható, ideiglenes helyettesítője a Hisense külső
hőmérséklettől függő COP-görbéjének. A tárolt elvárt minimum `COP 2,5`; a SCOP
nem pillanatnyi vezérlési érték. A későbbi tarifaalapú döntés a tényleges
COP-görbével váltja majd fel az egyszerű kültéri küszöböt.

Nyitott vagy ismeretlen állapotú nyílászáró, explicit offline kontaktus és a
zárás utáni stabilizációs idő az adott helyiséget blokkolja; ezek önmagukban nem
okoznak gázra váltást. A régi, de elérhető Tuya állapotjelzés továbbra sem hiba.

A Computherm kártyája megmutatja a Bosch kézi nyilvántartás szerinti állapotát.
Ha a termosztát `active` állapota fűtést kér, de a Bosch ki van kapcsolva, külön
helyszíni bekapcsolási figyelmeztetés jelenik meg. A `power` mező csak a
termosztát bekapcsolt állapotát jelenti, nem a relé fűtési kérését. `22 °C`
feletti Computherm- vagy Hisense-célértéket az observer eltérésként jelez; az
1.4.0 még nem írja vissza.

## Szervizmódok és Computherm-próba

A `Klímaszerviz folyamatban` globális kapcsoló felfüggeszti a hűtési és
klímafűtési observer szabályait, valamint az időzített klímavezérlés
végrehajtását. A szervizoldalról indított kézi hűtési és fűtési próbákra nem
vonatkozik beltéri vagy kültéri hőmérsékleti határ, termosztátigény- vagy
nyílászáró-kapuzás. A `Gázkazánszerviz folyamatban` kapcsoló csak
a fűtési döntéseket függeszti fel, és engedélyezi a Computherm szerviztesztet.
A kezdőlap aktív szervizmód esetén piros figyelmeztetést mutat.

A klímaszerviz-parancs explicit módot (`cool` vagy `heat`), célhőmérsékletet és
ventilátorfokozatot küld. A készülék hardveres `16–30 °C` tartománya megmarad.
A siker feltétele, hogy a visszaolvasott bekapcsolt állapot, üzemmód,
célhőmérséklet és ventilátorfokozat mind megfeleljen a kérésnek. A kért mód az
auditnapló része.

A Computherm-próba csak szerkesztőnek, bekapcsolt gázkazánszerviz mellett és a
nyilvántartás szerint bekapcsolt Bosch kazánnal használható. Egyszerre csak egy
termosztát tesztelhető. Indítás előtt teljes állapotmentés készül. A teszt a
termosztát kikapcsolása nélkül kézi módra vált, szükség esetén ideiglenesen
megemeli a `22 °C` felső korlátot, majd beállítja a kért célértéket. A fűtési
kérés megszüntetése a mért érték alatti kézi céllal engedi el a relét; nem
kapcsolja ki a Computhermet. A teszt lezárása visszaállítja az eredeti módot,
célértéket és haladó korlátokat. A napi program tartalma egyik lépésben sem
íródik felül. Minden parancs és visszaolvasott állapot auditnaplóba kerül.

### Helyiségi igény

Egy helyiség fűtési igényt jelezhet, ha az elfogadott hőmérséklete a beállított
célérték és a fűtési holtsáv alá kerül, és ez az állapot kellő ideig fennáll.

### Referenciahelyiség

Ha a Computherm és a vele egy helyiségben lévő ESP eltérően ítéli meg a
kapcsolási helyzetet:

1. a különbséget és annak időtartamát naplózni kell;
2. a két eszköz eltérő dinamikáját figyelembe kell venni;
3. tartós, kalibráción és holtsávon túli eltérésnél nem szabad automatikusan
   valamelyiknek igazat adni;
4. a rendszer szenzor-, elhelyezési vagy referenciahely-problémát jelezzen.

### Zónaigény

Előfordulhat, hogy egy távolabbi helyiség ESP-je már fűtési igényt jelez,
miközben a referenciahelyiség Computhermje még nem. Ez lehet valós zónán belüli
hőmérséklet-különbség, nem feltétlen mérési hiba. A zóna döntési szabályának
később konfigurálhatóan kell meghatároznia:

- hány helyiségi igény szükséges;
- mely helyiségek vagy referenciaeszközök kapnak nagyobb súlyt;
- mennyi ideig kell fennállnia az eltérésnek;
- milyen feltételekkel kérhető a kazán vagy más fűtőeszköz indítása.

A fűtés felső globális szobahőmérsékleti és célértékhatára jelenleg `22 °C`.
Computherm esetén a korlátot a Computherm aktuális helyiségének elfogadott
szenzoraira kell alkalmazni, nem a teljes ház bármely érzékelőjére.

## Hűtési döntés

Az 1.3.0 verzió az emeleti hűtés első, kizárólag megfigyelő változata. Kiszámolja
és megjeleníti, mit tenne, de sem Hisense-, sem Computherm-parancsot nem küld.
A hűtés és a fűtés külön döntési kör; a földszint ebben a hűtési körben nem vesz
részt.

Az adott helyiség aktív Zigbee hőmérője a mérvadó. A Hisense saját érzékelője
magasabban van, a Computherm pedig csak a dolgozóban áll rendelkezésre, ezért
ezek kisebb súllyal módosíthatják a mérvadó értéket. Az alapértelmezett
cselekedeti hőmérséklet:

`Zigbee + 0,20 × (Hisense − Zigbee) + 0,10 × (Computherm − Zigbee)`

Ha valamelyik másodlagos mérés hiányzik vagy túl régi, annak korrekciós tagja
kimarad; a Zigbee súlya ennek megfelelően nő. A Zigbee mérés kötelező. Az ESP32
eredeti nyers/elfogadott/cselekedeti modellje változatlanul megmarad, az emeleti
observer pedig ugyanezt a fogalmi különválasztást helyiségi, többforrású
számítással alkalmazza.

Alapértelmezett, a Globális beállításokban módosítható hűtési paraméterek:

- hűtési igény bekapcsolási határa: `27,5 °C`;
- hűtési igény kikapcsolási határa: `27,0 °C`;
- kültéri indítási engedély: `28,1 °C`;
- kültéri leállítási határ: `27,1 °C`;
- legkisebb megengedett hűtési célérték: `25 °C`;
- döntési adat maximális kora: `180 perc`;
- az utolsó nyílászáró bezárása utáni stabilizálás: `10 perc`;
- Hisense súlya: `0,20`, Computherm súlya: `0,10`.

A két szobahőmérsékleti és a két kültéri határ hiszterézist alkot: kikapcsolt
klímánál a magasabb indítási, működő hűtésnél az alacsonyabb fenntartási határ
érvényes. A termikus „Hűtést kér” állapot külön fogalom attól, hogy a kérés
végrehajtható-e. Nyitott, ismeretlen állapotú vagy a Zigbee mesh-ről leesett
nyílászáró-érzékelő blokkol; bezárás után a stabilizációs idő végéig szintén
blokkolt maradna az indítás. Régi, de elérhető Tuya állapotjelzés önmagában nem
hiba.

Az observer lehetséges eredményei: `Elindítaná`, `Folytatná`, `Leállítaná`,
`Nem indítaná`, `Hűtést kér, de blokkolva`, illetve `Nincs elég friss adat`.
A `25 °C` alatti kézi Hisense-célértéket külön korrekciós igényként jelzi, de
ebben a verzióban azt sem írja vissza.

## Kültéri hőmérséklet és fűtési mód választása

Klímás fűtésnél konfigurálható alsó kültéri hőmérsékleti határ szükséges. A
határ alatt a klímát nem kell erőltetni; ilyenkor a fűtési igényt a kazános
rendszer felé kell továbbítani. A határértéket mérések és üzemeltetési
tapasztalat alapján kell meghatározni, nem rögzített `5–10 °C` feltételezésként.

## Döntési konfliktusok

Konfliktusnak számít például:

- egy helyiség elfogadott szenzorai a holtsávon túl eltérnek;
- a referenciahelyiség ESP-je tartósan fűtést kér, a Computherm pedig nem;
- a zóna több helyisége fűtést kér, de a referenciahely nem;
- egy klíma bekapcsoltnak látszik, miközben a vezérlési napló szerint leállt;
- a külső hőmérsékletforrások érdemben eltérnek vagy elavultak.

Konfliktus esetén a rendszer biztonságos állapotot választ, naplózza az okot,
és felhasználói figyelmeztetést ad. A későbbi elemzőréteg felismerheti a tartós
mintázatot és javasolhat ellenőrzést, de nem oldhatja fel önállóan a konfliktust.

## Naplózási követelmények

Minden döntési ciklusnál utólag megállapítható legyen:

- mely nyers és elfogadott mérések szerepeltek a döntésben;
- milyen korrekció és szűrés volt érvényes;
- mely célérték, profil, holtsáv és biztonsági korlát vonatkozott rá;
- milyen események – klíma, szellőztetés, kültéri adat – voltak aktívak;
- mi lett a helyiségi és zónaigény;
- született-e parancs, és ha nem, mi blokkolta;
- a végrehajtott parancs visszaolvasása sikeres volt-e.

## Még eldöntendő és mérendő paraméterek

- ESP-időszűrés típusa és időállandója;
- szenzoronkénti végleges relatív korrekció;
- helyiségi hiszterézis és minimális fennállási idő;
- zónán belüli helyiségprioritások vagy szavazási szabály;
- referenciahelyiség és távolabbi helyiségek konfliktusának feloldása;
- minimális be- és kikapcsolva tartási idő;
- klímaindítás utáni tranziens időablak és ventilátorfokozat hatása;
- kültéri hőmérséklethez kötött hűtési célértékek;
- klímás fűtés alsó kültéri határa és kazánra váltási szabálya.

E paramétereket mérési eredmény alapján, verziózott konfigurációként kell
bevezetni. Módosításuk nem írhatja át a korábbi döntések értelmezését.
