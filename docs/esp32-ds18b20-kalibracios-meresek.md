# ESP32–DS18B20 kalibrációs mérések

## 1. Cél

A méréssorozat célja az öt DS18B20 érzékelő egymáshoz igazítása, dinamikájuk
összehasonlítása a Computherm termosztáttal, valamint a közvetlen légmozgás
hatásának vizsgálata. Külön vizsgáljuk a gyári kivitelű, a szellőző műanyag
dobozba helyezett, a későbbi rézcsöves, illetve a doboz és rézcső együttes
kialakítást. A nyers adatok minden esetben változatlanul megmaradnak.

## 2. Helyszín és eszközök

A kalibrációs mérések helyszíne a dolgozószoba.

Referencia és adatszolgáltató eszközök:

- Computherm 400RF termosztát: `iot-computherm-emelet`;
- DS18B20: `esp32-ext`;
- DS18B20: `esp32-dolgozo`;
- DS18B20: `esp32-halo`;
- DS18B20: `esp32-kisnappali`;
- DS18B20: `esp32-kristofek`.

## 3. Térbeli elhelyezés

A szenzorok nem közvetlenül a klíma alatt vannak. A klímához képest körülbelül
1,5 méterrel jobbra, 80 centiméterrel mélyebben és 70 centiméterrel előrébb
helyezkednek el, gyakorlatilag a ferde tetősík alatti könyvespolc magasságában,
a távcső környezetében.

Az öt DS18B20 azonos magasságban, vízszintesen körülbelül 40 centiméteren belül
helyezkedik el. A szondák alja megközelítőleg a Computherm termosztát közepének
magasságában, a termosztát előtt található. A kis távolság csökkenti annak
esélyét, hogy a szoba geometriája vagy bútorozása szenzorkülönbségként jelenjen
meg, de a klíma légárama a mérőhelyet így is erősen befolyásolja.

A kalibrációs állványon a DS18B20 érzékelők sorrendje balról jobbra:

1. `esp32-ext`;
2. `esp32-kisnappali`;
3. `esp32-kristofek`;
4. `esp32-halo`;
5. `esp32-dolgozo`.

A sorrendet minden fizikai módosításnál meg kell őrizni vagy a változást külön
fel kell jegyezni, mert a klímától való néhány tíz centiméteres helyzetkülönbség
is befolyásolhatja a légáram okozta dinamikát. A Computherm termosztát a
szenzorsor mögött és attól kissé balra helyezkedik el.

## 4. Időkezelés és mintavétel

Az alábbi időpontok budapesti helyi időben, 2026 augusztusában CEST
(`UTC+02:00`) szerint szerepelnek. A MariaDB az időbélyegeket UTC-ben tárolja.

A `kisnappali` első adatbázisrekordja 2026. augusztus 13-án 14:46:55-kor volt,
majd 14:56:55-kor egy második pont keletkezett. Az öt DS18B20 közös,
összehasonlítható kalibrációs sorozata 16:34:11-kor indult. A kezdeti időszakban
a mintavétel 10 perces, később körülbelül 2 perc 10 másodperces lett. A
meredekségeket ezért csak azonos mintavételű szakaszokon szabad közvetlenül
összehasonlítani.

## 5. Mérési konfigurációk

### 5.1 Gyári kivitel

2026. augusztus 13. 16:34:11-től mind az öt DS18B20 az eredeti, fém
szondaházas kivitelben, további fizikai burkolat nélkül vett részt a mérésben.

### 5.2 Szellőző műanyag doboz

2026. augusztus 15-én 09:27-kor az `esp32-kisnappali` érzékelője szellőző
nyílásokkal ellátott műanyag dobozba került. A többi négy DS18B20 változatlan
maradt, ezért kontrollként használható.

A beavatkozás előtti utolsó `kisnappali`-érték 09:24:50-kor 24,4375 °C volt. Az
első beavatkozás utáni mérés 09:27:00-kor 25,2500 °C, a maximum 09:29:10-kor
25,5000 °C lett. Ez a felfelé mutató átmenet a kézi megfogás és áthelyezés
hatása, nem a helyiség tényleges felmelegedése.

Az érték 09:48:38-kor került először az `esp32-ext` értékétől egyetlen DS18B20
lépésen, 0,0625 °C-on belülre. 10:05:59-kor mindkét szenzor 25,0000 °C-ot
mért. Operatív értelemben a szenzor 09:48 és 10:06 között stabilizálódott. Ezt
követően nyugodt légállapotban a `kisnappali` és az `ext` jellemzően együtt,
legfeljebb egy-két kvantálási lépcső eltéréssel mozgott.

### 5.3 Második szellőző műanyag doboz

2026. augusztus 16-án, helyi idő szerint körülbelül 16:23–16:25 között egy
második, azonos célú, de eltérő geometriájú műanyag doboz került az
`esp32-dolgozo` érzékelőre. Ez a kalibrációs állvánnyal szemben állva a jobb
szélső szonda. Az `esp32-halo` változatlan, csupasz kontroll maradt.

