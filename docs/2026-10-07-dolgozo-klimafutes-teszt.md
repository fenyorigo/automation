# Dolgozószobai klímafűtési próba – 2026. október 7.

## Cél

Az első kontrollált őszi klímafűtési próba célja annak megfigyelése volt, hogy
a dolgozószobai Hisense klíma egyórás, közepes ventilátorfokozatú fűtése:

- milyen gyorsan emeli a dolgozó különböző pontjain mért hőmérsékletet;
- a nyitott, 90 × 210 cm tokméretű ajtón keresztül mennyire temperálja a hálót;
- milyen gyorsan cseng le a hatása a kikapcsolás után;
- milyen kapcsolat van a mért értékek és a szubjektív hőérzet között.

Ez egyszeri próba, ezért az eredménye még nem végleges vezérlési szabály.

## Beállítás és adatforrások

- Klíma: `HS dolgozó`, Hisense Energy SE KA35XR0E.
- Üzemmód: fűtés.
- Kért célhőmérséklet: 22 °C.
- Ventilátor: közepes.
- A dolgozó és a háló közötti ajtó végig nyitva volt.
- A klíma indulásakor körülbelül 2 perc előfűtés előzte meg a légáram
  megindulását.
- Kikapcsolás után az utófutás körülbelül 30 másodpercig tartott.
- A klímát kézzel, a Hisense alkalmazásból kapcsoltuk ki.

Felhasznált hőmérsékletforrások:

- `Zb dolgozó`: a klíma légáramára gyorsan reagáló helyiségi Zigbee-hőmérő;
- `CT400 emelet`: a dolgozó másik részén levő Computherm;
- `Zb háló`: a nyitott ajtón keresztüli temperálás megfigyelése;
- `Zb ext`: kültéri referencia.

A dolgozó fűtési cselekedeti hőmérséklete a jelenlegi szabály szerint a
`Zb dolgozó` és a `CT400 emelet` 50–50%-os átlaga. A Hisense saját, magasan és
saját légáramában levő hőmérője nem vezérlési alap.

## Időzítés és állapot-visszaolvasás

Az automation 09:09:55-kor észlelte a klíma bekapcsolását. Az első észlelt
állapot átmenetileg 23 °C és automatikus ventilátor volt; 09:20:07-től minden
periodikus visszaolvasás 22 °C-os célértéket és közepes ventilátort mutatott.
Ezért a bekapcsolás utáni legelső tíz perc pontos parancsállapota nem teljesen
rekonstruálható, a próba döntő része azonban igazoltan a tervezett beállítással
futott.

A kézi kikapcsolás körülbelül 10:13-kor történt. A tízperces Hisense-polling
10:21:13-kor észlelte először a kikapcsolt állapotot, ezért az automatikusan
naplózott 71 perces eseményhossz nem azonos a tényleges, körülbelül 63 perces
fűtési idővel.

## Három összehasonlítási pont

Az időpontok Europe/Budapest helyi idő szerint értendők. A Zigbee eszközök
változásvezérelten jelentenek, ezért az értékekhez a tényleges MQTT-mérési
időpontot őrizzük meg; nem tekintjük őket mesterségesen egyidejűnek.

| Forrás | Indulási érték | Kikapcsolás / utófutás vége | Egyórás utánmérés |
|---|---:|---:|---:|
| Zb dolgozó | 18,6 °C (09:13:34) | 22,8 °C (10:11:13) | 20,2 °C (11:08:37) |
| CT400 emelet | 18,4 °C (09:14:45) | 20,6 °C (10:15:26) | 19,9 °C (11:14:19) |
| Dolgozó cselekedeti | 18,5 °C | 21,7 °C | 20,05 °C |
| Zb háló | 18,0 °C (09:14:36) | 19,0 °C (10:14:44) | 18,8 °C (11:00:55) |
| Zb ext | 11,3 °C (09:06:22) | 13,3 °C (10:12:14) | 15,3 °C (11:04:29) |

### Változások

| Forrás | Felfűtés alatti változás | Leállítás utáni változás | Teljes nettó változás |
|---|---:|---:|---:|
| Zb dolgozó | +4,2 °C | −2,6 °C | +1,6 °C |
| CT400 emelet | +2,2 °C | −0,7 °C | +1,5 °C |
| Dolgozó cselekedeti | +3,2 °C | −1,65 °C | +1,55 °C |
| Zb háló | +1,0 °C | −0,2 °C | +0,8 °C |
| Zb ext | +2,0 °C | +2,0 °C | +4,0 °C |

A közel egyórás szakaszokra vetített, csak tájékoztató meredekség:

- `Zb dolgozó`: felfűtéskor kb. +4,4 °C/óra, utána kb. −2,7 °C/óra;
- `CT400 emelet`: felfűtéskor kb. +2,2 °C/óra, utána kb. −0,7 °C/óra;
- `Zb háló`: felfűtéskor kb. +1,0 °C/óra, utána kb. −0,3 °C/óra.

