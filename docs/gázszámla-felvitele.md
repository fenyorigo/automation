# Gázszámla felvitele

Ez az útmutató az MVM földgáz-részszámlák rögzítését írja le az `automation`
alkalmazás Energia oldalán. A minta a `2025.07.07–2025.08.06` időszakú
részszámla, amely átlépi az augusztus 1-jei kedvezményes jogosultsági
évfordulót.

Az elszámolószámlák feldolgozása nincs ebben a dokumentumban véglegesítve.
Annak folyamatát egy tényleges elszámolószámla alapján külön dolgozzuk ki.

## 1. A három különböző időszak

A gázadatok feldolgozásakor három, egymástól független időszakot kell
megkülönböztetni:

1. **Számlázási időszak:** az adott részszámlán szereplő zárt dátumtartomány,
   például `2025.07.07–2025.08.06`.
2. **Saját éves elszámolási ciklus:** a tényleges éves leolvasás körül, jelenleg
   novemberben kezdődik. Ez adja a saját leolvasások kumulált fogyasztásának
   kezdőpontját.
3. **Kedvezményes jogosultsági év:** augusztus 1-jétől a következő év július
   31-éig tart. A jelenlegi éves keret 63 645 MJ, tájékoztatóan legalább
   1729 m³, idő- és fogyasztásarányos elszámolással.

A novemberi leolvasási ciklust nem szabad összekeverni az augusztusban
forduló kedvezményes jogosultsági évvel. Az MVM részszámláin szereplő becsült
fogyasztás szintén külön adatsor a saját, óráról leolvasott fogyasztástól.

## 2. Az augusztus 1-jei váltás

Ha egy számla átlépi augusztus 1-jét, továbbra is **egyetlen számlafejet** kell
rögzíteni a számlán szereplő teljes időszakkal. Nem kell két mesterséges
számlát létrehozni, és a júliusi részt sem szabad elhagyni.

Az MVM a mintaszámlát két fogyasztási és négy energiadíj-részre bontotta:

- `2025.07.07–2025.07.31`: a 2024/2025-ös jogosultsági év vége;
- `2025.08.01–2025.08.06`: a 2025/2026-os jogosultsági év kezdete.

Ezt a bontást az alkalmazásban a számlafej alatti külön fogyasztási
részletekkel és külön számlatételekkel kell leképezni. Mindig a számlán
szereplő bontást kell követni. Ha egy másik számla nem közöl ilyen bontást,
nem szabad önkényesen felosztani a szolgáltatói adatot.

## 3. Számlafej rögzítése

Az Energia oldalon az **Új számla rögzítése** részt kell használni. A
számlafej a teljes szolgáltatói bizonylatot jelenti, ezért a nettó, ÁFA,
bruttó és fizetendő összeg a fogyasztási és fix tételeket együtt tartalmazza.

A mintaszámla fejlécének adatai:

| Mező | Érték |
|---|---:|
| Típus | Részszámla |
| Részszámla sorszáma | 9 |
| Időszak | 2025.07.07–2025.08.06 |
| Számla kelte | 2025.08.13 |
| Teljesítés | 2025.08.28 |
| Fizetési határidő | 2025.08.28 |
| Nettó összeg | 33 849 Ft |
| ÁFA | 8 659 Ft |
| Bruttó összeg | 42 508 Ft |
| Kerekítés | 0 Ft |
| Fizetendő összeg | 42 508 Ft |
| Folyószámla-egyenleg | 42 508 Ft |
| Rezsicsökkentés nélküli összeg | 182 082 Ft |

A nettó összeg és az ÁFA megadása után a bruttó összeg automatikusan
kitöltődik. Ha a számlán külön **Kerekítés** sor szerepel, annak előjeles
összegét a számlafej `Kerekítés (Ft)` mezőjébe kell írni, például `-1`. A
fizetendő összeg a bruttó és a kerekítés összegeként automatikusan számolható.
A kerekítés nem fogyasztási részlet és nem számlatétel. A számlafej mentése
után jelennek meg a hozzá tartozó fogyasztási részlet- és tételűrlapok.

## 4. Fogyasztási részletek

A lenyitott számlán az **Újabb fogyasztási időszak hozzáadása** űrlappal
tetszőleges számú fogyasztási részlet rögzíthető. Az augusztus 1-jét átlépő
mintaszámlához két részlet tartozik:

| Időszak | Fogyasztás | Korrekció | Korrigált mennyiség | Fűtőérték | Hőmennyiség |
|---|---:|---:|---:|---:|---:|
| 2025.07.07–2025.07.31 | 148 m³ | 1,0000 | 148,00 m³ | 35,37 MJ/m³ | 5235 MJ |
| 2025.08.01–2025.08.06 | 36 m³ | 1,0000 | 36,00 m³ | 35,37 MJ/m³ | 1273 MJ |