A beavatkozás előtti utolsó `dolgozo`-érték 16:23:50-kor 26,6250 °C volt. Az
első egyértelműen beavatkozás utáni mérés 16:26:00-kor 27,8750 °C, a maximum
16:28:10-kor 28,0625 °C lett. Ez a felfelé mutató ugrás a szenzor megfogásának
és a doboz felhelyezésének hatása. 16:39:01-re az érték 27,0625 °C-ra csökkent,
majd a következő két mérésben ezen a szinten maradt. A görbe tehát ekkor már
stabilizálódni látszott, de 16:43:21-kor még 0,1875 °C-kal a csupasz
`esp32-halo` kontroll fölött állt. 16:47:41-kor a `dolgozo` 26,9375 °C-ot, a
`halo` szintén 26,9375 °C-ot mért. 16:52:01-től a `dolgozo` ismét jellemzően a
kalibrációs sor második legalacsonyabb értékét adta, közvetlenül a
`kristofek` fölött, vagyis visszaállt a dobozolás előtti relatív helyére.
Operatív stabilizálódási időpontként ezért 16:52 vehető fel; a felhelyezés
okozta hőmérsékleti tranziens lecsengése körülbelül 27–28 percig tartott.

A sikertelen klímateszt után a nagyobb dobozt 2026. augusztus 16-án 19:27:29 és
19:29:39 között levették az `esp32-dolgozo` szenzorról. A levétel előtti utolsó
mérés 19:27:29-kor 26,5625 °C, az első emelkedő érték 19:29:39-kor 26,7500 °C,
a kézi megfogás késleltetett maximuma pedig 19:31:49-kor 27,0000 °C volt. Ettől
az időponttól az érzékelő ismét csupasz konfigurációban mér. A dobozt nem
selejtezték: a következő változatban a három hosszú rést szigetelőszalaggal
leszűkítik, és további kisebb körfuratokkal biztosítják a szellőzést.

Az elhelyezés kalibrációs szempontból kedvező: a korábbi méréseken az
`esp32-dolgozo` és az `esp32-halo` szorosan együtt mozgó párt alkotott. Így a
dobozolt `dolgozo` közvetlen kontrollja a változatlan `halo` lehet, ugyanúgy,
ahogy a dobozolt `kisnappali` kontrollja az `ext`.

Az `esp32-kristofek` tendenciózusan a legalacsonyabb hőmérsékletet mérte. Ezért
a második dobozt az első összehasonlító futások előtt nem célszerű áttenni rá:
a szenzor saját alapeltérése és a doboz dinamikai hatása nehezebben lenne
szétválasztható. A `kristofek` külön dobozos vizsgálata később, saját doboz
előtti és utáni kontrollszakasszal végezhető el.

### 5.4 A két műanyag doboz geometriája

Mindkét doboz hengeres, de méretük és szellőzőnyílásaik elrendezése lényegesen
eltér. A kísérlet egyik célja annak vizsgálata, hogy ez okoz-e szignifikáns
eltérést a szenzorok dinamikus viselkedésében.

| Jellemző | `esp32-kisnappali` doboza | `esp32-dolgozo` doboza |
|---|---|---|
| Külső méret | 40 mm átmérő, 60 mm magasság | 60 mm átmérő, 85 mm magasság |
| Palást nyílásai | 8 db 10 mm-es furat két sorban, közöttük 4 db 10 mm-es furat; összesen 12 db | 3 db, egymástól 120°-ra elhelyezett, körülbelül 58 × 5 mm-es téglalap alakú nyílás, közöttük 3 db 6 mm-es furat |
| Nyílások magassága | az alsó furatok a palást aljától körülbelül 15 mm-re, a felsők a tetőtől körülbelül 25 mm-re | a 6 mm-es furatok a téglalap alakú nyílások középvonalának magasságában |
| Alsó nyílás | 1 db 10 mm-es furat, a szenzorral szemben | 1 db, körülbelül 26 × 6 mm-es téglalap alakú nyílás |
| Anyag és megmunkálhatóság | merevebb műanyag; nehezebben volt fúrható, sniccerrel nem lehetett vágni | egyértelműen lágyabb műanyag; a téglalap alakú nyílások sniccerrel kivághatók voltak |
| Közvetlen kontroll | `esp32-ext` | `esp32-halo` |

A közelítő geometriai számítás szerint a kisebb doboz belső térfogata mintegy
75 cm³, teljes nyílásfelülete körülbelül 1020 mm²; a nagyobb dobozé mintegy
240 cm³, illetve 1110 mm². A nagyobb doboz térfogata tehát körülbelül 3,2-szeres,
miközben a nyílásfelülete csak mintegy 9%-kal nagyobb. A nyílásfelület és a
térfogat aránya a kisebb doboznál körülbelül 13,5 mm²/cm³, a nagyobbnál
4,6 mm²/cm³. Emiatt előzetesen a nagyobb doboztól erősebb csillapítás és nagyobb
időállandó várható. A hosszú, irányított rések ugyanakkor a klíma légáramának
irányától függően növelhetik a kényszerített átöblítést, ezért ezt a következő
azonos paraméterű klímatesztek mérési adataiból kell eldönteni.

