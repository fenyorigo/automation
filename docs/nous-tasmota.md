# Nous/Tasmota fogyasztásmérők

Az alkalmazás a Tasmota firmware-t futtató Nous okosdugaljakat közvetlen HTTP-
lekérdezéssel kezeli; ezeknél az MQTT nem része az adatútnak. A periodikus
lekérdezés önmagában nem kapcsolja a relét és nem módosítja az eszköz
konfigurációját. A bojlerprogram a `nous-bojler` kezdőlapi kártyájáról
kapcsolható be és ki szerkesztőként.

## Nyilvántartott eszközök

| Technikai azonosító | Cím | Feladat |
|---|---|---|
| `nous-mainit` | `192.168.0.44` | fő informatikai infrastruktúra |
| `nous-auxit` | `192.168.0.45` | dolgozószobai kiegészítő informatikai infrastruktúra |
| `nous-bojler` | `192.168.0.46` | 1,8 kW-os villanybojler tápellátása, fogyasztásmérése és időzítése |
| `nous-kazan` | `192.168.0.47` | Bosch kazán tápellátása, kapcsolása és fogyasztásmérése |

A korábbi `nous-kazan` fizikai dugalj (`.46`, `C8:C9:A3:2B:34:11`, Tasmota
`tasmota-2B3411-5137`) került a bojlerhez és vette át a `nous-bojler`
integrációs azonosítót. A `.47`, `C8:C9:A3:2B:35:60` eszköz reléje az
áramkimaradások után hibásnak látszott, de teljes Tasmota-reset és
újrakonfigurálás után ismét működik, ezért új `nous-kazan` rekordként került
vissza a kazánházba. A hibásként létrehozott régi rekordot és 180 mérését
2026. szeptember 24-én töröltük.

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
| aktív `nous-bojler` (korábbi kazándugalj) | 229 V | 2026-09-24-én újrakalibrálva |
| `nous-kazan` | 230 V | a teljes reset után újból ellenőrizendő |

A most aktív bojlerdugalj korábban a Bosch előtt működött; azon a helyen a
bekapcsolt Bosch nyugalmi fogyasztása 5 W volt. Ez történeti adat, nem a
villanybojler jelenlegi terhelése.

Ez kizárólag a feszültségcsatorna kalibrációja. A teljesítmény- és
energiamérés pontosságának ellenőrzéséhez ismert, lehetőleg közel ohmos
terhelés és külön referencia teljesítménymérő szükséges. Terhelés nélküli
állapotból a teljesítménykalibráció nem állapítható meg.

A később meghibásodott korábbi `nous-bojler` első felfűtési ciklusában a még gyári `PowerCal=12530`
`2231–2297 W` teljesítményt jelzett, miközben az egyidejű feszültség- és
áramértékek szorzata `1,81–1,88 kW` volt. Stabil, tisztán ellenállásos
terhelésnél a `PowerSet 1870` paranccsal a végleges érték `PowerCal=10132` lett;
utána a kijelzés `1862–1875 W` között stabilizálódott. A kalibráció előtti
135 mérési sort töröltük, az eszköz napi és összes energiaértéke pedig
2026. szeptember 23-án 08:33:37-kor új, nulláról induló mérési életet kezdett.
Ez a teljesítménykalibráció nem került át az új fizikai dugaljra: az aktív
`.46` eszköz teljesítmény- és energiamérését a következő bojler-felfűtéskor
ismert terheléssel külön ellenőrizni kell.
Az előző adatállapot mentése:
`/var/backups/automation/home_automation_before_nous_bojler_measurement_reset_20260923T0832CEST.sql.gz`.

## Villanybojler időzítése

A `nous-bojler` napi tápablakának egyetlen igazságforrása az automation.
Az eszközbélyeg a fizikai relé ON/OFF állapotától külön jelzi, hogy a program
aktív-e. A bélyeg művelete a program be- vagy kikapcsolása; aktív programnál a
közvetlen kézi relékapcsoló nem jelenik meg. Az időablakon kívüli OFF állapot
várt, semleges állapotként jelenik meg.
A Tasmota saját időzítői kikapcsolva maradnak. A Globális beállítások között
állítható az ütemezés engedélyezése, a bekapcsolási idő és a kikapcsolási idő;
az alapérték minden nap `05:00–12:00`.

