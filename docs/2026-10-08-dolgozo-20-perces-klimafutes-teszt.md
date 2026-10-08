# Dolgozószobai 20 perces klímafűtési próba – 2026. október 8.

## Cél és beállítás

A próba azt vizsgálja, hogy a tegnapi egyórás futásnál lényegesen rövidebb,
20 perces fűtés mennyire közelíti meg a dolgozóban megfelelőnek érzett
20,5 °C körüli stabilizált cselekedeti hőmérsékletet, és a felfűtés után
mennyi ideig marad komfortos a helyiség.

- klíma: `HS dolgozó`;
- üzemmód: fűtés;
- célhőmérséklet: 21 °C;
- ventilátor: közepes, nem Auto;
- a dolgozó és a háló közötti ajtó nyitva;
- bekapcsolás: 09:30;
- a tényleges légáramlás és a 21 °C / közepes állapot igazolása: 09:32:52;
- kikapcsolás: 09:53 körül;
- utófutás: körülbelül 20 másodperc;
- a kikapcsolt állapot közvetlen visszaigazolása: 09:53:48.

A Hisense nyers visszaolvasásában közepes ventilátornál
`t_fan_speed=7` szerepelt. A klíma saját beltéri hőmérője a leállításkor
25 °C-ot közölt; ezt a korábbi próbákhoz hasonlóan nem használjuk helyiségi
vezérlési értékként.

A rövid utófutás miatt a tényleges meleg légáramlás hozzávetőleg 09:53:20-kor
szűnt meg. Ez az egyórás lecsengési szakasz értelmezésében elhanyagolható
eltérés, ezért annak referenciaideje továbbra is 09:53.

## Indulási és leállítási pont

Az időpontok Europe/Budapest helyi idő szerint értendők. A Zigbee-eszközök
változásvezérelten jelentenek, ezért a táblázat a legutóbbi tényleges mérési
időpontokat tartalmazza.

| Forrás | Indulás | Leállítás | Változás |
|---|---:|---:|---:|
| Zb dolgozó | 19,0 °C (09:19:18) | 21,0 °C (09:52:53) | +2,0 °C |
| CT400 emelet | 19,0 °C (09:27:25) | 19,6 °C (09:53:46) | +0,6 °C |
| Dolgozó cselekedeti átlag | 19,0 °C | 20,3 °C | +1,3 °C |
| Zb háló | 18,8 °C (09:14:56) | 19,0 °C (09:52:11) | +0,2 °C |
| Zb ext | 15,1 °C (09:18:23) | 15,1 °C (09:47:15) | 0,0 °C |

## Egyórás utánmérés

| Forrás | Leállítás | Egy órával később | Változás a leállításhoz képest | Változás az induláshoz képest |
|---|---:|---:|---:|---:|
| Zb dolgozó | 21,0 °C | 19,8 °C (10:46:46) | −1,2 °C | +0,8 °C |
| CT400 emelet | 19,6 °C | 19,6 °C (10:53:49) | 0,0 °C | +0,6 °C |
| Dolgozó cselekedeti átlag | 20,3 °C | 19,7 °C | −0,6 °C | +0,7 °C |
| Zb háló | 19,0 °C | 19,0 °C (10:52:06) | 0,0 °C | +0,2 °C |
| Zb ext | 15,1 °C | 15,8 °C (10:49:27) | +0,7 °C | +0,7 °C |

A klíma 10:53:50-kor is igazoltan kikapcsolt és online volt. A leállítás óta
a dolgozó cselekedeti hőmérséklete 0,6 °C-ot csökkent, de még 0,7 °C-kal az
indulási érték fölött maradt. A két dolgozói érzékelő közötti eltérés
1,4 °C-ról 0,2 °C-ra csökkent: a légáramhoz közelebbi Zigbee-hőmérő gyors
csúcsértéke lecsengett, miközben a Computherm által reprezentált távolabbi
szobatér megőrizte a leállításkori 19,6 °C-ot.

A kültér közben 0,7 °C-kal melegedett, ezért a 0,6 °C-os lecsengés nem vihető
át változatlanul hidegebb időjárásra. A háló hőmérséklete a leállítást követő
órában nem csökkent, és továbbra is 0,2 °C-kal a próba előtti érték fölött van.

Az objektív adatok alapján a 20 perces felfűtés hatása egy órával később is
egyértelműen mérhető. A komfortos időtartam meghatározásához ehhez a ponthoz
még szükséges a szubjektív komfortértékelés, majd a 20,0 és 19,5 °C-os
cselekedeti határ átlépésének követése.