A két műanyag közötti különbséget a megmunkálás is egyértelműen jelezte: a
kisebb doboz merevebb volt, nehezebben lehetett megfúrni, és sniccerrel nem volt
vágható; a nagyobb doboz téglalap alakú nyílásai viszont sniccerrel készültek.
Ez eltérő anyagösszetételre vagy mechanikai tulajdonságra utalhat, de önmagában
nem bizonyít jobb hőszigetelést: azt az anyagfajta, a falvastagság és a szerkezet
együtt határozza meg. A mérésben ezért a lágyabb anyagot lehetséges további
csillapító tényezőként kezeljük, amelynek hatása nem választható el teljesen a
doboz nagyobb térfogatának és eltérő nyílásgeometriájának hatásától.

### 5.5 A nagyobb doboz leszűkített nyílású változata

2026. augusztus 17-én a nagyobb doboz három hosszú palástnyílását
szigetelőszalaggal jelentősen leszűkítették. A három eredeti, 6 mm-es körfurat
mindegyike fölé és alá kézi furdancs segítségével egy-egy további, kisebb furat
került, vagyis összesen hat új kis furat készült. Az új furatok pontos átmérője
nem lett megmérve.

A módosított dobozt 09:41-kor helyezték vissza az `esp32-dolgozo` szenzorra.
Ettől az időponttól ez külön fizikai konfigurációnak számít: „nagyobb doboz,
leszűkített hosszú nyílásokkal”. A módosítás célja a korábbi változatban
feltételezett közvetlen átöblítés csökkentése úgy, hogy a doboz szellőzése a
kilenc palástfuraton — három 6 mm-es és hat kisebb furaton — továbbra is
biztosított maradjon. A visszahelyezés utáni, kézi megfogásból eredő tranziens
adatait a klímateszt kiértékeléséből ki kell zárni; a teszt csak a relatív
szenzorsorrend és a görbe stabilizálódása után indítható.

Az adatbázisban a visszahelyezés előtti utolsó mérés 09:39:36-kor 26,1250 °C,
az első egyértelműen utána keletkezett mérés 09:41:46-kor 26,8750 °C volt.
09:43:56-kor az érték még 27,3125 °C-ra emelkedett, tehát ekkor a kézi
megfogásból eredő tranziens még nem ért véget.

A `dolgozo` 10:01:07-kor 26,3750 °C-ot, a csupasz `halo` kontroll 26,4375 °C-ot
mért; ettől kezdve a páros ismét a korábbi relatív tartományában mozgott. Az új
konfiguráció operatív stabilizálódási ideje ezért körülbelül 10:01: a
felhelyezéstől mintegy 20 perc, a 09:43:56-os maximumtól körülbelül 17 perc
telt el.

## 6. Klímatesztek

A klíma vezérlési állapota közel négyszögjelként értelmezhető: az indítás és a
leállítás pontosan naplózott. A helyiséget érő hőhatás azonban nem ideális
négyszögjel, mert a beltéri egység ventilátora, hőcserélője és kompresszora
menet közben módosíthatja a leadott teljesítményt.

| Dátum | Indítás | Leállítás | Időtartam | Cél | Ventilátor | Szenzorkialakítás |
|---|---:|---:|---:|---:|---|---|
| 2026-08-13 | 19:08:15 | 19:48:26 | 40,2 perc | 25 °C | nem naplózott | mind az öt gyári |
| 2026-08-14 | 18:45:11 | 19:35:24 | 50,2 perc | 25 °C | középmagas | mind az öt gyári |
| 2026-08-15 | 18:40:12 | 19:30:25 | 50,2 perc | 25 °C | középmagas | négy gyári, `kisnappali` dobozban |
| 2026-08-16 | 17:16:06 | 18:06:20 | 50,2 perc | 25 °C | középmagas | három gyári; `kisnappali` kisebb, `dolgozo` nagyobb dobozban |
| 2026-08-17 | 10:12:09 | 10:27:18 | 15,2 perc | 25 °C | középmagas | három gyári; `kisnappali` kisebb, `dolgozo` leszűkített nagyobb dobozban |
| 2026-08-17 | 18:07:11 | folyamatban | tervezett 50 perc | 25 °C | középmagas | három gyári; `kisnappali` kisebb, `dolgozo` leszűkített nagyobb dobozban |

A 18:07-es futás a délelőtti rövid teszt azonos szenzorkialakítással végzett,
50 perces kontrollja. A vendégszobai szellőztetést előtte lezárták, az
ajtót és az ablakot becsukták. Közvetlenül a klíma igazolt indulása után kézi
lekérdezési kör készült. A sor a futás lezárása és az adatsor kiértékelése után
egészítendő ki a tényleges leállási idővel és az eredményekkel.

A 2026. augusztus 16-i futás kezdő időpontját a kezelőfelületen 17:16-ra
állították; a klíma 17:16:06-kor bekapcsolt, majd 18:06:20-kor leállt. Az öt
ESP32 közvetlenül a futás előtt mért átlaga körülbelül 26,94 °C volt, szemben az
előző napi teszt körülbelül
26,71 °C-os kezdőátlagával. A hivatalos külső referencia az indulás környékén
34,3 °C-os Open-Meteo-adat; az Apple Watch 40 °C-ot, az Időkép körülbelül
34 °C-ot jelzett. Az utóbbi két érték kiegészítő megfigyelés, nem az elemzés
elsődleges külső adata.

