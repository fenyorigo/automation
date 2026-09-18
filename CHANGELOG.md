# Változásnapló

A projekt a szemantikus verziózás elvét követi. A kiadás dátumai budapesti
helyi dátumok.

## Kiadatlan

- A Mérési előzmények eszközválasztója külön **Aktív eszközök** és
  **Inaktivált eszközök** csoportot mutat. Az inaktivált hőmérők megőrzött
  idősorai grafikonon és CSV-exportban is kiválaszthatók; a lista azt is jelzi,
  hogy az adott inaktivált eszközhöz maradt-e mérés.
- A Mérési előzmények időablaka időtávval vagy explicit kezdő és végidőponttal
  is megadható; ugyanaz a beállítás érvényes a grafikonra és a CSV-exportra.

- A Globális beállítások mentése fájlrendszerhiba esetén nem ad többé nyers
  HTTP 500 választ, hanem kezelhető hibaüzenetet jelenít meg. A Fedora
  telepítésben a tényleges `.env` az `automation` tulajdonú `config`
  könyvtárban él, így atomikusan írható a projektgyökér írási joga nélkül.
- A kezdőlap a háttérben 30 másodpercenként ellenőrzi, érkezett-e új polladat;
  a mérési és vezérlési ciklusok változatlanok.
- Megszűnt a kezdőlap 5 másodpercenkénti téves újratöltési ciklusa: a dashboard
  és a poll-státusz most ugyanazt, az aktív eszközök legutóbbi pollindítási
  időpontját használja frissítési jelzőként. Ez megszünteti a MariaDB-t
  túlterhelő párhuzamos kezdőlapi lekérdezéseket.
- A legutóbbi szenzor-, eszközállapot- és pollrekordok rendezett visszaolvasása
  célzott összetett indexeket kapott, így a dashboard nem rendez végig több
  százezer idősoros rekordot minden oldalbetöltésnél.
- A Globális beállítások oldalon a klíma- és gázkazánszerviz kapcsoló felirata
  piros figyelmeztető színt kapott.
- A Computherm szervizteszt az emeleti és a földszinti termosztáton egymástól
  függetlenül, akár egyidejűleg is futtatható. Mindkét próba saját eredeti
  állapotot őriz, külön engedhető el, és külön állítható vissza.
- Az `SP ebédlő` az UI-ról be- és kikapcsolható; kikapcsolása külön piros
  megerősítést kér, kikapcsolt állapotban a kártya piros. Bekapcsolás után az
  alkalmazás jelzi, hogy a Klarsteint kézzel kell Standby-ból fűtésre
  kapcsolni. Más Zigbee-routerek továbbra sem kapcsolhatók.
- A negyedik S60ZBTPF `SP közlekedő` néven a földszinti Közlekedőhöz és
  helytörténethez került; kizárólag megfigyelési és Zigbee-router szerepű.
- A Zigbee2MQTT collector a SONOFF S60ZBTPF dugaljak pillanatnyi
  teljesítményét, áramát, feszültségét és összesített energiáját is a közös
  `sensor_readings` idősorba menti. A reléállapot továbbra is állapotadat,
  nem periodikus mérés.
- A harmadik S60ZBTPF `SP ebédlő` néven, a földszinti Ebédlő-konyha
  helyiséghez és helytörténethez rendelve került nyilvántartásba; feladata a
  Klarstein konvektor fogyasztásának megfigyelése és a Zigbee mesh erősítése.
- A `Klarstein Norderney` külön, helyi API nélküli `Villanyfűtő`ként került a
  nyilvántartásba és a hűtés–fűtés alapnézetbe. Kártyája nem mutat hibás
  offline állapotot; jelzi, hogy működését az `SP ebédlő` méri.
- A `thinkpad220x` helyére került `t470` ugyanazon a nyilvántartási eszköz- és
  szenzorrekordokon folytatja a rendszerterhelési méréseket. A helyiség, a
  `192.168.10.2` cím, a korlátozott SSH-hozzáférés, a pollritmus és minden
  korábbi mérés megmaradt.
