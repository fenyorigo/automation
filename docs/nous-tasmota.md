# Nous/Tasmota fogyasztásmérők

Az alkalmazás a Tasmota firmware-t futtató Nous okosdugaljakat hálózaton,
csak olvasható teljesítmény- és energiamérőként kezeli. A periodikus lekérdezés
nem kapcsolja a relét és nem módosítja az eszköz konfigurációját.

## Nyilvántartott eszközök

| Technikai azonosító | Cím | Feladat |
|---|---|---|
| `nous-mainit` | `192.168.0.44` | fő informatikai infrastruktúra |
| `nous-auxit` | `192.168.0.45` | dolgozószobai kiegészítő informatikai infrastruktúra |
| `nous-kazan` | `192.168.0.46` | Bosch 7000i tápellátásának felügyelete |

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

A 2026. augusztus 17-i beállítások:

| Eszköz | Referencia | `VoltageCal` változás |
|---|---:|---:|
| `nous-auxit` | 230 V | 1950 → 1522 |
| `nous-mainit` | 226 V | → 1454 |

Ez kizárólag a feszültségcsatorna kalibrációja. A teljesítmény- és
energiamérés pontosságának ellenőrzéséhez ismert, lehetőleg közel ohmos
terhelés és külön referencia teljesítménymérő szükséges. Terhelés nélküli
állapotból a teljesítménykalibráció nem állapítható meg.

## Üzemeltetési megjegyzések

- A `nous-mainit` kritikus hálózati eszközöket táplál; kapcsolása az egész
  helyi infrastruktúrát leállíthatja.
- A jelenlegi alkalmazásintegráció olvasási célú, vezérlés nincs engedélyezve.
- A `nous-kazan` a hűtés–fűtés vezérlésben részt vevő eszközök alapnézetében
  is megjelenik. A relé bekapcsolt állapota csak a Bosch tápellátását jelenti;
  nem bizonyítja, hogy a kazánon a melegvíz vagy a fűtés engedélyezve van.
- A `nous-kazan` 2026. szeptember 10-i első lekérdezésekor a relé bekapcsolt,
  a terhelés 0 W volt. A kijelzett 306 V nyilvánvaló kalibrációs hiba, ezért a
  feszültség- és energiaadatok üzemszerű használata előtt külön kalibráció kell.
- A Tasmota `PowerOnState` beállítása határozza meg, áramszünet után milyen
  reléállapot álljon vissza. Ennek módosítása külön, tudatos üzemeltetési döntés.
- Firmware-frissítés vagy kalibráció idején az adott fogyasztásmérő adatsora
  átmenetileg megszakadhat.
