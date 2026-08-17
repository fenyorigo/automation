# Determinisztikus elemzés és automatikus jelentések

## Alapelv

A számítás, minősítés és szövegalkotás Pythonban, verziózott szabályokkal
történik. A rendszer nem használ nyelvi modellt, ezért minden mondat pontosan
visszavezethető a felhasznált adatokra és a szabályra. A jelentéskészítő nem
kap eszközvezérlési jogosultságot.

## Feldolgozási folyamat

1. A felhasználó kijelöl egy legfeljebb hét napos időablakot.
2. Olvasási lekérdezések összegyűjtik a hőmérsékleteket, külső referenciákat,
   klíma- és szellőztetési eseményeket.
3. A Python szenzoronként kiszámítja a mérési darabszámot, minimumot,
   maximumot, átlagot, nettó változást és a legerősebb csökkenést.
4. Verziózott szabályok készítik el az állításokat és azok minősítését.
5. Rögzített magyar sablonok állítják össze a jelentésszöveget.
6. A jelentés, minden szabály bizonyítéka és az eredeti ténycsomag bekerül az
   adatbázisba.

Az első generátorverzió: `deterministic-v1`.

## Adattárolás

A `deterministic_reports` tábla tárolja:

- a jelentési időablakot;
- a generátorverziót és az összesített `info`, `warning` vagy `critical`
  minősítést;
- a címet és a teljes jelentésszöveget;
- a szabályonkénti `rule_id`, `severity`, `message` és `evidence` mezőket;
- a teljes bemeneti ténycsomagot;
- az opcionális kézi megfigyelést;
- a készítő felhasználót és a létrehozási időbélyeget.

Az Elemzések oldalon a jelentések szabad szöveggel, minősítéssel és
létrehozási dátumtartománnyal kereshetők. A kézi megfigyelés kereshető, de
bizonyítéktípusa mindig `manual`.

## Első szabálykészlet

- `temperature_coverage_v1`: értékelt szenzorok és mérési pontok száma;
- `sensor_window_statistics_v1`: szenzoronkénti ablakstatisztika;
- `outdoor_reference_v1`: a külső szolgáltatói adat kizárólag tájékoztató
  referenciaként;
- `environmental_events_v1`: átfedő klíma- és szellőztetési események;
- `common_esp32_drop_v1`: legalább három ESP32 közös csökkenéseinek összegzése;
- `operator_observation_v1`: elkülönített kézi megfigyelés.

Az első verzió óvatos: mérési eltérésből nem talál ki okot, és nem minősít
hibának olyan változást, amelyet klíma, szellőztetés vagy más környezeti esemény
is magyarázhat.

## Korábbi Llama-kísérlet

A Llama 3.2 1B modellt korábban kötött JSON-sémával és validátorral próbáltuk.
Nem különítette el kellő megbízhatósággal a bizonyított tényt és az értelmezést,
ezért a modellt eltávolítottuk, az Ollama-integrációt pedig kivezettük. A régi
`ai_analysis_experiments` rekordok auditcélból az adatbázisban maradhatnak, de
az aktív alkalmazás nem használja őket.