Az első teljes, klímaindítás utáni mintavételi intervallumban, 17:15:52 és
17:18:02 között a két dobozolt szenzor letörése már kisebb volt a három csupasz
szenzorénál:

| Szenzor | Kialakítás | Első változás |
|---|---|---:|
| `esp32-kisnappali` | kisebb doboz | −0,0625 °C |
| `esp32-dolgozo` | nagyobb doboz | −0,0625 °C |
| `esp32-ext` | csupasz | −0,1250 °C |
| `esp32-kristofek` | csupasz | −0,1250 °C |
| `esp32-halo` | csupasz | −0,1875 °C |

Ez az első intervallumban fele–harmada akkora letörést jelent a dobozolt
szenzoroknál. Az eredmény előzetes: a teljes futás maximummeredeksége és becsült
időállandója alapján kell majd értékelni.

### 6.1 A 2026. augusztus 16-i két doboz összehasonlítása

| Szenzor | Kialakítás | Teljes letörés | Legmeredekebb szakasz | 25 °C első elérése az indítástól |
|---|---|---:|---:|---:|
| `esp32-ext` | csupasz, a kisebb doboz kontrollja | −3,8750 °C | −0,288 °C/perc | 12,5 perc |
| `esp32-kisnappali` | kisebb doboz | **−3,1250 °C** | **−0,173 °C/perc** | **23,1 perc** |
| `esp32-halo` | csupasz, a nagyobb doboz kontrollja | −4,3750 °C | −0,343 °C/perc | 10,3 perc |
| `esp32-dolgozo` | nagyobb doboz | −3,8125 °C | −0,280 °C/perc | 12,5 perc |
| `esp32-kristofek` | csupasz | −4,2500 °C | −0,311 °C/perc | 10,3 perc |

A nagyobb doboz a saját `halo` kontrolljához képest körülbelül 12,9%-kal
csökkentette a teljes letörést és 18,2%-kal a maximális csökkenési meredekséget.
Ez mérhető csillapítás, de lényegesen gyengébb a kisebb dobozénál: a kisebb
doboz csúcsmeredeksége körülbelül 40%-kal maradt el az `ext` kontrollétól, és a
25 °C-os határt több mint tíz perccel később érte el.

A nagyobb doboz ezért ebben a kialakításban nem megfelelő. A valószínű
magyarázat az, hogy a paláston elhelyezett három hosszú, 58 × 5 mm-es rés a
klíma irányított légáramában átöblítést engedett, és ezzel részben semlegesítette
a nagyobb térfogat és a lágyabb műanyag lehetséges csillapító hatását. Ez erősen
támogatott mérési hipotézis, de a nyílások részleges, visszafordítható lezárásával
végzett kontrollteszt nélkül nem tekinthető külön bizonyítottnak.

### 6.2 A leszűkített nagyobb doboz 15 perces tesztje

A dolgozószobai éjszakai szellőztetést 10:12:00-kor lezárták, a klíma pedig
10:12:09-kor indult el. A 15 perces rövid teszt célja nem a teljes időállandó
meghatározása volt, hanem annak gyors eldöntése, hogy a leszűkített nagyobb
doboz dinamikája elválik-e a csupasz szenzorokétól. A klíma 10:27:18-kor állt
le. Ezt két kézi lekérdezés követte: az első 10:27:27-kor a hűtés
lekapcsolását, a második 10:27:50-kor a ventilátor megállását rögzítette. A
szobát ezután legalább 15 percig zárva tartották, új szellőztetés indítása
nélkül, hogy a visszafutás külön zavarás nélkül legyen megfigyelhető.

| Szenzor | Kialakítás | Teljes letörés az aktív szakaszban | Legmeredekebb szakasz |
|---|---|---:|---:|
| `esp32-ext` | csupasz, a kisebb doboz kontrollja | −2,5000 °C | −0,260 °C/perc |
| `esp32-kisnappali` | kisebb doboz | **−1,5625 °C** | **−0,173 °C/perc** |
| `esp32-halo` | csupasz, a nagyobb doboz kontrollja | −2,6250 °C | −0,289 °C/perc |
| `esp32-dolgozo` | leszűkített nagyobb doboz | **−1,7500 °C** | **−0,173 °C/perc** |
| `esp32-kristofek` | csupasz | −2,6875 °C | −0,318 °C/perc |

A módosított `dolgozo` doboz maximális csökkenési meredeksége gyakorlatilag
megegyezett a korábban bevált kisebb dobozéval. A saját `halo` kontrolljához
képest a teljes letörést körülbelül 33,3%-kal, a maximális meredekséget pedig
körülbelül 40,0%-kal csökkentette. Ez lényeges javulás a hosszú nyílásos
változat 12,9%-os, illetve 18,2%-os csillapításához képest, és erősen
alátámasztja, hogy a korábbi gyenge eredményt valóban a hosszú réseken kialakuló
közvetlen átöblítés okozta.