- A SONOFF TRV Gen2 (`TRV-ZBT`) külön radiátortermosztát-eszköztípusként
  automatikusan felismerhető. A collector a radiátorközeli hőmérsékletet, a
  célhőmérsékletet, a szelepnyitást, az órás fűtési aktivitást és az
  elemállapotot a közös idősorba menti; a teljes eszközállapot továbbra is a
  Zigbee-cache-ben marad.
- A TRV-kártya megmutatja a mérést, célértéket, szelepállást, üzemmódot,
  kalibrációt, hibajelzést, elemet és LQI-t. A kártya egyértelműen jelzi, hogy
  a radiátorközeli mérés aktív gázfűtés alatt nem vezérlési alap; ebben a
  fázisban az alkalmazás nem küld parancsot a szelepnek.
- A két első TRV (`TRV-G2 nappali bal`, `TRV-G2 Kristófék`) helyiséghez és
  helytörténethez rendelve, aktív idősoros adatgyűjtéssel üzemel.
- Új, verziózott folytatási átadó dokumentum rögzíti az éles Fedora, a Mac
  fejlesztési repository és a távoli Git eltérő szerepét, a dokumentációs
  belépési pontokat, a biztonsági invariánsokat és a következő munkák sorrendjét.
- Az eszközleltár az éles adatbázis 2026-09-14-i név- és
  helyiség-hozzárendeléseire frissült; a későbbre eldöntött Bosch-, TRV-,
  automatikavezérlési, energia- és Zigbee-feladatok bekerültek a teendőlistába.
- A kezdőlap új, alapértelmezett **Hűtés–fűtés vezérlés** szűrője egyetlen
  nézetben mutatja a döntési lánc klímáit, termosztátjait, kazánját, mérvadó
  Zigbee hőmérőit és nyitásérzékelőit, valamint a kültéri referenciaforrást.
- A földszinti Computherm is kapott külön fűtési javaslatot; ez a kizárólagos
  gázfűtési zónában a termosztát reléigényét és a Bosch állapotát mutatja.
- A kazánházba telepített `nous-kazan` Tasmota dugalj bekerült a
  nyilvántartásba és a hűtés–fűtés vezérlés alapnézetébe; a rövid próba
  elkülönítette a Bosch 0 W-os kikapcsolt és 5 W-os bekapcsolt nyugalmi
  állapotát.
- Kizárólag a `Nous kazán` kapcsolható a kezdőlapról; az IT- és Zigbee
  router-dugaljak megfigyelhetők maradnak. A kikapcsolás piros, eszközhöz
  kötött második megerősítést kér, minden kísérlet auditált és a visszaigazolás
  hiánya nem jelenik meg sikerként.
- A `Nous kazán` igazolt lekapcsolása a Bosch kézi állapotát is kikapcsoltra
  állítja és naplózza. A Bosch kártyája külön jelzi a Nous vagy kézi forrású
  tápellátást, a melegvíz-szolgáltatást és a fűtést; a három kézi érték egy-egy
  jelölőnégyzettel rögzíthető. Táp nélkül a két kazánüzem nem lehet aktív.
- Bekapcsolt Nous mellett a Bosch power kapcsolóját a friss teljesítmény igazolja:
  a kb. 5 W-os nyugalmi fogyasztás aktív panelt jelent, a friss 0 W piros
  figyelmeztetést ad. A relékapcsolás előtti régi mérés nem okoz téves riasztást.
- A hűtés–fűtés alapnézet a Computhermek helyiségeinek mérvadó Zigbee
  hőmérőit is mutatja, így a földszinti Computherm mellett a vendégszobai
  hőmérő is információforrásként látható.
- Javítva a Nous kazán kapcsolása után futó Bosch-állapotszinkron adatbázis-
  lekérdezése; a hibás lekérdezés a már végrehajtott reléparancs után 500-as
  választ adott.
- A `nous-kazan` feszültségmérését 235,5 V referenciaértékkel kalibráltuk;
  a `VoltageCal` 1950-ről 1498-ra változott, a kijelzés 306 V-ról 235 V-ra
  állt be.
- A Nous kazán aktuális reléállapotával azonos kapcsológomb egyértelműen
  szürke és inaktív; a szerveroldali visszaolvasás az ismételt parancsot is
  hatás nélkül hagyja.
