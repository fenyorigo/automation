# `esp32-rita` sárgaréz cső + dupla falú doboz mérési jegyzőkönyve

## 1. A vizsgálat célja

A vizsgálat célja annak meghatározása, hogy a DS18B20 szondára húzott
sárgaréz cső és a perforált, dupla falú gyógyszeresdoboz együttesen mennyire
csillapítja a rövid légáramlási hatásokat. Az értékelés összehasonlítja az
`esp32-rita` korábbi csupasz és új kombinált kialakítását, továbbá az új
kialakítást az ugyanott, változatlanul mérő kontrollokkal.

Az időpontok budapesti helyi időben, CEST (`UTC+02:00`) szerint szerepelnek.
A vizsgált adatsor vége: **2026. augusztus 20. 11:59:25**.

## 2. Fizikai kialakítás és a beavatkozás

Az `esp32-rita` érzékelőre 2026. augusztus 19-én **17:33-kor** került fel:

- egy 40 mm-nél kissé hosszabb D8 sárgaréz cső;
- egy perforált, dupla falú gyógyszeresdoboz;
- hővezető paszta nélkül.

A beavatkozást közvetlenül kézi lekérdezési kör követte. Az adatbázis első,
egyértelműen beavatkozás utáni pontja 17:33:32-kor keletkezett.

A doboz méretei:

- külső átmérő: 48 mm;
- magasság: 69 mm;
- felső palástsor, az aljtól 44 mm-re: 4 db Ø8 mm-es furat;
- középső palástsor, az aljtól 20 mm-re: 4 db Ø8 mm-es furat, a felső sorhoz
  képest 45°-kal elforgatva;
- alsó palástsor, az aljtól 15 mm-re: 4 db Ø6 mm-es furat;
- a doboz alján: 3 db Ø6 mm-es furat, a perem közelében, 120°-os eloszlásban.

A névleges furatfelület körülbelül 600 mm². A külső méretekből számított
hengeres térfogat körülbelül 125 cm³, de a dupla fal miatt a tényleges belső
légtér ennél kisebb. A névleges furatfelület/térfogat arány hozzávetőleg
4,8 mm²/cm³. Ez csak geometriai jellemző: a dupla fal, a furatok tényleges
átvezetése és a szenzor helyzete az effektív légcserét külön is befolyásolja.

## 3. Összehasonlító elrendezés

| Eszköz | Kialakítás a beavatkozás után | Szerep |
|---|---|---|
| `esp32-ext` | csupasz DS18B20 | csupasz referencia |
| `esp32-nappali` | D8 sárgaréz cső | csak csöves kontroll |
| `esp32-rita` | D8 sárgaréz cső + dupla falú doboz | vizsgált kombináció |
| `esp32-veronika` | csupasz DS18B20 | csupasz kontroll |

A névleges lekérdezési gyakoriság körülbelül két perc. A pontokat a Rita
időbélyegeihez legfeljebb 45 másodperces eltéréssel párosítottuk. A két csupasz
kontroll közös referenciája az `esp32-ext` és az `esp32-veronika` adott
mintához tartozó számtani átlaga.

## 4. A csupasz `esp32-rita` alapszakasza

A teljes csupasz alapszakasz 2026. augusztus 18. 10:29:46 és augusztus 19.
17:31:27 között 861 közös mérési pontot tartalmazott. A Rita ebben az
időszakban szorosan és párhuzamosan mozgott a két csupasz kontrollal:

- a Rita eltérése a csupasz kontrollátlagtól átlagosan −0,093 °C volt;
- az eltérés szórása csak 0,031 °C;
- az eltérés teljes tartománya −0,156 és 0,000 °C közé esett;
- a mintaközi változások szórása 0,0426 °C volt, lényegében ugyanannyi, mint a
  csupasz érzékelőké;
- a csupasz Rita tehát nem mutatott önmagában érzékelhető fizikai csillapítást.

A kombinált szakasz hosszával közel azonos, közvetlenül megelőző 18,4 órás
ablakban a Rita teljes abszolút jelmozgása 13,00 °C volt. A két csupasz
kontrollé 12,625, illetve 13,50 °C; ez szintén az azonos dinamikát támasztja
alá.

## 5. Felhelyezési tranziens és stabilizálódás

