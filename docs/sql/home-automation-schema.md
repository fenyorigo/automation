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
- `thermostat_service_tests`: visszaállítható Computherm szerviztesztek eredeti és legutóbbi állapota
- `thermostat_service_commands`: a szerviztesztek parancs- és visszaolvasási auditnaplója
- `computherm_schedule_changes`: a CT400 heti programjának kért, írás előtti
  és visszaellenőrzött állapotát, valamint a sikeres és sikertelen módosításokat
  felhasználóhoz és eszközhöz kötve őrző auditnapló
- `computherm_clock_syncs`: az automatikus CT400-órakorrekciók észlelt
  eltérését, küszöbét, írás előtti és visszaellenőrzött állapotát, valamint a
  sikeres és sikertelen szinkronizálásokat őrző auditnapló
- `climate_control_attempts`: a közvetlen, időzített és szervizcélú
  ConnectLife-parancsok auditja; a `requested_mode` a kért üzemmódot is megőrzi.
  A közvetlen UI-parancsoknál az `execution_phase`, `started_at` és
  `phase_updated_at` mezők tartós végrehajtási sort és köztes állapotjelzést
  biztosítanak; a `verified_state` a legutóbbi visszaolvasást is tartalmazhatja.
- `device_power_control_attempts`: a dedikált kapcsolható dugaljak kézi vagy
  ütemezett kapcsolási kérései, opcionális kérő felhasználója, `ui`/`schedule`
  eredete, előzetes és visszaigazolt reléállapota, valamint hibája
- `boiler_mode_state_events`: a Bosch kézzel rögzített melegvíz- és
  fűtésállapotának időbélyeges változásai
- `sensor_readings`: mért értékek idősorokhoz

A kontaktusérzékelők `devices.opening_role` mezője választja szét a külső,
blokkoló/szellőztető (`external`) és a belső, nem blokkoló (`internal`)
nyílászárókat. Belső ajtónál a `room_id` az egyik, a
`connected_room_id` a másik helyiséget azonosítja; a két helyiség nem lehet
azonos, és a nyilvántartási felület azonos zónát követel meg.
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
- `energy_invoice_consumption`: a számlán szereplő becsült vagy tényleges,
  `m3` vagy `kWh` egységű fogyasztási sorok; a korrekciós és fűtőértékmezők
  csak gáznál használatosak
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
- `ventilation_events`: kézzel vagy Zigbee nyitásérzékelővel indított,
  helyiségszintű szellőztetések időintervalluma és külsőhőmérséklet-pillanatképei

Az `energy_invoices` opcionálisan a számlán szereplő szolgáltató/számlázási
rendszer nevét, felhasználóazonosítót és szerződéses folyószámlát is megőrzi.
Ez visszakereshetővé teszi a 2026. május 31-i villanyszámla-zárás utáni
számlázási átállást anélkül, hogy a fizikai A1 mérőt lecserélnénk.

A villanyszámlák ugyanazt a számlamodellt használják, mint a gáz. A
fogyasztási részletek kWh-ban tárolják az A1 mérő szolgáltatói állásait. A
régi összevont rendszerhasználati díj, az új átviteli és elosztói díj, továbbá
az elszámolt részszámlák rendszerhasználati jóváírása külön díjkategória. A
használaton kívüli vezérelt mérő fogyasztási idősor nélkül, kizárólag a
számlán ténylegesen felszámított alapdíjsorral jelenik meg.

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
tulajdonságok, továbbá a TRV-ZBT `local_temperature`,
`occupied_heating_setpoint`, `heating_valve_position` és
`heat_percentage_hour` tulajdonságai ezen felül a közös `sensor_readings`
idősorba is bekerülnek. A forrásoldali `last_seen` idő és az IEEE-cím stabil
eseményazonosítást biztosít.
A bináris `contact` csatorna ugyanebbe a táblába csak induló állapotként és
valódi változáskor kerül (`0 = nyitva`, `1 = csukva`), nem ismétlődő
pillanatképként.

A `ventilation_events.event_origin` elkülöníti a `manual` és a
`zigbee_contact` eredetet. Automatikus eseménynél a kezdő és lezáró eszköz is
hivatkozható, a `pending_end_at` a még visszaellenőrzés alatt álló csukást
jegyzi. A `long_threshold_seconds` az esemény létrejöttekor érvényes rövid/hosszú
határt őrzi, ezért a globális alapérték későbbi módosítása nem osztályozza át a
történeti eseményeket.