- Javítva a reléállapot adatbázisból érkező `0/1` értékének boolean
  normalizálása, hogy a megfelelő kapcsológomb ténylegesen megkapja a böngésző
  `disabled` állapotát.
- Javítva a Bosch kézi melegvíz- és fűtésállapotának mentési lekérdezése; a
  hibás SQL miatt a mentés 500-as hibaoldallal végződött.

## 1.3.1 — 2026-09-08

### Klímaszerviz

- A Szervizteszt oldalon a Hisense klímák hűtésben vagy fűtésben, szabadon
  választott eszköz-célhőmérséklettel és ventilátorfokozattal próbálhatók.
- Klímaszerviz módban a parancsokat nem korlátozza a helyiségi vagy kültéri
  hőmérséklet, a termosztátigény, illetve a nyílászáró állapota.
- Az automatikus és időzített klímaparancsok a szerviz teljes ideje alatt
  szünetelnek, így nem írhatják felül a szerelő kézi próbáját.
- A kért hűtési vagy fűtési üzemmód bekerül a vezérlési auditnaplóba, és a
  ConnectLife-parancs utáni visszaolvasás ezt is ellenőrzi.

### Computherm-szerviz

- Külön globális klíma- és gázkazánszerviz-kapcsoló készült; aktív állapotuk
  jól láthatóan felfüggeszti az érintett observer szabályokat.
- Új, szerkesztői Computherm szervizteszt teszi lehetővé az emeleti és
  földszinti fűtési kérés külön próbáját, kizárólag bekapcsolt Bosch mellett.
- A teszt soha nem kapcsolja ki a Computhermet és nem írja át a napi programot.
  A teljes eredeti állapotot elmenti, a tesztcélhoz szükség esetén ideiglenesen
  megemeli a felső korlátot, majd egy művelettel mindent visszaállít.
- A tesztek és parancsaik előtte/utána állapottal, felhasználóval és
  időbélyeggel auditálhatók; egyszerre csak egy termosztátteszt futhat.

### Emeleti fűtési megfigyelés

- Az emeleti helyiségek Zigbee-alapú, Hisense- és Computherm-méréssel
  mérsékelten korrigált fűtési igényt kapnak.
- A zóna vagy kizárólag klímás, vagy kizárólag gázfűtési javaslatot ad; kevert
  üzemet Zigbee radiátorszelepek hiányában nem enged.
- Az ideiglenes klímás kültéri alsó határ, a `COP 2,5` elvárás, a helyiségi
  hiszterézis, a forrássúlyok, az adatkor és az ablakzárás utáni várakozás a
  Globális beállításokban módosítható.
- A Computherm kártyák megmutatják a Bosch kazán kézi állapotát, és külön
  figyelmeztetnek, ha a termosztát fűtést kér, miközben a kazán ki van kapcsolva.
- A helyiségi `Fűtést kér` jelzés, a klímaalkalmasság, a blokkoló nyílászárók és
  az egész emelet hőforrás-javaslata megjelenik a kezdőlapon.

### Fűtési biztonság

- Az observer sem klíma-, sem Computherm-parancsot nem küld. Nyitott vagy
  ismeretlen nyílászáró nem kényszerít gázra váltást, hanem az érintett
  helyiséget blokkolja.

## 1.3.0 — 2026-09-08

Az emeleti Hisense klímákhoz elkészült a hűtési döntés első, kizárólag
megfigyelő változata.

### Új funkciók

- A helyiség Zigbee hőmérője alapján, a Hisense és – ahol van – a Computherm
  mérésével mérsékelten korrigálva számítjuk a cselekedeti hőmérsékletet.
- A hűtési igény, a beltéri és kültéri hiszterézis, az adatfrissesség és az
  ablakzárás utáni stabilizáció határai a Globális beállításokban módosíthatók.
- A mérvadó hőmérő kártyáján piros `Hűtést kér` jelzés, részletes indítási,
  folytatási, leállítási vagy blokkolási javaslat és a felhasznált forrássúlyok
  jelennek meg.
- Nyitott, ismeretlen vagy valóban elérhetetlen nyílászáró-érzékelő blokkolja a
  javasolt indítást; a Tuya érzékelő pusztán régi állapotjelzése nem.