A két doboz közel azonos maximális csökkenési meredeksége annak ellenére alakult
ki, hogy a nagyobb doboz térfogata körülbelül 3,2-szerese a kisebbének. Ez erősen
arra utal, hogy a vizsgált mérettartományban a térfogat önmagában nem domináns
tényező. A viselkedést sokkal inkább a levegőcsere geometriája határozza meg: a
hosszú, irányított átöblítési út megszüntetése, valamint a több ponton elosztott,
legfeljebb 10 mm-es körfuratok használata.

A jelenlegi kísérletből nem következik általánosan, hogy minden 10 mm alatti
furatátmérő egyenértékű. Ehhez azonos dobozon, azonos teljes nyílásfelülettel és
eltérő furatátmérőkkel végzett kontrollált mérés kellene. A mostani adatok alapján
az a szűkebb következtetés tehető, hogy az alkalmazott, 10 mm-nél nem nagyobb
furatok tartományában a furatátmérő hatása kisebbnek látszik, mint a nyílások
alakjának, térbeli eloszlásának és a légáramhoz viszonyított irányítottságának
hatása. A nagyobb doboz módosítás utáni tényleges szabad nyílásfelülete a
szalaggal leszűkített rések szabálytalan alakja miatt csak közelítőleg lenne
meghatározható.

#### Kikapcsolás utáni visszaállás és az azt követő szellőztetés

A klíma leállítása után a csupasz szenzorok már 10:29:54-kor emelkedni kezdtek.
A dobozolt `dolgozo` ekkor még 0,0625 °C-kal tovább csökkent, a dobozolt
`kisnappali` pedig változatlan maradt. Ez a dobozok fizikai késleltetésének
közvetlen jele.

A `dolgozo–halo` páros eltérése a klíma végén még 0,75 °C volt, majd
10:34–10:36-ra egyetlen DS18B20-kvantálási lépcső környékére csökkent. A
`kisnappali–ext` eltérés 10:27:50-kor 0,875 °C volt, 10:38:43-kor már csak
0,0625 °C, 10:40:53-kor pedig mindkét szenzor 25,3750 °C-ot mért. A teljes
relatív visszaállás így a klíma leállításától számítva körülbelül 13 percet vett
igénybe. Ez nem az eredeti abszolút szobahőmérséklet visszaállását jelenti,
hanem a dobozolt és csupasz kontrollgörbék újbóli konvergenciáját.

A zárt szobás lezáró kézi lekérdezés 11:03:17-kor készült, majd a
dolgozószobai szellőztetés 11:03:00-s naplózott kezdőidővel elindult. A
szolgáltatói külső hőmérséklet ekkor 30,8 °C volt, miközben az öt DS18B20
25,6250–25,9375 °C közötti értékeket mért. A szellőztetés ezért ebben a
szakaszban melegítő, nem hűtő gerjesztést jelentett.

| Szenzor | Érték 11:03 körül | Érték 11:29 körül | Változás |
|---|---:|---:|---:|
| `esp32-ext` | 25,8125 °C | 26,3125 °C | +0,5000 °C |
| `esp32-kisnappali` | 25,9375 °C | 26,3125 °C | +0,3750 °C |
| `esp32-halo` | 25,6875 °C | 26,1250 °C | +0,4375 °C |
| `esp32-dolgozo` | 25,6875 °C | 26,0625 °C | +0,3750 °C |
| `esp32-kristofek` | 25,6250 °C | 26,0000 °C | +0,3750 °C |

A két dobozolt érzékelő a lassú felmelegedési trendet továbbra is követi. A
kisebb változás ebben a rövid szakaszban összhangban van a gyors komponensek
csillapításával, de önmagában még nem különíti el a doboz hatását a szenzorok
alapeltérésétől és térbeli helyzetétől.

### 6.3 Teljes letörés a klíma működése alatt

A táblázat a klímaindításhoz legközelebbi mérés és az aktív időszak minimuma
közötti különbséget mutatja. A 2026. augusztus 13-i értékek a ritkább
mintavétel miatt kisebb időbeli pontosságúak.

| Eszköz | 2026-08-13 | 2026-08-14 | 2026-08-15 |
|---|---:|---:|---:|
| `esp32-ext` | −3,063 °C | −3,813 °C | −3,938 °C |
| `esp32-dolgozo` | −3,688 °C | −4,500 °C | −4,500 °C |
| `esp32-halo` | −3,688 °C | −4,438 °C | −4,500 °C |
| `esp32-kisnappali` | −3,063 °C | −3,813 °C | **−3,250 °C** |
| `esp32-kristofek` | −3,500 °C | −4,313 °C | −4,313 °C |
| `iot-computherm-emelet` | −1,300 °C | −1,700 °C | −1,900 °C |

A két azonos, 50 perces és középmagas ventilátorfokozatú mérés között a dobozolt
`kisnappali` letörése 0,5625 °C-kal, körülbelül 14,8%-kal kisebb lett. Ezzel
szemben a négy változatlan ESP32 letörése hasonló vagy kissé nagyobb volt, ezért
az eltérés nem magyarázható a teljes helyiség gyengébb lehűlésével.

