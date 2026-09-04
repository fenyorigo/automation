# Home automation adatbázis dokumentáció

## Cél

Ez a dokumentáció a MariaDB alapú, forrásfüggetlen adatbázis-sémát írja le az
ESP32, ConnectLife, Computherm, Zigbee2MQTT és Shelly MQTT adatok tárolásához.

## Fő elvek

- Minden időbélyeg UTC-ben legyen tárolva.
- A forrást minden rekordnál a `source_system` és a `source_event_id` együtt határozza meg.
- A mérési adatok a `sensor_readings` táblában, az állapotváltozások a `device_states` táblában legyenek.
- A DS18B20 hibás mérésnél `value = NULL`, `quality = 'invalid'` és `error_code` legyen kitöltve.
- A szobákhoz a kanonikus `rooms` tábla tartozzon, a forrásoldali azonosítók a `room_source_refs` táblába.
- A `room_source_refs` kulcsa a forrás-specifikus szobaazonosítóra épül, így egy külső szoba csak egy kanonikus `rooms` rekordhoz tartozhat.
- A hőmérsékleti értékek `DECIMAL(8,4)` formában kerülnek tárolásra a DS18B20 pontosságának megőrzéséhez.
- Az ESP32 hardverazonosítója az eFuse-alapú egyedi azonosítóból vagy MAC-címből származik, és a `devices.source_puid` mezőben kerül tárolásra.
- A `devices.source_device_id` a logikai név, nem a hardverazonosító.
- A DS18B20 gyári 64 bites ROM-azonosítója a `sensors.source_sensor_id` mezőben szerepel, így ugyanaz a fizikai szenzor nem kerülhet kétszer bevezetésre.
- Az ESP32 szobahelye a `devices.room_id` mezőn keresztül jelenik meg, és a hozzá tartozó aktív szenzorok `sensors.room_id` mezőjét is konzisztensen frissíteni kell, ha az ESP32 áthelyezésre kerül.

## Fő táblák

- `rooms`: kanonikus helyiségek
- `room_source_refs`: forrás-specifikus szobaazonosítók
- `devices`: eszközök, például klíma, ESP32 gateway, termosztát
- `sensors`: szenzorok, például DS18B20, ConnectLife beltéri hőmérséklet, Computherm hőmérséklet
- `sensor_readings`: mért értékek idősorokhoz
- `energy_billing_cycles`: mérőnkénti, nem feltétlenül naptári elszámolási ciklusok
- `gas_conversion_periods`: időben érvényes korrekciós tényező és fűtőérték
- `energy_tariff_periods`: kedvezményes és versenypiaci energia-egységárak
- `energy_allocation_rules`: szolgáltatói részszámlák becsült díjsávmegosztásai
- `energy_entitlement_periods`: az augusztus 1.–július 31. közötti kedvezményes
  gázjogosultsági évek MJ-kerete és tájékoztató m³-mennyisége
- `energy_fixed_charge_periods`: becsléshez használt, fogyasztástól független díjak
- `energy_invoice_charge_defaults`: időben hatályos, új részszámlára
  automatikusan másolt alapdíj- és szolgáltatássablonok
- `energy_invoices`: szolgáltatói számlafejek, számlaszintű kerekítés és
  fizetendő összegek
- `energy_invoice_consumption`: a számlán szereplő becsült vagy tényleges fogyasztási sorok
- `energy_invoice_charge_lines`: a számla energia-, alapdíj-, szolgáltatás- és
  korrekciós tételei, külön `rate`/`exempt` adózási jelöléssel és opcionális
  törzsadat-kapcsolattal
- `energy_invoice_settled_installments`: az elszámolószámlán felsorolt
  részszámlák szolgáltatói száma, végösszege és opcionális kapcsolata a már
  rögzített részszámlához
- `sensor_calibrations`: az ESP–DS fizikai kialakításának és kalibrációjának
  időben verziózott története
- `derived_temperature_readings`: ofszetkompenzált, EMA-szűrt és ritkábban
  publikált cselekedeti hőmérsékletek
- `derived_temperature_sources`: a származtatott értékek pontos forráslánca
- `device_states`: eszközállapotok, például üzemmód, be-/kikapcsolás, ventilátorsebesség
- `deterministic_reports`: kereshető, időbélyegzett automatikus jelentések,
  verziózott szabályokkal, bizonyítékokkal és az eredeti ténycsomaggal

## MQTT-források

A Shelly H&T Gen3 a meglévő általános táblákat használja, új Shelly-specifikus
tábla nélkül. Egy készülékhez egy `devices` rekord és négy `sensors` csatorna
tartozhat: `temperature`, `humidity`, `battery`, `battery_voltage`. Minden élő
MQTT-jelentés külön `sensor_readings` sort hoz létre; nem kell a külön topicokon
érkező értékeket egyetlen mintává összevárni.

A retained Shelly-üzenetek stabil topic+payload hash-alapú eseményazonosítót
kapnak. Élő üzenetnél az érkezési idő része a `source_event_id`-nak, így azonos
érték ismételt jelentése is megmarad.

A Zigbee2MQTT minden tulajdonságának legutolsó értéke a
`zigbee2mqtt_property_cache` táblában marad. A temperature, humidity és battery
tulajdonságok ezen felül a közös `sensor_readings` idősorba is bekerülnek. A
forrásoldali `last_seen` idő és az IEEE-cím stabil eseményazonosítást biztosít.

## Kalibrált és cselekedeti hőmérséklet

A `sensor_readings` nyers értékei változatlanok. Származtatott érték csak olyan
ESP32-hőmérőhöz készül, amelynek az adott időpontban érvényes
`copper_tube_box` konfigurációja és bekapcsolt `decision_enabled` jelzője van.
Az additív ofszet után az EMA minden sikeres mintával frissül. A cselekedeti
érték azonban csak az `action_interval_seconds` idő leteltekor jelenik meg; az
alapértelmezett időállandó és publikálási időköz egyaránt 240 másodperc.

## Seed fájlok

- [SQL/home_automation_schema_v1.0_20260807.sql](../../SQL/home_automation_schema_v1.0_20260807.sql)
- [SQL/seed_home_automation_v1.0_20260807.sql](../../SQL/seed_home_automation_v1.0_20260807.sql)

## Alapvető használat

1. Futtassuk a séma SQL-fájlt.
2. Futtassuk a seed SQL-fájlt.
3. A későbbi collectorok a `source_event_id` konvenciót kövessék.

## `source_event_id` formátum

A javasolt formátum:

`{source_system}:{source_device_id_or_sensor_id}:{measurement_or_state}:{source_timestamp}`

Példa:

`esp32:esp32-d1-mini-01:ds18b20:20260807T123456789Z`
