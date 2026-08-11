# Determinisztikus napi elemzés és lokális AI

## Alapelv

A fűtési és hűtési vezérlés determinisztikus marad. A lokális nyelvi modell
nem kap közvetlen hozzáférést az eszközökhöz és nem módosíthat célértéket,
időprofilt vagy biztonsági korlátot. Feladata kizárólag az előre kiszámított,
strukturált tények emberileg olvasható megfogalmazása.

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
6. Opcionális Ollama-hívás kizárólag a ténycsomaggal.
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
OLLAMA_MODEL=llama3.2:1b
OLLAMA_TIMEOUT_SECONDS=60
```

Az `/analysis` oldal ettől függetlenül, két másodperces időkorláttal lekéri az
Ollama `/api/tags` végpontját. Külön jelzi a szolgáltatás tényleges
elérhetőségét és azt, hogy a konfigurált modell szerepel-e a telepített
modellek között.

A modell engedélyezése előtt még implementálandó a determinisztikus napi
pipeline, a validátor, az ütemezés, a hibakezelés és a Fedora-szolgáltatás.
Ollama telepítése vagy modell letöltése ebben az előkészítő fázisban nem
történik.
