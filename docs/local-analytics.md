# Determinisztikus elemzés és a lokális AI-kísérlet tapasztalatai

## Alapelv

A fűtési és hűtési vezérlés determinisztikus marad. Nyelvi modell nem kaphat
közvetlen hozzáférést az eszközökhöz, és nem módosíthat célértéket, időprofilt
vagy biztonsági korlátot. Egy későbbi, alkalmas modell feladata is legfeljebb az
előre kiszámított, strukturált tények emberileg olvasható megfogalmazása lehet.

Egy kis modell használata csökkenti az erőforrásigényt, de önmagában nem zárja
ki a hallucinációt. A későbbi megvalósítás ezért minden számszerű és eszközre
vonatkozó állítást visszaellenőriz a determinisztikus tényhalmaz ellen. Sikertelen
ellenőrzés esetén a modell válasza `rejected`, és sablonalapú `fallback`
összefoglaló készül.

## Feldolgozási folyamat

1. Az előző helyi nap nyers méréseinek és eszközállapotainak lezárása.
2. Adatminőség-ellenőrzés: hiány, elavulás, beragadt érzékelő, érvénytelen adat.
3. Szenzoronkénti napi statisztikák és változási sebességek számítása.
4. Lokalizált z-pontszámú és szabályalapú anomáliák létrehozása.
5. Ellenőrzött, strukturált ténycsomag előállítása.
6. Opcionális, jelenleg kikapcsolt szövegmodell-hívás kizárólag a ténycsomaggal.
7. A válasz állításainak validálása; szükség esetén determinisztikus tartalék.
8. Az eredmény megjelenítése, emberi döntésre bízva minden javaslatot.

## Előkészített táblák

- `analysis_runs`: napi futások, verzió, állapot és hiba;
- `daily_sensor_metrics`: determinisztikus napi szenzormutatók;
- `anomaly_events`: típus, súlyosság, időablak, z-pontszám és bizonyíték;
- `daily_ai_summaries`: modell, promptverzió, bemeneti tények, szöveg és
  validációs állapot.

A `validated_facts` és az `evidence` JSON megmarad az AI-szöveg mellett, ezért
az összefoglaló utólag auditálható és újragenerálható.

## Konfiguráció

Az Ollama alapértelmezetten ki van kapcsolva:

```text
OLLAMA_ENABLED=false
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=
OLLAMA_TIMEOUT_SECONDS=60
```

Az első modellalkalmassági vizsgálat után a Llama 3.2 1B modellt eltávolítottuk.
Az `/analysis` oldal jelzi, hogy az Ollama ki van kapcsolva és nincs telepített
szövegmodell. Az Ollama az UI-ból nem engedélyezhető; az elemzési ténycsomagot
a determinisztikus Python-folyamat továbbra is el tudja készíteni.

## Kézi bizonyítékcsomag-kísérlet

Az `/analysis` oldalon szerkesztői jogosultsággal tetszőleges, legfeljebb hét
napos időablak elemezhető. A Python csak olvasási lekérdezésekkel kapcsolja
össze a méréseket, szellőztetést, klímaeseményeket és külső hőmérsékletet.
A teljes ténycsomag auditálásra megmarad. Jelenleg nem kerül szövegmodellhez;
SQL-t csak az alkalmazás olvasási folyamata futtat, eszközvezérlés nem történik.

A korábbi kísérleteknél a prompt, a kézi megfigyelés, a nyers modellválasz és a validálási eredmény az
`ai_analysis_experiments` táblába kerül. A validátor ellenőrzi a JSON-sémát,
a bizonyítékhivatkozásokat, az üres és ismétlődő állításokat, továbbá megtiltja,
hogy a kézi megfigyelés bizonyított műszeres tényként szerepeljen.

## A Llama 3.2 1B kísérlet eredménye

A modellt szándékosan szűk feladattal próbáltuk: nem nyers adatbázis-hozzáférést
kapott, hanem Pythonból előállított, strukturált bizonyítékcsomagot, kiegészítve
egy elkülönítetten jelölt emberi megfigyeléssel. A választ kötött JSON-séma és
bizonyítékhivatkozások alapján ellenőriztük.

A próbák során a modell:

- összekeverte a mért tényt a valószínű értelmezéssel;
- ismételt vagy egymást átfedő állításokat adott;
- nem mindig emelte ki a több érzékelőn egyszerre megjelenő, fontos eseményt;
- a kötött szerkezet ellenére sem adott megbízhatóan validálható választ.

Ezért a válaszok `rejected` állapotúak lettek. A tapasztalat szerint az egymilliárd
paraméteres modell erre a feladatra nem alkalmas; a validáció lazítása csak
elfedné a hibát. A `llama3.2:1b` modellt töröltük, az Ollamát programból
kényszerítetten kikapcsoltuk, és az UI-ból nem engedélyezhető.

## Jelenlegi működés és továbblépési feltétel

A modell eltávolítása nem érinti az adatgyűjtést, a statisztikai számításokat,
az anomáliaészlelést vagy a bizonyítékcsomag elkészítését; ezeket Python végzi.
Az Elemzések oldal kifejezetten jelzi, hogy nincs telepített szövegmodell.

Új modell csak külön alkalmassági vizsgálat után kerülhet használatba. Ugyanazt
a rögzített ténycsomagot, sémát és szigorú validátort kell teljesítenie. A modell
akkor sem válhat döntési vagy vezérlési komponenssé: hibás válasz esetén az
alkalmazás determinisztikus, sablonalapú összefoglalóra tér vissza.