- A nyers/cselekedeti nézet megmaradt, és most az emeleti, többforrású
  cselekedeti hőmérsékletet is meg tudja jeleníteni.

### Biztonság

- Az observer sem a Hisense klímának, sem a Computherm termosztátnak nem küld
  parancsot; az 1.3.0 csak azt mutatja meg, mit tenne a későbbi automatika.

## 1.2.0 — 2026-09-08

Zigbee- és Shelly-szenzorintegráció, nyílászáró-alapú szellőztetési napló,
valamint részletes gáz- és villanyszámla-kezelés.

### Adatimport

- A PDF-ekkel ellenőrzött történeti villanyszámlákhoz idempotens, tranzakciós
  importáló és utólagos adatbázis-ellenőrzés készült.

### Újdonságok

- A közös energiaszámla-modell már gáz mellett villany fogyasztási részleteket
  is kezel, kWh-alapú szolgáltatói mérőállással.
- Új villanyos díjkategóriák készültek az összevont rendszerhasználati,
  átviteli, elosztói és elszámolási jóváírási tételekhez.
- A villany kedvezményes, piaci és rendszerhasználati tarifái időben hatályos
  törzsadatként bekerülnek; az A1 és a használaton kívüli vezérelt mérő
  alapdíja automatikus számlatételként használható.
- A számlafej megőrzi a szolgáltatói számlázási rendszert, a
  felhasználóazonosítót és a szerződéses folyószámlát.
- Elkészült a villanyszámlák felviteli és ellenőrzési leírása, benne az
  augusztus 1-jei bontással, az elszámolószámlákkal és az ismert duplumokkal.

### Javítások

- A Zigbee2MQTT systemd drop-inja 3 percre emeli a leállási határt, mert a
  TCP-s Z-Stack koordinátor mentése a jelenlegi hálózaton mérve közel 97
  másodperc. Ezzel a korábbi 90 másodperces timeout nem szakítja félbe a
  zigbee-herdsman szabályos leállását; végső időtúllépéskor coredump sem készül.
- Dokumentáltuk a Zigbee2MQTT ismert `write after end` leállási hibáját: a TCP
  socket késői `Port closed` naplózása a már lezárt Winston transportot éri.
  A hibás kilépési kódot szándékosan nem fedjük el systemd-beállítással.
- A nyitásérzékelők régi `last_seen` időpontja többé nem jelent piros
  elérhetetlenséget: sárga, fekete betűs „Régi állapotjelzés” látszik. Piros
  hibát csak a Zigbee2MQTT explicit `availability=offline` állapota okoz.
- A Zigbee2MQTT availability-figyelése aktív: a hálózati eszközök 10 perc, az
  elemes végberendezések 48 óra üzenetcsend után minősülnek offline-nak.
  A Tuya érzékelők 65000 másodperces reporting értéke az akkumulátor-
  attribútumokra vonatkozik, nem a nyitva/csukva állapot ismétlésére.
- Az óraállás ceruza ikonja ismét megnyitja a szerkesztőt: az Energia oldal a
  kiválasztott rekord valódi energiatípusát és évét automatikusan láthatóvá
  teszi, és mentés után is ennél a sornál marad.

### Új funkciók

- A közös poller új `network_device` illesztője DNS-, ICMP-ping- és HTTP-
  ellenőrzéssel felügyeli a helyi hálózati végpontokat. Elsőként a Xerox B235
  nyomtató került be 10 perces ciklussal és külön eszközkártyával.
- Új `docs/teendok.md` tartja nyilván a későbbre halasztott kontrollált Zigbee
  bridge-áramtalanítási próbát és a hozzá kapcsolódó megbízhatósági feladatokat.
- Új Zigbee célzott újracsatlakoztatási útmutató készült a SONOFF és Nous/Tuya
  végberendezésekhez, a térkép/LQI korlátaival és biztonságos hibaelhárítási
  sorrenddel.
- A Zigbee/Tuya nyitásérzékelők eszközkártyája hőmérséklet helyett a
  `Nyitva`/`Csukva` állapotot és a tamper jelzést mutatja.