Az alkalmazás az alábbi összefüggésekkel számol:

```text
korrigált mennyiség = fogyasztás × korrekciós tényező
hőmennyiség = korrigált mennyiség × fűtőérték
```

Az ismert időszak korrekciós tényezője és fűtőértéke automatikusan
betöltődik. A korrigált mennyiség két tizedesre, a hőmennyiség egész MJ-ra
kerekítődik. A számlán szereplő érték szükség esetén felülírható.

### Mérőállások és leolvasási mód

- Az **Induló MVM-állás** és **Záró MVM-állás** kizárólag akkor töltendő, ha
  az adott fogyasztási sorban valóban szerepelnek.
- Részszámlán ezek gyakran üresek. Nem azonosak az utolsó éves elszámolás
  mérőállásával.
- A **Leolvasás módja** a számla `LM` oszlopát követi. Ha az `LM` üres, a
  felületen a **Nincs feltüntetve** értéket kell választani; a részszámla
  becsült jellege önmagában nem indok a `Becsült` érték kiválasztására.
- Az **Utolsó elszámolt állás** külön tájékoztató adat. Elegendő a számla egyik
  fogyasztási részletén rögzíteni.
- A **Részszámlák kumulált mennyisége** a jelen számlát is figyelembe vevő,
  utolsó elszámolás óta számlázott mennyiség. A mintaszámlán ez `1656 m³`;
  célszerű az időrendben utolsó, augusztusi fogyasztási részlethez írni.

## 5. Energiadíjtételek

A számlát lenyitva a **Számlatétel hozzáadása** űrlapon minden szolgáltatói
sort külön kell rögzíteni. A tételt hozzá kell kapcsolni a megfelelő
fogyasztási részlethez.

Az energiadíj rögzítésekor külön ellenőrizni kell:

- a **Kategória** mező valóban `Kedvezményes energia` vagy `Versenypiaci
  energia` legyen; a kategória kiválasztásakor a megnevezés automatikusan
  kitöltődik;
- az energiadíjak **Mértékegység** mezője automatikusan `MJ` értéket kap;
- a kapcsolt fogyasztási részlet és a tétel dátumtartománya ugyanahhoz a
  számlabontáshoz tartozzon.

A mintaszámla négy energiadíjtétele:

| Kapcsolt részlet | Kategória | Mennyiség | Egységár | Nettó | ÁFA | Bruttó |
|---|---|---:|---:|---:|---:|---:|
| 07.07–07.31, 148 m³ | Kedvezményes energia | 4359 MJ | 2,256 Ft/MJ | 9834 Ft | 27% | 12 489 Ft |
| 07.07–07.31, 148 m³ | Versenypiaci energia | 876 MJ | 17,324 Ft/MJ | 15 176 Ft | 27% | 19 274 Ft |
| 08.01–08.06, 36 m³ | Kedvezményes energia | 1046 MJ | 2,256 Ft/MJ | 2360 Ft | 27% | 2997 Ft |
| 08.01–08.06, 36 m³ | Versenypiaci energia | 227 MJ | 17,324 Ft/MJ | 3933 Ft | 27% | 4995 Ft |

Az alkalmazás a mennyiség és a nettó egységár szorzatából egész forintra
kerekített nettó összeget számol. Ebből és az ÁFA-kulcsból szintén egész
forintra kerekített bruttó összeg készül. Az adatbázis a kerekített nettó és
bruttó összeget tárolja.

Az ÁFA alapértéke 27%. A **Szolgáltatás** kategória kivétel: ott 0% az
alapérték.

## 6. Fix és áfamentes tételek

A fix díjak is számlatételek; nem kell és nem szabad őket automatikusan a
becsült havi fix díjból létrehozni. A számlán ténylegesen szereplő sorokat kell
rögzíteni.

| Kategória | Megnevezés | Időszak | Mennyiség | Egységár | Nettó | ÁFA | Bruttó |
|---|---|---|---:|---:|---:|---:|---:|
| Alapdíj | Háztartási alapdíj | 2025.08.01–2025.08.31 | 1 hó | 766 Ft/hó | 766 Ft | 27% | 973 Ft |
| Szolgáltatás | OtthonSOS Komfort | 2025.08.01–2025.08.31 | 1 hó | 790 Ft/hó | 790 Ft | 0% | 790 Ft |
| Szolgáltatás | OtthonSOS Garancia Médium | 2025.08.01–2025.08.31 | 1 hó | 990 Ft/hó | 990 Ft | 0% | 990 Ft |