A 2026. augusztus 15-i minimumoknál a dobozolt `kisnappali` 23,625 °C-ot, a
gyári ESP32-k 22,125–22,875 °C-ot, a Computherm pedig 25,1 °C-ot mért. A
Computherm háza és belső feldolgozása mindhárom alkalommal lényegesen tompább
választ adott.

### 6.4 Legmeredekebb csökkenés

A körülbelül 2 perc 10 másodperces mintavétel mellett mért legnagyobb negatív
szakaszmeredekségek:

| Eszköz | 2026-08-14 | 2026-08-15 |
|---|---:|---:|
| `esp32-ext` | −0,317 °C/perc | −0,288 °C/perc |
| `esp32-dolgozo` | −0,403 °C/perc | −0,404 °C/perc |
| `esp32-halo` | −0,404 °C/perc | −0,375 °C/perc |
| `esp32-kisnappali` | **−0,288 °C/perc** | **−0,173 °C/perc** |
| `esp32-kristofek` | −0,375 °C/perc | −0,346 °C/perc |
| `iot-computherm-emelet` | −0,049 °C/perc | −0,050 °C/perc |

A `kisnappali` maximális csökkenési meredeksége a dobozban körülbelül 40%-kal
kisebb lett. Ez az eddigi legerősebb jel arra, hogy a doboz valóban csillapítja
a gyors légáramhatást.

### 6.5 A 25 °C-os célérték elérése

2026. augusztus 14-én a gyári DS18B20-k körülbelül 7,6–10,3 perccel az indítás
után érték el először a 25 °C-ot vagy annál kisebb értéket. A Computherm ezt
43,8 perc után érte el.

2026. augusztus 15-én a változatlan DS18B20-k 8,6–10,8 perc után, a dobozolt
`kisnappali` 17,3 perc után érte el ugyanezt a határt. A Computherm minimuma
25,1 °C volt, tehát ezen a futáson nem érte el a 25 °C-ot.

Ez nem jelenti azt, hogy a helyiség tényleges átlaghőmérséklete ilyen gyorsan
elérte a klíma célértékét. A gyors átlépés elsősorban a szenzorokat érő hideg
légáramot mutatja. A doboz körülbelül hét perccel késleltette ezt a reakciót.

### 6.6 Leállítás utáni visszafutás

Harminc perccel a leállítás után az öt DS18B20 2026. augusztus 14-én
25,56–25,94 °C, 2026. augusztus 15-én 25,75–26,06 °C között volt. Hatvan perc
után egyik futásnál sem tértek vissza a klíma előtti érték 0,2 °C-os környezetébe.
Ez önmagában nem szenzorkésés: a helyiség a klíma miatt ténylegesen lehűlt, és a
korábbi két estén a későbbi szellőztetés is megszakította a tiszta visszaállási
szakaszt. A stabilizálódást ezért nem szabad kizárólag a kiindulási értékhez való
visszatéréssel definiálni; a görbe meredekségének tartós lecsökkenését és a
szenzorok ismételt együttmozgását is vizsgálni kell.

## 7. A műanyag doboz előzetes dinamikai becslése

Az `esp32-ext` és az `esp32-kisnappali` a dobozolás előtt nyugodt levegőben és
klíma alatt is szorosan együtt mozgott. Emiatt az `ext` használható előzetes
kontrollbemenetként, a dobozolt `kisnappali` pedig kimenetként.

A változó mintaközt figyelembe vevő elsőrendű modell:

\[
\alpha_i = 1-e^{-\Delta t_i/\tau}, \qquad
y_i = \alpha_i x_i + (1-\alpha_i)y_{i-1}.
\]

### 7.1 Becsült időállandó a 63,2%-os válasz alapján

A dobozolt `kisnappali` teljes, klíma alatti hőmérséklet-esése 3,25 °C volt,
26,875 °C-ról 23,625 °C-ra. Ideális elsőrendű rendszer és lépcsőszerű bemenet
esetén az időállandó ott olvasható le, ahol a kimenet a teljes változás 63,2%-át
eléri. A keresett hőmérséklet:

\[
26{,}875 - 0{,}632 \cdot 3{,}25 = 24{,}821\ ^\circ\mathrm{C}.
\]

A szenzor 18:59:37-kor 24,8125 °C-ot mért, ami egyetlen DS18B20-kvantálási
lépcsőn belül megfelel ennek az értéknek. Ha a klíma hőhatásának kezdetét a
gyári szenzorok 18:42:16-kor induló letöréséhez kötjük, akkor:

\[
\tau_{doboz,63{,}2\%} = 18{:}59{:}37 - 18{:}42{:}16
= 1041\ \mathrm{s} \approx 17{,}35\ \mathrm{perc}.
\]

Ez egyszerű és fizikailag jól értelmezhető becslés, de az eredmény csak akkor
lenne közvetlen időállandó, ha a szenzort érő levegő hőmérséklete valódi
lépcsőjelként változna, a 23,625 °C pedig a rendszer végleges állandósult értéke
lenne. A klíma teljesítménye és légárama menet közben változhatott, a minimum
pedig közvetlenül a leállítás előtt keletkezett. Emiatt a 17,35 percet
`63,2%-os látszólagos időállandóként` kezeljük, nem végleges fizikai
paraméterként.