A poller legfeljebb egyperces ciklusban közvetlen HTTP-állapotolvasással
egyezteti a relét a kívánt állapottal. Ha a szerver vagy a dugalj a kapcsolási
időpontban nem volt elérhető, a kapcsolat helyreállása után a soron következő
egyeztetés állítja be a helyes állapotot. A tényleges automatikus kapcsolások és a hibák a
`device_power_control_attempts` táblába kerülnek `schedule` eredettel.

## Üzemeltetési megjegyzések

- A 2026-09-23-i áramkimaradások után mind a négy A1T-t újra kellett
  konfigurálni. A helyreállításkor minden eszközön az A1T template, a HTTP API,
  a `PowerOnState` és a feszültségkalibráció ellenőrzése szükséges volt.
- A 2026-09-24-i fizikai azonosítás során derült ki, hogy a kazán és a bojler
  mellett lévő két dugalj szerepe fel volt cserélve. A működő `.46` került a
  bojlerhez. A `.47` relékimenete először hibásnak látszott, de teljes reset és
  újrakonfigurálás után terheléssel is működött; új `nous-kazan` rekordként
  visszakerült a kazánházba.

- A `nous-mainit` kritikus hálózati eszközöket táplál; kapcsolása az egész
  helyi infrastruktúrát leállíthatja.
- A `nous-bojler` 1,8 kW-os névleges terhelése 230 V mellett kb. 7,8 A. A
  fizikailag 16 A-es A1T ehhez megfelelő tartalékkal rendelkezik; az első
  teljes felfűtési ciklus alatt az aljzat és a csatlakozó melegedését ellenőrizni
  kell.
- A Bosch tápellátását ismét a `nous-kazan` kapcsolja és méri. A kazánpanel,
  a melegvíz- és a fűtésengedély állapota továbbra is kézi nyilvántartású.
- Minden kapcsolási kísérlet, kérő felhasználó és visszaellenőrzött eredmény a
  `device_power_control_attempts` táblába kerül.
- A `nous-mainit`, `nous-auxit` és a Zigbee router-dugaljak az UI-ból nem
  kapcsolhatók; ezek továbbra is csak megfigyelhetők.
- A korábbi `nous-kazan` 2026. szeptember 10-i első lekérdezésekor a relé bekapcsolt,
  a kikapcsolt Bosch panel terhelése 0 W volt. A rövid kézi próba alatt az
  indulási értékek 23, 122 és 74 W, a bekapcsolt panel nyugalmi értéke stabilan
  5 W volt. A kijelzett 301–304 V nyilvánvaló kalibrációs hiba, ezért a
  feszültség- és energiaadatok üzemszerű használata előtt külön kalibráció kell.
- A Bosch fogyasztásalapú power-felismerése a `nous-kazan` friss méréseire
  ismét alkalmazható; az első próba egy csatlakoztatott terheléssel 8 W-ot
  és 231 V-ot mutatott.
- A Tasmota `PowerOnState` beállítása határozza meg, áramszünet után milyen
  reléállapot álljon vissza. Ennek módosítása külön, tudatos üzemeltetési döntés.
- Firmware-frissítés vagy kalibráció idején az adott fogyasztásmérő adatsora
  átmenetileg megszakadhat.
- A melegvíz- és fűtésüzem automatikus felismerése még nincs bekapcsolva. A
  következő kazánszerviz nagy gyakoriságú méréseiből előbb külön profilt kell
  készíteni a két üzemhez. Ha a fűtés később megbízhatóan felismerhető, a
  rendszer a hiányzó kézi **Fűtés** és **Melegvíz-szolgáltatás** jelölést
  együtt pótolhatja; melegvízből önmagában nem következtethet fűtésre.
