# Nous/Tasmota fogyasztásmérők

Az alkalmazás a Tasmota firmware-t futtató Nous okosdugaljakat közvetlen HTTP-
lekérdezéssel kezeli; ezeknél az MQTT nem része az adatútnak. A periodikus
lekérdezés önmagában nem kapcsolja a relét és nem módosítja az eszköz
konfigurációját. Kézi kapcsolás a `nous-kazan` és a `nous-bojler` kezdőlapi
kártyájáról indítható szerkesztőként.

## Nyilvántartott eszközök

| Technikai azonosító | Cím | Feladat |
|---|---|---|
| `nous-mainit` | `192.168.0.44` | fő informatikai infrastruktúra |
| `nous-auxit` | `192.168.0.45` | dolgozószobai kiegészítő informatikai infrastruktúra |
| `nous-kazan` | `192.168.0.46` | Bosch 7000i tápellátásának felügyelete |
| `nous-bojler` | `192.168.0.47` | 1,8 kW-os villanybojler tápellátása, fogyasztásmérése és időzítése |

A címeket statikus DHCP-foglalás biztosítja. Az alkalmazásban hostnév
használandó, hogy a címzés központilag, a helyi DNS-ben maradjon kezelhető.

## Lekérdezés

A Tasmota HTTP API olvasási végpontja:

```text
http://<hostnév>/cm?cmnd=Status%200
```

Az alkalmazás az alábbi idősorokat tárolja:

- pillanatnyi hatásos teljesítmény (`W`);
- látszólagos teljesítmény (`VA`);
- meddő teljesítmény (`var`);
- teljesítménytényező;
- feszültség (`V`);
- áram (`A`);
- összes, mai és tegnapi energia (`kWh`).

Az összes energia méréséhez a Tasmota `TotalStartTime` mezője is megmarad.
A kezdőlapi eszközkártyán ezért az összes kWh alatt az is látható, hogy az
összegzés mikor kezdődött. A relé állapota és az, hogy van-e pillanatnyi
terhelés, két külön adat.

## Feszültségkalibráció

A kalibráció előtt megbízható multiméterrel, ugyanazon hálózati ponton kell
referenciafeszültséget mérni. A Tasmota konzoljában a mért érték adható meg:

```text
VoltageSet 230
```

A parancs nem egyszerű kijelzési korrekció: a Tasmota ebből új
kalibrációs tényezőt számít. A beállítás után ismét össze kell vetni a Tasmota
feszültségét a multiméterrel.

A rögzített kalibrációs beállítások:

| Eszköz | Referencia | `VoltageCal` változás |
|---|---:|---:|
| `nous-auxit` | 230 V | 1950 → 1522 |
| `nous-mainit` | 226 V | → 1454 |
| `nous-kazan` | 235,5 V | 1950 → 1498 |
| `nous-bojler` | 235 V | 1950 → 1515 |

A `nous-kazan` 2026. szeptember 11-i kalibrációja előtt a Tasmota 306 V-ot,
utána egész voltos felbontással 235 V-ot jelzett. A kalibráció idején a relé
bekapcsolt, a Bosch nyugalmi fogyasztása 5 W volt.

Ez kizárólag a feszültségcsatorna kalibrációja. A teljesítmény- és
energiamérés pontosságának ellenőrzéséhez ismert, lehetőleg közel ohmos
terhelés és külön referencia teljesítménymérő szükséges. Terhelés nélküli
állapotból a teljesítménykalibráció nem állapítható meg.

A `nous-bojler` első felfűtési ciklusában a még gyári `PowerCal=12530`
`2231–2297 W` teljesítményt jelzett, miközben az egyidejű feszültség- és
áramértékek szorzata `1,81–1,88 kW` volt. Stabil, tisztán ellenállásos
terhelésnél a `PowerSet 1870` paranccsal a végleges érték `PowerCal=10132` lett;
utána a kijelzés `1862–1875 W` között stabilizálódott. A kalibráció előtti
135 mérési sort töröltük, az eszköz napi és összes energiaértéke pedig
2026. szeptember 23-án 08:33:37-kor új, nulláról induló mérési életet kezdett.
Az előző adatállapot mentése:
`/var/backups/automation/home_automation_before_nous_bojler_measurement_reset_20260923T0832CEST.sql.gz`.

## Villanybojler időzítése