### 7.2 Becsült időállandó az `esp32-ext` kontrolljel illesztésével

A 2026. augusztus 15-i klímafutásra végzett rácskeresés előzetes eredménye:

- becsült fizikai időállandó: `τ ≈ 658 s`, azaz körülbelül 11 perc;
- 130 másodperces tipikus mintaköznél `α ≈ 0,179`;
- a szűrt modell RMSE-je 0,229 °C;
- a késleltetés nélküli, párosított `ext`–`kisnappali` eltérés RMSE-je 0,723 °C.

Kontrollként a 2026. augusztus 14-i, még doboz nélküli futásnál a legjobb
illesztés gyakorlatilag késleltetés nélküli volt (`α ≈ 1`), 0,056 °C RMSE-vel.
Ez összhangban van azzal a megfigyeléssel, hogy a két szenzor eredetileg együtt
mozgott, a műanyag doboz pedig hozzávetőleg 10–11 perces fizikai tehetetlenséget
adott hozzá a kontrolljelhez végzett illesztés szerint.

A két módszer eredménye tehát:

- 63,2%-os, ideális lépcsőválasz-feltételezés: `τ ≈ 1041 s`;
- a tényleges `esp32-ext` kontrollgörbéhez illesztett változó mintaközű modell:
  `τ ≈ 658 s`.

Az eltérés nem számítási ellentmondás. Az első módszer a futás végén mért
minimumot tekinti a teljes lépcsőválasz végértékének, a második pedig a
valóságban mért, időben változó kontrollgörbét használja bemenetként. Jelenleg a
doboz hatásának valószínű tartományát körülbelül 11–17 percnek tekintjük. Ezt
további, azonos protokollú futásokkal kell szűkíteni.

### 7.3 Változások száma és a jel teljes mozgása 24 óra alatt

A dobozolási beavatkozás átmenetének kizárása érdekében a vizsgált 24 órás
időablak 2026. augusztus 15. 10:06-tól augusztus 16. 10:06-ig tart. Az ablak a
klímatesztet és az éjszakai környezeti változásokat is tartalmazza, így nemcsak
nyugodt levegőben hasonlítja össze a két érzékelőt.

| Mutató | `esp32-ext` | dobozolt `esp32-kisnappali` | Különbség |
|---|---:|---:|---:|
| Érvényes mérési pont | 666 | 665 | −1 |
| Az előzőtől eltérő mérés | 280 | 243 | −37 (−13,2%) |
| Változatlan egymást követő mérés | 385 | 421 | +36 |
| Irányváltások száma | 118 | 114 | −4 |
| Teljes abszolút jelmozgás | 24,375 °C | 18,8125 °C | −5,5625 °C (−22,8%) |
| Legnagyobb két mérés közötti lépés | 0,625 °C | 0,375 °C | −40,0% |
| Nettó 24 órás változás | +0,375 °C | +0,3125 °C | −0,0625 °C |

A dobozolt érzékelő kevesebbszer változott, több egymást követő azonos értéket
adott, kisebb teljes utat járt be, és a legnagyobb rövid lépése is lényegesen
kisebb volt. Eközben a nettó 24 órás változás csak egyetlen DS18B20-lépéssel
tért el az `ext` értékétől. Ez arra utal, hogy a doboz a gyors komponenseket
csillapítja, miközben a lassú hőmérsékleti trend követése megmarad.

A változások puszta darabszáma önmagában nem elegendő szűrőminőségi mutató,
mert a DS18B20 0,0625 °C-os kvantálása és a határérték körüli oda-vissza váltás
befolyásolja. Emiatt a további értékelésekben együtt kell vizsgálni a
változásszámot, a teljes abszolút jelmozgást, a lépésnagyságok eloszlását, az
irányváltásokat és a tartós trend követési késését.

### 7.4 Természetes huzatimpulzusok 2026. augusztus 16–17. éjszakáján

Az éjszakai, tartós szellőztetés alatt több jól érzékelhető átfúvás történt:
23–24 óra és 0–1 óra között, kevéssel 03:00 előtt, valamint 06:15 és 07:30
között több alkalommal. Ezek független, természetes légáramlási gerjesztést
adtak. Mind az öt DS18B20 követte az eseményeket, ezért a közös letörések nem
egyetlen szenzor hibájának tekinthetők.

| Helyi időablak | Legerősebb azonosított impulzus | Csupasz `ext` legnagyobb mintaközi esése | Dobozolt `kisnappali` legnagyobb mintaközi esése | Teljes tartomány: `ext` / `kisnappali` |
|---|---|---:|---:|---:|
| 23:00–24:00 | 23:34–23:36 | −0,1875 °C | −0,0625 °C | 0,1875 / 0,1250 °C |
| 00:00–01:00 | 00:19–00:21 | −0,4375 °C | −0,1250 °C | 0,5000 / 0,1875 °C |
| 02:30–03:00 | 02:50–02:53 | −0,4375 °C | −0,1250 °C | 0,6875 / 0,3125 °C |
| 06:15–07:30 | legerősebb: 07:14–07:17 | −0,4375 °C | −0,0625 °C | 0,5625 / 0,2500 °C |