Ezek nem épületfizikai állandók: a napsütés és a folyamatosan emelkedő kültéri
hőmérséklet is befolyásolta őket.

## Külső–belső különbség

| Mérési pont | Dolgozó cselekedeti − kültér | Háló − kültér |
|---|---:|---:|
| Indulás | 7,2 °C | 6,7 °C |
| Leállítás | 8,4 °C | 5,7 °C |
| Egy órával később | 4,75 °C | 3,5 °C |

A lecsengés idején a kültér további 2 °C-ot melegedett. Emiatt a dolgozó
lassuló visszahűlése nem tulajdonítható kizárólag a helyiség hőtárolásának:
közben jelentősen csökkent a kifelé irányuló hőmérséklet-különbség is. Egy
hidegebb vagy állandó kültéri hőmérsékletű napon gyorsabb lecsengés is
lehetséges.

## Érzékelők és hőeloszlás

A `Zb dolgozó` a felfűtés végén 2,2 °C-kal mutatott többet a Computhermnél.
Ez nem egyszerű mérési ofszet: a klíma légáramában levő Zigbee gyorsan követte
a befújt meleget, míg a szoba másik részén levő Computherm a helyiség lassabban
melegedő tömegét reprezentálta. A leállítás után egy órával az eltérés már csak
0,3 °C volt. Ez erősen igazolja a két mérés átlagára épülő cselekedeti
hőmérséklet használatát.

A háló a nyitott ajtó ellenére csak 1,0 °C-ot melegedett, miközben a dolgozó
cselekedeti értéke 3,2 °C-kal nőtt. A dolgozói klíma tehát érzékelhetően
temperálja a hálót, de gyors és egyenletes hálófűtésre önmagában nem alkalmas.
A leállítás után a háló még egy órával is 0,8 °C-kal volt a kiindulási érték
felett.

## Komfortmegfigyelések

Két szubjektív megfigyelés különösen fontos:

1. Az egyórás, végig közepes ventilátoros működés már a vége előtt túl meleg
   hőérzetet okozott.
2. A légáram megszűnése után a hőérzet azonnal megfelelővé vált, majd kb.
   10:58-kor `CT400 emelet = 20,0 °C`, `Zb dolgozó = 20,4 °C`, vagyis kb.
   20,2 °C-os cselekedeti hőmérséklet mellett továbbra is jó maradt.

Ez azt jelzi, hogy a kellemetlenséget nem pusztán a levegő átlaghőmérséklete,
hanem a tartós meleg légáram is okozta. A következő stratégiai változtatás
elsősorban a ventilátorfokozat időbeni visszavétele legyen, ne a célhőmérséklet
folyamatos változtatása.

## Előzetes vezérlési következtetés

Az egyórás, állandó közepes fokozat nem alkalmas üzemszerű alapbeállításnak.
A következő teszt javasolt menete:

1. **Felfűtés:** fűtés mód, változatlan 22 °C-os célérték, közepes ventilátor.
2. **Korai átváltás:** legfeljebb 15–25 perc után, vagy amikor a dolgozó
   cselekedeti hőmérséklete eléri hozzávetőleg a 19,5–20,0 °C-ot, váltás
   automatikus ventilátorra.
3. **Tartás:** a célérték maradjon 22 °C; először az automatikus fokozatot kell
   kipróbálni. A csendes mód külön komfortteszt tárgya legyen.
4. **Leállítás vagy további visszavétel:** a cselekedeti hőmérséklet,
   hiszterézis és komfortmegfigyelés alapján, nem kizárólag a légáramhoz közeli
   Zigbee csúcsértéke szerint.

A 15–25 perces és 19,5–20,0 °C-os javaslat tesztelési kiindulópont, nem kész
automatizálási szabály. A következő próbán külön kell mérni, hogy automatikus
ventilátorra váltva a Computherm tovább közelít-e a Zigbee-hez anélkül, hogy a
közvetlen légáram ismét kényelmetlenné válna.

## Korlátok

- Egyetlen, napsütéses délelőtti mérés történt.
- A kültéri hőmérséklet a teljes megfigyelés alatt 4 °C-ot emelkedett.
- A Zigbee mérések változásvezéreltek, ezért a három összehasonlítási pont nem
  minden forrásnál pontosan azonos időpontú.
- A Hisense első visszaolvasott célértéke és ventilátorállapota eltért a próba
  tervezett beállításától; 09:20-tól azonban konzisztensen 22 °C és közepes
  ventilátor szerepelt.
- A próba nem tartalmazott villamosenergia-mérést és nem hasonlította össze a
  gázfűtés költségével vagy hatásfokával.