A kézi megfogás erős, egyértelműen nem környezeti hőimpulzust okozott:

- beavatkozás előtti utolsó Rita-mérés: 17:31:27, 27,0000 °C;
- első beavatkozás utáni mérés: 17:33:32, 29,7500 °C;
- maximum: 17:34:30, 29,8750 °C;
- a csupasz kontrollátlaghoz viszonyított maximális többlet: +2,8125 °C.

A relatív eltérés 17:58:09-kor már +0,0938 °C, 18:00:19-kor +0,0313 °C,
18:02:29-kor pedig −0,0313 °C volt. Ez alapján a felhelyezési tranziens
operatív lecsengési ideje körülbelül **27–29 perc**. A 17:33 és körülbelül
18:02 közötti adatokat a normál zaj- és offsetértékelésből ki kell zárni.

## 6. Azonos klímagerjesztés alatti viselkedés

A dolgozószobai Hisense klíma 2026. augusztus 19-én 18:33:16 és 18:53:27
között futott, 25 °C-os célértékkel. Ez az esemény azonos, erős gerjesztést
adott mind a négy érzékelőnek. A kezdőérték a klíma előtti körülbelül 12 perc
átlaga; a minimumot a futás kezdetétől a leállítás utáni 20 percig kerestük.

| Eszköz | Kialakítás | Kezdőátlag | Minimum | Teljes letörés | Legmeredekebb csökkenés | Minimum ideje az indítástól |
|---|---|---:|---:|---:|---:|---:|
| `esp32-ext` | csupasz | 27,0938 °C | 24,0625 °C | 3,0313 °C | −0,317 °C/perc | 19,9 perc |
| `esp32-nappali` | csak cső | 26,6875 °C | 23,5625 °C | 3,1250 °C | −0,260 °C/perc | 20,8 perc |
| `esp32-rita` | cső + dupla falú doboz | 26,7708 °C | 24,6875 °C | **2,0833 °C** | **−0,144 °C/perc** | **25,0 perc** |
| `esp32-veronika` | csupasz | 26,9063 °C | 23,2500 °C | 3,6563 °C | −0,375 °C/perc | 19,9 perc |

A két csupasz kontroll átlagához képest a kombinált Rita:

- a teljes letörést körülbelül **37,7%-kal csökkentette**;
- a legmeredekebb csökkenést körülbelül **58,3%-kal csökkentette**;
- a minimumot körülbelül **5 perccel később** érte el.

A csak csöves `esp32-nappali` szenzorhoz képest a kombinált Rita:

- a teljes letörést körülbelül **33,3%-kal csökkentette**;
- a legmeredekebb csökkenést körülbelül **44,4%-kal csökkentette**;
- a minimumot körülbelül **4,2 perccel később** érte el.

Ez a mérés közvetlenül igazolja, hogy a doboz a sárgaréz csőhöz képest is
jelentős további dinamikai csillapítást adott. A cső kissé eltérő hossza miatt
azonban a többlethatás nem tulajdonítható kizárólag a doboznak.

## 7. Hosszabb, felhelyezés utáni szakasz

A felhelyezési tranziens első 40 percének elhagyása után 496 párosított pont,
17,77 órányi mérés maradt. Ebbe beletartozik a klímafutás és a 19:57-kor
elindított, a vizsgálat végén még nyitott dolgozószobai szellőztetés is. Ezért
az alábbi eredmények nem nyugodt laboratóriumi zajt, hanem valós légáramlási
terhelést jellemeznek.

| Mutató | `ext` csupasz | `nappali` cső | `rita` cső+doboz | `veronika` csupasz |
|---|---:|---:|---:|---:|
| Mintaközi változások szórása | 0,0699 °C | 0,0658 °C | **0,0451 °C** | 0,0823 °C |
| Átlagos abszolút mintaközi változás | 0,0283 °C | 0,0264 °C | **0,0207 °C** | 0,0294 °C |
| Legnagyobb abszolút mintaközi változás | 0,6875 °C | 0,5625 °C | **0,3125 °C** | 0,8125 °C |
| Teljes abszolút jelmozgás | 14,0000 °C | 13,0625 °C | **10,2500 °C** | 14,5625 °C |
| Eltérő egymást követő pontok száma | 161 | 152 | **139** | 150 |
| Lineáris trendtől vett RMSE | 0,4517 °C | 0,4328 °C | **0,3619 °C** | 0,5022 °C |