A kisebb, körfuratos doboz minden vizsgált időablakban csökkentette mind a
legnagyobb rövid esést, mind a teljes hőmérsékleti tartományt. A legerősebb
huzatimpulzusoknál a dobozolt szenzor mintaközi letörése a csupasz kontroll
értékének körülbelül 14–29%-a volt. Ez a klímateszttől függetlenül is alátámasztja,
hogy a kisebb doboz a rövid légáramlási komponenseket hatásosan csillapítja,
miközben az események lassabb hőmérsékleti hatását továbbra is követi.

Az eredmények dobozos klímafutásokból és egy éjszakai természetes
huzatsorozatból származó előzetes becslések. Nem tekinthetők végleges
kalibrációs paraméternek, mert a klíma tényleges hőárama és a huzat sebessége nem
ismert, a két szenzor nem ugyanazon pontban van, és a kompresszor teljesítménye
menet közben változhat. Ismételt méréssel kell ellenőrizni őket.

## 8. Kiértékelési terv

Minden új fizikai konfigurációnál az alábbiakat kell mérni:

1. klíma előtti stabil szakasz és szenzorok közötti alapeltérés;
2. a klímaindítás után jelentkező késés;
3. legnagyobb negatív gradiens és teljes letörés;
4. a beállított célérték első elérésének ideje;
5. minimum érték és annak időpontja;
6. leállítás utáni legnagyobb pozitív gradiens;
7. a szenzorok ismételt együttmozgásának és a meredekség stabilizálódásának ideje;
8. Computhermhez viszonyított amplitúdó- és fáziskülönbség;
9. időfüggő EMA illesztése több `τ` értékkel;
10. legalább 30 perces, megfelelően illeszkedő lineáris növekedési vagy
    csökkenési szakaszok felismerése, legalább hat ponttal és dokumentált
    illesztési jósággal.

A következő konfigurációk:

- gyári DS18B20;
- szellőző műanyag doboz;
- hővezető pasztával rézcsőhöz kapcsolt DS18B20;
- műanyag doboz és rézcső együtt.

A fizikai burkolat és az EMA két egymást követő aluláteresztő szűrőként működik.
A végső cél ezért nem a lehető legsimább görbe, hanem a legkisebb olyan teljes
késleltetés megtalálása, amely a rövid légáramhatást elnyomja, miközben a tartós
helyiséghőmérséklet-változást még megfelelő gyorsasággal követi.

## 9. Rendelkezésre álló adatok és tesztprotokoll

### 9.1 Automatikusan rendelkezésre álló adatok

A klíma üzemmódja, célértéke, ventilátorfokozata, indítási és leállítási
időpontja, valamint tényleges futásideje az alkalmazás adatbázisában megvan.
Ezeket nem kell külön kézzel naplózni.

A szenzorok tényleges mérési időpontjai szintén az adatbázisban vannak. Ezekből
meghatározható a valós mintavételi gyakoriság, annak változása és minden mérési
kimaradás. A kiértékelésnek a tényleges időbélyegekkel kell számolnia, nem a
beállított névleges lekérdezési idővel.

A klíma előtti beltéri hőmérsékletet a kalibrációban részt vevő szenzorok
közvetlenül szolgáltatják. Külső hőmérsékleti referenciaként jelenleg legfeljebb
az Open-Meteo adatára támaszkodhatunk. Ez szolgáltatói becslés, nem helyben mért
hőmérséklet, ezért csak tájékoztató környezeti adatként használható.

### 9.2 A klímateszt kizáró feltételei

A klíma futása alatt nincs szellőztetés, felesleges járkálás vagy porszívózás.
Az ajtók és ablakok állapotát a futás közben nem változtatjuk meg. Ha ez mégis
megtörténik, az adott futást meg kell jelölni protokolleltérésként, és nem
szabad tiszta klímatesztként felhasználni a fizikai időállandó becsléséhez.

A klíma leállítása utáni megfigyelési időben szintén kerülni kell a
szellőztetést és más erős légmozgást addig, amíg a visszafutáshoz szükséges
legalább 30–60 perces adatszakasz el nem készül.

### 9.3 Kézzel rögzítendő fizikai konfiguráció

A szenzor fizikai kialakítása nem következtethető ki a mérési adatokból. Minden
módosításnál rögzíteni kell:

- az érintett szenzort;
- a konfigurációt: gyári, műanyag doboz, rézcső vagy doboz és rézcső;
- a módosítás pontos helyi időpontját;
- opcionális megjegyzést, például megfogás, áthelyezés vagy hővezető paszta
  használata;
- a stabilizálódás megállapított időpontját, amikor az már meghatározható.

Ehhez indokolt külön alkalmazásfunkció és adatbázistábla létrehozása. A
konfigurációváltás eseményként kerüljön tárolásra, ne a korábbi állapot
felülírásával, így bármely nyers méréshez utólag egyértelműen hozzárendelhető a
méréskor érvényes fizikai kialakítás. A 2026. augusztus 15-i 09:27-es dobozolás
ennek az első visszamenőleg rögzítendő eseménye.

Az eltérő napokon végzett klímateszteket csak ezeknek a körülményeknek a
figyelembevételével szabad összehasonlítani.
