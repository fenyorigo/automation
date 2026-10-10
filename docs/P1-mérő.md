# P1 mérő integráció

## Cél

Az E.ON által később telepítendő okosmérő P1 portjáról helyi, közel valós idejű villamosenergia-adatokat szeretnénk átvenni az `automation` rendszerbe. A jelenlegi elsődleges jelölt erre a **HomeWizard Wi‑Fi P1 Meter**.

A megoldás nem igényel külön Raspberry Pi-t vagy saját soros P1 illesztőt. A HomeWizard csatlakozik az okosmérő P1 portjához, Wi-Fi-n elérhető, a `think260x`-en futó collector pedig a helyi API-ján keresztül olvashatja az adatokat.

Termékoldal: [HomeWizard Wi‑Fi P1 Meter](https://www.homewizard.com/shop/wi-fi-p1-meter/)

## Várható kompatibilitás az E.ON mérőivel

A HomeWizard dokumentációja szerint az E.ON Hungária által használt Sanxing, Holley és Sagemcom mérők kompatibilisek. A HomeWizard ugyanakkor ezeknél nem támogatja a fázisonkénti információ megjelenítését, ezért elképzelhető, hogy csak az összesített import- és exportadatok lesznek elérhetők az API-ján.

Forrás: [HomeWizard – Kompatibilis az intelligens fogyasztásmérőm?](https://helpdesk.homewizard.com/hu/articles/5935311-kompatibilis-az-intelligens-fogyasztasmerom)

Az E.ON P1 interfésze DSMR5-alapú, RJ12 csatlakozót használ, és az adatait 115200 baud, 8N1 paraméterekkel szolgáltatja. Az E.ON dokumentációja szerint az adatfrissítés **10 másodpercenként** történik. Emiatt nálunk is körülbelül 10 másodperces tényleges időbeli felbontással érdemes számolni, még akkor is, ha a HomeWizard más szolgáltatóknál akár másodpercenkénti frissítést is támogat.

Az E.ON dokumentációja szerint a P1 port 5 V tápfeszültséget és legfeljebb 250 mA áramot biztosít. Ez várhatóan elegendő a HomeWizard táplálásához, de ezt csak a felszerelt mérő pontos típusa és működése alapján tekintjük véglegesnek. Szükség esetén a HomeWizard USB-C táplálást is kaphat.

Forrás: [E.ON – P1 port felhasználói interfész tájékoztató](https://www.eon.hu/content/dam/eon/eon-hungary/documents/Lakossagi/aram/muszaki-ugyek/p1_port%20felhaszn_interfesz_taj_%2020230210.pdf)

## Mit mér a P1 eszköz?

A P1 port az ingatlan és a közcélú hálózat csatlakozási pontján mérhető adatokat szolgáltatja. A legfontosabb várható értékek:

- hálózatból vételezett pillanatnyi teljesítmény;
- hálózatba visszatáplált pillanatnyi teljesítmény;
- kumulált vételezett energia;
- kumulált visszatáplált energia;
- a mérőtől és a HomeWizard támogatásától függő további villamos adatok;
- a villanyórán keresztül továbbított gázmérési adatok, ha ilyen kapcsolat rendelkezésre áll – ez a jelenlegi rendszerben nem elsődleges cél.

A P1 mérő önmagában napelemes és akkumulátoros üzemben **nem adja meg a ház teljes pillanatnyi fogyasztását**. A hálózati csatlakozási pont eredő importját vagy exportját látja. A tényleges házfogyasztás előállításához a Deye inverter adatait is fel kell használni:

```text
házi fogyasztás =
    napelemtermelés
  + hálózati import
  + akkumulátor-kisütés
  - hálózati export
  - akkumulátortöltés
```

Ezért a két adatforrás tervezett szerepe:

- **HomeWizard / E.ON okosmérő:** független, mérőoldali import- és exportadat, valamint elszámolási kontroll;
- **Deye inverter:** napelemtermelés, akkumulátortöltés és -kisütés, továbbá – a telepített mérési konfigurációtól függően – gyors helyi fogyasztási adatok;
- **automation:** az időben összeillesztett adatok tárolása, ellenőrzése, megjelenítése és későbbi vezérlési felhasználása.

## Helyi API és automation-integráció

A HomeWizard helyi API-ja külön bekapcsolható. A v2 API használatához a készülék fizikai gombjának megnyomása után létrehozható egy bearer token. Az automation ezt követően felhőkapcsolat nélkül olvashatja a mérési adatokat.

Támogatott integrációs lehetőségek:

- a `/api/measurement` végpont időszakos lekérdezése;
- a `/api/ws` WebSocket kapcsolat használata folyamatos adatfogadáshoz.

Források:

- [HomeWizard Local API – Introduction](https://api-documentation.homewizard.com/docs/introduction/)
- [HomeWizard Local API – Measurement](https://api-documentation.homewizard.com/docs/v2/measurement/)
- [HomeWizard Local API – WebSocket](https://api-documentation.homewizard.com/docs/v2/websocket/)

A konkrét collector, adatbázis-mezők és mintavételi stratégia megtervezése csak a felszerelt E.ON mérő és a HomeWizard által ténylegesen visszaadott payload megismerése után történjen. Elsődlegesen a meglévő energia- és idősoros adatmodellt kell bővíteni; új struktúrát csak akkor indokolt létrehozni, ha a meglévő modell nem tudja egyértelműen kezelni az importot, exportot és azok forrását.

## Üzembe helyezési sorrend

1. Az E.ON felszereli és üzembe helyezi az okosmérőt.
2. Feljegyezzük vagy lefényképezzük a gyártót, a pontos típust és a csatlakozó környezetét.
3. Ellenőrizzük, hogy az RJ12 P1 port fizikailag hozzáférhető és aktív-e.
4. Ellenőrizzük a kompatibilitást a HomeWizard aktuális listáján.
5. Beszerezzük és csatlakoztatjuk a HomeWizard P1 Metert.
6. Szükség esetén USB-C táplálást biztosítunk számára.
7. Beállítjuk a Wi-Fi kapcsolatát és statikus DHCP-címet rendelünk hozzá.
8. Engedélyezzük a helyi API-t, és az automation számára külön hozzáférési tokent hozunk létre.
9. Megvizsgáljuk a tényleges API-payloadot és a frissítési gyakoriságot.
10. Elkészítjük a `think260x`-en futó collectort, majd összevetjük az adatokat az E.ON és a Deye értékeivel.

## Nyitott kérdések

- Pontosan milyen gyártmányú és típusú okosmérőt szerel fel az E.ON?
- Hozzáférhető és alapból aktív lesz-e a P1 port?
- A mérő P1 tápellátása stabilan elegendő-e a HomeWizard számára?
- Milyen mezőket ad vissza ténylegesen a HomeWizard az adott E.ON mérővel?
- Valóban csak összesített értékek érhetők-e el, vagy a helyi API fázisonkénti adatokat is továbbít?
- Milyen időeltérés lesz a Deye és a P1 mérései között, és szükséges-e időablakos illesztés?
- A Deye rendszerben telepített CT vagy mérő megfelelően méri-e a teljes házfogyasztást?

## Jelenlegi döntés

A HomeWizard Wi‑Fi P1 Meter megfelelő és kedvező árú elsődleges jelölt. A vásárlással célszerű megvárni az E.ON mérő felszerelését és pontos típusának ellenőrzését. Külön Raspberry Pi nem szükséges: a meglévő `think260x` végzi majd az adatgyűjtést.