### Komfortértékelés 10:53-kor

- A dolgozó `Zb dolgozó = 19,8 °C`, `CT400 emelet = 19,6 °C`, vagyis 19,7 °C-os
  cselekedeti hőmérséklet mellett továbbra is komfortos.
- A háló 19,0 °C-on már hűvösnek érződik.
- A komfort alsó határának jelenlegi becslése 19,4 °C. A megfigyelést addig
  folytatjuk, amíg a dolgozó cselekedeti átlaga eléri ezt az értéket. Ez még
  mérési küszöb, nem végleges automatikus kapcsolási paraméter.
- A dolgozó és a háló közötti ajtó nyitva van, ezért a két helyiség között
  folyamatos hőcsere történik. Ennek ellenére a dolgozói klíma a hálót csak
  19,0 °C-ig temperálta, ami arra utal, hogy a háló komfortjához saját klímás
  fűtésre is szükség lehet.

### Köztes pont 12:18-kor

- `Zb dolgozó = 19,6 °C` (11:54:37-kor jelentett érték);
- `CT400 emelet = 19,5 °C` (12:15:11);
- számított cselekedeti hőmérséklet: 19,55 °C;
- `Zb háló = 19,0 °C` (11:52:00);
- `Zb ext = 17,3 °C` (12:11:42);
- a dolgozó–kültér különbség a cselekedeti érték alapján kb. 2,25 °C.

A klíma leállítása után mintegy 2 óra 25 perccel a dolgozó még 0,15 °C-kal a
megfigyeléshez választott 19,4 °C-os komfortküszöb fölött van. A lecsengés az
első óra után jelentősen lelassult, ami összhangban van azzal, hogy a kültéri
hőmérséklet 15,1-ről 17,3 °C-ra emelkedett, így a külső–belső különbség már
csak valamivel több mint 2 °C. A mérés folytatódik a 19,4 °C-os cselekedeti
érték eléréséig vagy a komfort korábbi romlásáig.

### Köztes pont 14:14-kor

- `Zb dolgozó = 19,4 °C` (14:01:24-kor jelentett érték);
- `CT400 emelet = 19,5 °C` (14:14:48, soron kívüli lekérdezés);
- számított cselekedeti hőmérséklet: 19,45 °C;
- `Zb háló = 19,0 °C` (13:51:50);
- `Zb ext = 17,9 °C` (14:12:12);
- a dolgozó–kültér különbség a cselekedeti érték alapján kb. 1,55 °C.

A dolgozó a klíma leállítása után több mint 4 óra 20 perccel, 19,45 °C-os
cselekedeti hőmérsékleten továbbra sem kellemetlen. Emiatt a korábban
feltételezett 19,4 °C-os alsó komforthatárt ez a próba nem igazolja; azt el kell
vetni, és a megfigyelést a tényleges szubjektív komfortromlásig kell folytatni.

A kültér ekkorra 17,9 °C-ra melegedett, ezért a belső–külső különbség már csak
kb. 1,55 °C. A dolgozó hőmérséklete emiatt hosszabb időre 19,4–19,5 °C körül
stabilizálódhat. A mai eredmény azt bizonyítja, hogy ilyen enyhe, melegedő
időben a 20 perces felfűtés legalább többórás komfortot ad; hidegebb időre
azonban ebből közvetlenül nem számítható azonos komfortidő.

## Első megfigyelés

A rövid futás végére a dolgozó cselekedeti hőmérséklete 20,3 °C lett, vagyis
közel került a korábban megfelelő komfortot adó 20,5 °C-hoz. A légáramhoz
gyorsabban kapcsolódó Zigbee-hőmérő 1,4 °C-kal többet mutatott a szoba másik
részén levő Computhermnél. Ezért a leállítás pillanata önmagában még nem elég a
végeredmény megítéléséhez: szükséges az egyórás kiegyenlítődés megfigyelése.

## További mérési pontok

Az egyórás pont után a megfigyelést addig érdemes folytatni, amíg a helyiség
már nem komfortos. Külön rögzítendő:

- a szubjektív komfort megszűnésének időpontja;
- a tényleges szubjektív komfortromlás időpontja és az akkori cselekedeti
  hőmérséklet;
- a mindenkori kültéri hőmérséklet, mert a lehűlési idő csak a külső–belső
  különbséggel együtt hasonlítható össze egy későbbi próbával.