Az **Alapdíj** kategória automatikusan a `Háztartási alapdíj` megnevezést
kapja. A **Szolgáltatás** kategóriánál legördülőből választható az
`OtthonSOS Komfort` vagy az `OtthonSOS Garancia Médium`. Mindkét kategóriánál
automatikusan `hó` lesz a mértékegység. A tétel dátuma a számlán közölt
szolgáltatási időszak legyen, ami nem feltétlenül egyezik meg a számlafej
teljes időszakával.

A becslési törzsadatok között szereplő havi fix összeg kizárólag tervezési
adat. Nem helyettesíti a számla tényleges alapdíj- és szolgáltatási sorait.

## 7. Ellenőrző összegek

A felvitel után az alábbi egyezőségeket érdemes ellenőrizni:

```text
148 m³ + 36 m³ = 184 m³
5235 MJ + 1273 MJ = 6508 MJ

4359 MJ + 876 MJ + 1046 MJ + 227 MJ = 6508 MJ
9834 Ft + 15 176 Ft + 2360 Ft + 3933 Ft = 31 303 Ft energiadíj nettó
12 489 Ft + 19 274 Ft + 2997 Ft + 4995 Ft = 39 755 Ft energiadíj bruttó

31 303 Ft + 766 Ft = 32 069 Ft 27%-os nettó
32 069 Ft + 8659 Ft = 40 728 Ft 27%-os bruttó
40 728 Ft + 790 Ft + 990 Ft = 42 508 Ft fizetendő
```

Az összes számlatétel bruttó összegének meg kell egyeznie a számlafej
fizetendő összegével. A fogyasztási részletek MJ-összegének meg kell egyeznie
az energiadíjtételek MJ-összegével.

Az ellenőrzésnél nem elég csak az összegeket összeadni. Külön át kell nézni:

- minden tétel kezdő- és záródátumát;
- az energiadíjak `MJ`, a havi fix tételek `hó` mértékegységét;
- a kedvezményes és versenypiaci kategóriák helyes kiválasztását;
- hogy az utolsó elszámolt mérőállás dátuma és értéke ugyanazon fogyasztási
  részleten szerepeljen, a másik részleten pedig mindkettő legyen üres;
- hogy korábban felvitt tételnél se maradjon tört forintos bruttó összeg.

## 8. MJ és kWh összehasonlítás

A Globális beállítások `ENERGY_MJ_PER_KWH` értéke jelenleg `3,6 MJ/kWh`.

```text
kWh-egyenérték = hőmennyiség MJ / 3,6
6508 MJ / 3,6 = 1807,78 kWh
```

Ez energiatartalom-egyenérték, nem a helyiségbe leadott hasznos hő. A gáz- és
klímafűtés költségének összehasonlításakor még figyelembe kell venni a kazán
hatásfokát és a klíma külső hőmérséklettől függő COP/SCOP értékét.

## 9. Javítás

Szerkesztői jogosultsággal külön ceruza található:

- a számlafej mellett;
- minden fogyasztási részlet mellett;
- minden számlatétel sorának végén.

A ceruza csak a kiválasztott rekordot nyitja meg javításra. A többi
fogyasztási részletet és tételt nem módosítja.

## 10. Adatbázis-megfeleltetés

| Felületi adat | Tábla |
|---|---|
| Saját óraállás | `energy_meter_readings` |
| Számlafej | `energy_invoices` |
| MVM fogyasztási részlet | `energy_invoice_consumption` |
| Energia-, alapdíj- és szolgáltatási tétel | `energy_invoice_charge_lines` |
| Korrekció és fűtőérték | `gas_conversion_periods` |
| Kedvezményes és piaci tarifa | `energy_tariff_periods` |
| Augusztus–júliusi kedvezményes keret | `energy_entitlement_periods` |
| MVM havi becsült sávmegosztása | `energy_allocation_rules` |

A saját leolvasást nem szabad az MVM becsült fogyasztási adataival
helyettesíteni vagy összevonni. A szolgáltatói számlázás és a tényleges
fizikai fogyasztás később ezek különbségével ellenőrizhető.

## 11. Elszámolószámla – későbbi feladat

Az elszámolószámla várhatóan lezárja vagy korrigálja a részszámlák becsült
fogyasztását, tartalmaz tényleges mérőállást, és módosíthatja a kedvezményes és
versenypiaci sávok végleges megosztását. A pontos adatfelviteli folyamatot nem
feltételezzük előre: egy rendelkezésre álló elszámolószámla alapján külön kell
ellenőrizni és dokumentálni.

## Források

- MVM: [A lakossági földgáz rezsicsökkentés legfontosabb információi](https://www.mvmnext.hu/lakossagirezsi/legfontosabb-informaciok-gaz)
- Minta: NKM/MVM Gáz, `2025.07.07–2025.08.06` időszakú 9. részszámla