A `nous-bojler` napi tápablakának egyetlen igazságforrása az automation.
A Tasmota saját időzítői kikapcsolva maradnak. A Globális beállítások között
állítható az ütemezés engedélyezése, a bekapcsolási idő és a kikapcsolási idő;
az alapérték minden nap `05:00–12:00`.

A poller legfeljebb egyperces ciklusban közvetlen HTTP-állapotolvasással
egyezteti a relét a kívánt állapottal. Ha a szerver vagy a dugalj a kapcsolási
időpontban nem volt elérhető, a kapcsolat helyreállása után a soron következő
egyeztetés állítja be a helyes állapotot. A kézi UI-kapcsolás megmarad, de aktív
ütemezés mellett csak átmeneti: az automation visszaállítja az időablak szerinti
állapotot. A tényleges automatikus kapcsolások és a hibák a
`device_power_control_attempts` táblába kerülnek `schedule` eredettel.

## Üzemeltetési megjegyzések

- A `nous-mainit` kritikus hálózati eszközöket táplál; kapcsolása az egész
  helyi infrastruktúrát leállíthatja.
- A `nous-bojler` 1,8 kW-os névleges terhelése 235 V mellett kb. 7,7 A. A
  fizikailag 16 A-es A1T ehhez megfelelő tartalékkal rendelkezik; az első
  teljes felfűtési ciklus alatt az aljzat és a csatlakozó melegedését ellenőrizni
  kell.
- A `nous-kazan` bekapcsolása közvetlenül kérhető. A kikapcsolás első
  gombnyomása még nem
  küld parancsot: piros következményjelzés jelenik meg, és csak az öt percig
  érvényes második megerősítés hajtja végre a kapcsolást.
- A Nous relé igazolt állapota a Bosch tápellátási jelzését is frissíti, és
  változáskor `manual_state_events` bejegyzést készít. Kikapcsoláskor a kézzel
  nyilvántartott melegvíz és fűtés is inaktív lesz; ezek változását a
  `boiler_mode_state_events` őrzi. Visszakapcsoláskor csak a tápellátás válik
  aktívvá, a melegvíz- és fűtésjelzést külön kell megadni.
- Minden kapcsolási kísérlet, kérő felhasználó és visszaellenőrzött eredmény a
  `device_power_control_attempts` táblába kerül.
- A `nous-mainit`, `nous-auxit` és a Zigbee router-dugaljak az UI-ból nem
  kapcsolhatók; ezek továbbra is csak megfigyelhetők.
- A `nous-kazan` a hűtés–fűtés vezérlésben részt vevő eszközök alapnézetében
  is megjelenik. A relé bekapcsolt állapota csak a Bosch tápellátását jelenti;
  nem bizonyítja, hogy a kazánon a melegvíz vagy a fűtés engedélyezve van.
- A `nous-kazan` 2026. szeptember 10-i első lekérdezésekor a relé bekapcsolt,
  a kikapcsolt Bosch panel terhelése 0 W volt. A rövid kézi próba alatt az
  indulási értékek 23, 122 és 74 W, a bekapcsolt panel nyugalmi értéke stabilan
  5 W volt. A kijelzett 301–304 V nyilvánvaló kalibrációs hiba, ezért a
  feszültség- és energiaadatok üzemszerű használata előtt külön kalibráció kell.
- Bekapcsolt Nous esetén a Bosch saját power kapcsolóját a friss valós
  teljesítményből származtatjuk. Legalább `BOILER_PANEL_ON_MIN_POWER_W`
  (alapból 2 W) aktív panelt igazol; az új mérésből származó 0 W piros
  figyelmeztetést ad. A relé bekapcsolása előtti mérés figyelmen kívül marad,
  ezért a következő pollig csak ellenőrzésre váró állapot jelenik meg.
- A Tasmota `PowerOnState` beállítása határozza meg, áramszünet után milyen
  reléállapot álljon vissza. Ennek módosítása külön, tudatos üzemeltetési döntés.
- Firmware-frissítés vagy kalibráció idején az adott fogyasztásmérő adatsora
  átmenetileg megszakadhat.
- A melegvíz- és fűtésüzem automatikus felismerése még nincs bekapcsolva. A
  következő kazánszerviz nagy gyakoriságú méréseiből előbb külön profilt kell
  készíteni a két üzemhez. Ha a fűtés később megbízhatóan felismerhető, a
  rendszer a hiányzó kézi **Fűtés** és **Melegvíz-szolgáltatás** jelölést
  együtt pótolhatja; melegvízből önmagában nem következtethet fűtésre.
