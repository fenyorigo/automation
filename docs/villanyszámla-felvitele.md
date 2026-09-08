# Villanyszámla felvitele

Ez a leírás az A1 villanyóra 2024. december 17-től rendelkezésre álló NKM/MVM
számláinak rögzítését írja le. A számlán szereplő szolgáltatói becslés nem
helyettesíti a saját óraállás-idősort.

## Nyilvántartott mérő

Az automation fogyasztási mérője a `9900930533` gyári számú A1 mérő. A
`9900460152` vezérelt mérő állása folyamatosan 30 395 kWh, fogyasztása nulla,
ezért nem készül hozzá külön mérő- és fogyasztási idősor.

A vezérelt mérő számlán ténylegesen felszámított díja viszont megmarad:

- kategória: **Alapdíj**;
- megnevezés: **Használaton kívüli vezérelt mérő alapdíja**;
- nettó egységár: 39,50 Ft;
- ÁFA: 27%;
- kerekített nettó összeg: 40 Ft;
- kerekített bruttó összeg: 51 Ft.

Ezt csak azon a számlán kell szerepeltetni, amelyen a szolgáltató is
felszámította. A 2026. május 31-i záró elszámoláson és az új MVM-számlaképen
már nem szerepel.

## Elszámolási ciklusok

Három ciklussal érdemes indulni:

1. `2024-12-17–2025-12-20`, lezárt éves NKM-ciklus;
2. `2025-12-21–2026-05-31`, a számlázási átállás miatt idő előtt lezárt ciklus;
3. `2026-06-01–`, nyitott MVM-ciklus.

A ciklus és a kedvezményes mennyiség augusztus 1-jei éves határa két külön
fogalom. Ha egy számla átnyúlik augusztus 1-jén, ugyanahhoz a számlafejhez két
fogyasztási részletet, valamint időszakonként külön kedvezményes és piaci
energiadíjsort kell rögzíteni.

## Számlafej

Az energiafajta/mérő a **Villanyóra** legyen. A számláról rögzítendő:

- számlaszám;
- részszámla, elszámolószámla vagy korrekció;
- részszámla sorszáma;
- elszámolt időszak;
- számla kelte, teljesítés és fizetési határidő;
- nettó, ÁFA- és bruttó számlaérték;
- külön számlaszintű kerekítés;
- fizetendő összeg és folyószámla-egyenleg;
- szolgáltató/számlázási rendszer, felhasználóazonosító és szerződéses
  folyószámla.

A számlaszám egyedi. Az azonos számlaszámú második PDF nem új számla.

## Fogyasztási részlet

Villanyszámlán a fogyasztási részlet mezői:

- időszak kezdete és vége;
- induló és záró szolgáltatói mérőállás;
- leolvasási mód;
- elszámolt fogyasztás kWh-ban;
- az utolsó elszámolt mérőállás dátuma és értéke, ha a számla közli;
- részszámlák kumulált fogyasztása, amelyet cikluson belül az alkalmazás
  újraszámol.

Villanynál nincs korrekciós tényező, korrigált m³, fűtőérték vagy hőmennyiség.
Ezek a mezők továbbra is kizárólag a gázszámlákhoz tartoznak.

## Díjtételek

### Energiadíj

- **Kedvezményes energia**: nettó 5,1100 Ft/kWh;
- **Versenypiaci energia**: nettó 31,8000 Ft/kWh.

A kWh-mennyiséget mindig a számláról kell átvenni. Az egységár az időben
hatályos tarifatörzsből kitöltődhet. A nettó és bruttó összeget az alkalmazás
egész forintra kerekíti.

### Rendszerhasználati díjak

A régi számlaképen egyetlen tétel szerepel:

- **Összevont rendszerhasználati díj**,
  `Rendszerhasználati-üzemeltetési díj`, nettó 23,4000 Ft/kWh.

A 2026. június 1-jétől induló új számlaképen két tétel szerepel:

- **Átviteli forgalmi díj**, nettó 3,3900 Ft/kWh;
- **Elosztói forgalmi díj**, nettó 20,0100 Ft/kWh.

Mindegyik fogyasztásarányos, ezért a számla teljes elszámolt kWh-mennyiségét
kell hozzá megadni.

### Alapdíj

Az A1 mérő alapdíja nettó 120,50 Ft. A számlán szereplő mennyiséget és
mértékegységet kell átvenni. A 2026.06.01–07.22 közötti első új MVM-részszámla
két havi alapdíjat tartalmaz; ezt az automatikusan létrehozott soron 2-re kell
javítani. A használaton kívüli vezérelt mérő 39,50 Ft-os nettó alapdíja külön
sor, kizárólag a régi számlákon.

### Túlfizetés és egyéb egyszerű összegek

A túlfizetés vagy támogatás előjeles, bruttó összeg. A
`2026.06.01–2026.07.22` számlán a korábbi záró elszámolás 12 512 Ft-ja
`-12 512 Ft` túlfizetésként csökkenti a fizetendőt.

## Elszámolószámla

Az éves vagy záró elszámolás fogyasztási sorában a teljes ciklus induló és
záró állása, valamint tényleges vagy becsült fogyasztása szerepel. A
kedvezményes és piaci energiadíjat a számla szerinti időszakokra kell bontani.

A jóváírások külön negatív tételek:

- **Elszámolt részszámlák energiadíja**;
- **Elszámolt rendszerhasználati díjak**.

Az elszámolás utolsó oldalán felsorolt részszámlákat a számlaszám és pozitív
végösszeg alapján hozzá kell kapcsolni. A szolgáltató a korábbi havi
alapdíjakat nem ezekben a jóváírásokban fordítja vissza.

## Ismert duplumok

Csak egyszer rögzítendő:

- `NKM Áram 20260127-20260225.pdf` és a `bis` példánya ugyanaz a
  `14510917691` számú számla;
- `NKM Áram 20251221-20260531 elszámolás.pdf` és
  `MVM 20251231-2026-0531 Villany_011512318276.pdf` ugyanaz a
  `11512318276` számú elszámolószámla. A helyes időszak
  `2025-12-21–2026-05-31`.

## Javasolt rögzítési sorrend

1. Elszámolási ciklus létrehozása.
2. Számlafej rögzítése.
3. Egy vagy több fogyasztási részlet rögzítése.
4. Kedvezményes és piaci energiadíjtételek.
5. Rendszerhasználati és alapdíjtételek.
6. Elszámolószámlán a két negatív jóváírás.
7. Elszámolt részszámlák összekapcsolása.
8. A számlafej, a díjtételek és a fizetendő összeg végső egyeztetése.