A kombinált Rita mintaközi változásának szórása a két csupasz kontroll
átlagánál körülbelül **41%-kal**, a teljes jelmozgása körülbelül **28%-kal**
kisebb. A legnagyobb rövid lépés 0,3125 °C volt, szemben a csupasz kontrollok
0,6875 és 0,8125 °C-os értékével.

A csak csöves `esp32-nappali` értékéhez képest a kombinált kialakítás
mintaközi szórása körülbelül 31,5%-kal, teljes jelmozgása 21,5%-kal, maximális
lépése pedig 44,4%-kal kisebb. Ez alátámasztja a klímafutásból kapott
következtetést: a perforált, dupla falú doboz a cső önálló hatásán túl is
érdemi csillapítást ad.

## 8. Következtetések

1. **A csupasz Rita megfelelő saját kontroll.** A beavatkozás előtt
   gyakorlatilag együtt mozgott a csupasz kontrollokkal, állandó, körülbelül
   −0,09 °C-os alapeltéréssel. A későbbi dinamikai különbség ezért nem magyarázható
   a szenzor korábban is eltérő viselkedésével.
2. **A cső + dupla falú doboz kombináció erősen csillapít.** Ezt ugyanazon
   klímaimpulzus kisebb amplitúdója, lényegesen kisebb maximális gradiense és
   későbbi minimuma egyaránt mutatja.
3. **A doboz a puszta csőhöz képest is további szűrést ad.** A kombinált Rita
   minden fontos rövid idejű mutatóban simább volt a csak csöves Nappalinál.
4. **A felhelyezési tranziens hosszú.** A kézi érintés után közel fél óra kell
   a relatív egyensúly visszaállásához; minden fizikai módosítás után legalább
   30 perc kizárandó.
5. **A csillapítás ára mérhető késés.** A klímahatás minimuma körülbelül öt
   perccel később jelentkezett, mint a csupasz szenzorokon. Vezérlési célra azt
   kell eldönteni, hogy ez a késés elfogadható-e a légáramlási áljelek
   visszaszorításáért cserébe.
6. **Az abszolút offsetet külön kell kezelni.** A burkolás előtti −0,09 °C-os
   eltérés és a burkolás utáni tranziens nem keverhető össze a dinamikai
   csillapítással. A nyugodt, hosszabb utólagos szakaszból később külön
   korrekciós offset becsülhető.
7. **Az eredmény erős, de egyetlen kontrollált klímafutásból származik.** Az
   azonos konfigurációjú ismétlés szükséges a százalékos értékek
   reprodukálhatóságának ellenőrzéséhez.

## 9. Javasolt következő lépések

- A jelenlegi konfigurációt fizikai változtatás nélkül legalább további 24
  órán át mérni.
- Azonos célértékű, üzemmódú és ventilátorfokozatú klímafutással megismételni
  a gerjesztést.
- Külön értékelni a tartós, lassú hőmérsékleti trend követési hibáját, nemcsak
  a rövid impulzusok csillapítását.
- A hővezető paszta felvitele új konfigurációváltásnak számítson, pontos
  időbélyeggel és új stabilizálódási szakasszal.
- A végleges döntésnél a kombinált fizikai szűrés mellé csak akkora EMA-időállandót
  választani, amely nem növeli szükségtelenül tovább a teljes késést.

## 10. Módszertani korlátok

- A két sárgaréz cső hossza nem teljesen azonos.
- Hővezető paszta egyik vizsgált csöves kialakításban sem volt.
- A doboz dupla falú; a hőkapacitás, a hőszigetelés és a csökkent légcsere
  hatása ebből az egy kísérletből nem választható szét.
- A trendmentesített RMSE nem tisztán nagyfrekvenciás zaj: tartalmazhat lassabb
  görbületet, kvantálást és tranziens eseményeket is.
- A kétperces diszkrét mintavétel a minták közötti pontos görbét nem mutatja.
- Az összehasonlítás valós szobai környezetben készült; előnye a gyakorlati
  relevancia, hátránya a nem teljesen szabályozott légáramlás.