- A helyiséghez rendelt Zigbee/Tuya nyitásérzékelők automatikusan vezetik a
  szellőztetési naplót. A késleltetett lezárás egy eseményben tartja a bukó és
  nyitott állás közti, pillanatnyi becsukással járó váltást; a rövid/hosszú
  határ és a zárási késleltetés globálisan állítható. A már futó kézi esemény
  megőrzi eredetét, de átadható az érzékelő alapú automatikus lezárásnak.
- A Zigbee `contact` állapot első ismert értéke és minden valódi változása
  forrásoldali időbélyeggel bekerül a közös `sensor_readings` táblába.
- A szellőztetési napló alapból csak az aktív eseményeket mutatja, és állapot,
  valamint helyiség szerint szűrhető.
- A kezdőlap aktuális külső referencia-kártyája már nem jelöl minden forrást
  szolgáltatói mérésnek: a lábléc külön saját Zigbee-mérést, webes időjárási
  adatot, helyi szenzort vagy kézi mérést jelez. Saját Zigbee/ESP32 forrásnál
  a külön összesítő rejtve marad, mert az eszközkártya már tartalmazza az
  értéket; webes tartalékforrásnál továbbra is megjelenik.

- Az Energia számlalistája energiatípus, nyitott/lezárt ciklus és év szerint
  szűrhető; alapból a nyitott gázciklus látszik. A korábbi óraállások külön
  energiatípus- és évszűrőt kaptak, és alapból rejtve maradnak.
- A gáz korrekciós/fűtőérték és tarifa törzsadat új értéke automatikusan
  lezárja a korábbi hatályt. A számlázási időszak alapján a fogyasztási
  részlet és az energiadíj egységára ezekből töltődik, miközben a két
  díjsáv MJ-mennyisége továbbra is kézi, számla szerinti adat.
- Hatályos automatikus számlatétel-törzs készült. Új gáz-részszámlán a
  Háztartási alapdíj és a két aktív OtthonSOS szolgáltatás automatikusan
  létrejön; a szolgáltatások áfamentessége elkülönül a 0%-os adókulcstól.

- A `Támogatás/túlfizetés` és az új `Késedelmi kamat` számlatétel egyszerű,
  előjeles bruttó összegként, nettó-, ÁFA- és mennyiségi adatok nélkül vihető
  fel.
- A ciklushoz rendelt részszámlák kumulált m³ értéke a ciklus elejétől,
  részszámlasorrendben automatikusan számolódik és javításkor újraszámolódik.
- A számlalista a részszámlák rögzített sorszámát is kijelzi, például
  `3. részszámla` formában.
- A történeti gázszámlák rögzítéséhez az `OtthonSOS Plusz` szolgáltatás is
  kiválasztható a számlatétel legördülőjében.
- Az elszámolószámlák külön energiadíj- és alapdíj-jóváírási kategóriát
  kaptak. Külön táblában és szerkeszthető felületen rögzíthető az elszámolásban
  felsorolt részszámlák száma és végösszege, automatikus számlaszám-alapú
  kapcsolással.
- Új `docs/gázszámla-felvitele.md` gyakorlati útmutató készült a
  részszámlákhoz, az augusztus 1-jei jogosultsági évváltással, számításokkal
  és ellenőrző összegekkel; az útmutató már az éves elszámolószámla
  jóváírásait és részszámlalistáját is tartalmazza.
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
  kategória áfamentes, minden más szokásos kategória 27% alapértéket kap.
- Javítva az Energia oldal üres URL-hivatkozásnál fellépő JavaScript-hibája,
  amely megakadályozta a számlatételek automatikus ÁFA- és összegszámítását.
- A számlatétel kategóriája automatikusan kitölti a szabványos megnevezést és
  mértékegységet; szolgáltatásnál legördülőből választhatók az OtthonSOS
  Komfort és Garancia Médium tételek.
- Új v1.37 számlafej-szintű kerekítési mező kezeli a pozitív vagy negatív
  `Kerekítés` sort. A kerekítés tájékoztató adat, mert a szolgáltatói bruttó
  számlaérték már tartalmazza; nem módosítja másodszor a fizetendő összeget.
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