## Kalibrált és cselekedeti hőmérséklet

A `sensor_readings` nyers értékei változatlanok. Származtatott érték csak olyan
ESP32-hőmérőhöz készül, amelynek az adott időpontban érvényes
`copper_tube_box` konfigurációja és bekapcsolt `decision_enabled` jelzője van.
Az additív ofszet után az EMA minden sikeres mintával frissül. A cselekedeti
érték azonban csak az `action_interval_seconds` idő leteltekor jelenik meg; az
alapértelmezett időállandó és publikálási időköz egyaránt 240 másodperc.

## Időjárás-előrejelzések

A háromnapos Open-Meteo-előrejelzés nem keveredik a tényleges kültéri
mérésekkel. Az `outdoor_weather_forecast_runs` egy lekérés metaadatait és
eredeti payloadját, az `outdoor_weather_forecast_points` annak 72 órás pontjait
tárolja. Egy ponthoz az érvényességi idő mellett a lekéréskori előrejelzési
horizont is megmarad, ezért később külön mérhető a rövid és hosszabb távú
prognózis hibája. Az `outdoor_weather_forecast_poll_attempts` a gyűjtés
sikerességét auditálja. A tényleges összehasonlítás alapja továbbra is az
`outdoor_temperature_observations`, elsődlegesen a saját Zigbee kültéri
hőmérővel.

## ENTSO-E / HUPX másnapi villamosenergia-árak

Az `electricity_day_ahead_price_runs` a magyar ajánlattételi zóna egy-egy
ENTSO-E A44 dokumentumának vagy HUPX-tartaléklekérésének metaadatait,
normalizált tartalmi SHA-256 lenyomatát és eredeti XML/JSON válaszát őrzi. A
`source_code` megkülönbözteti az `entsoe` és `hupx` forrást. Azonos forrásból az
azonos publikált görbe csak egyszer tárolható,
míg egy valódi
revízió külön futás marad. Az `electricity_day_ahead_price_points` a dokumentum
15 perces — az API régebbi vagy eltérő felbontása esetén általánosan kezelt —
intervallumait és EUR/MWh árait tárolja UTC idővel. A
`electricity_day_ahead_price_poll_attempts` minden sikeres, még nem publikált
és hibás próbálkozást külön auditál. A szállítási nap budapesti helyi nap,
ezért az óraátállítás 23 és 25 órás napjai nem kényszerülnek 24 órára.

Az MNB hivatalos napi EUR/HUF középárfolyamát a
`currency_exchange_rate_observations` őrzi a forrás dátumával, lekérési idővel,
eredeti SOAP-válasszal és SHA-256 lenyomattal. A
`currency_exchange_rate_poll_attempts` a napi próbálkozások auditnaplója. A
következő szállítási nap előnézete mindig az addig elérhető legutóbbi, a
szállítási napnál nem későbbi árfolyamot használja; új MNB-adat beérkezésekor a
számított ár automatikusan pontosodik.

Az `electricity_dynamic_tariff_parameters` a D árszabás időben hatályos
kereskedői díját és ÁFA-kulcsát tárolja. A kezdeti rekord 2026. szeptember
10-től `13,7000 Ft/kWh` nettó kereskedői díjat és 27% ÁFÁ-t rögzít. A
negyedórás nettó és bruttó D energiadíj származtatott adat, ezért nem
duplikáljuk az adatbázisban: a nyers HUPX-ár, az adott napi MNB-árfolyam és az
adott napon hatályos paraméter alapján újraszámítható.

A `trv_setting_requests` a kézzel kiadott SONOFF TRV Gen2 PID-, gyerekzár- és
szelepállás-kéréseket őrzi. A `pending` állapot a kiküldött, de cache-ből még
nem igazolt parancs, a `verified` a visszaolvasott egyezés, az `expired` a
30 percen belül meg nem erősített kérés, a `failed` pedig a bizonyított
parancsküldési hiba. A kért és – ha rendelkezésre áll – a visszaolvasott
állapot JSON-ként megmarad.

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
