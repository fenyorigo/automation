# ConnectLife klímavezérlés – vizsgálati összefoglaló

**Projekt:** öt Hisense Energy SE KA35XR0E klíma saját vezérlése
**Állapot dátuma:** 2026. augusztus 1.
**Vizsgált ConnectLife-profil:** `009-104`

## Jelenlegi állapot

Az X260-ról működik a ConnectLife-bejelentkezés, a Python-kliens mind az öt klímát megtalálja, és az aktuális állapotukat JSON formában le tudja kérdezni. Mind az öt készülék ugyanazt a `009-104` profilt és azonos állapotstruktúrát használja. A kontrollált telefonos tesztek megerősítették az üzemmódok, a működés közbeni ventilátorfokozatok, a Fast Cool és az alvóprofilok kódjait.

Az első tényleges API-írás is sikeresen megtörtént a Fedora X260-ról a Python `connectlife` csomaggal. A kikapcsolt **Dolgozó** klíma `t_temp` értéke `16`-ról `25`-re változott, és az új értéket egy ezt követő friss snapshot visszaigazolta, miközben a `t_power` végig `0` maradt. Ezzel a ConnectLife cloud API-n keresztüli **olvasás és írás egyaránt bizonyított**.

## A projekt célja

Saját, átlátható klímaszabályozás kialakítása a meglévő infrastruktúrára építve:

- az öt Hisense klíma állapotának olvasása és vezérlése a ConnectLife API-n keresztül;
- a helyiségek valós hőmérsékletének és páratartalmának mérése Shelly H&T érzékelőkkel;
- célzott Python-szolgáltatás készítése az X260-on;
- biztonságos automatizálás hiszterézissel, minimális futási idővel és hibakezeléssel;
- a Computherm E400RF-EM hálózati kommunikációjának feltérképezése, és lehetőség szerint kiegészítő adatforrásként való használata.

Az elsődleges cél nem egy teljes Home Assistant-rendszer, hanem egy kis, jól követhető, saját vezérlő- és megfigyelőrendszer.

## Környezet

| Elem | Részlet |
|---|---|
| Gép | Lenovo ThinkPad X260 (`think260x`) |
| Operációs rendszer | Fedora Linux |
| Futási környezet | Python virtuális környezet (`.venv`) |
| Munkakönyvtár | `~/connectlife-test` |
| Python-csomag | `connectlife` |
| Használt segédprogramok | `python`, `jq`, `grep`, `diff` |
| ConnectLife backend | alapértelmezett, nem TRIR |

A jelszó interaktívan lett megadva, nem került a parancssorba vagy ebbe a dokumentumba.

## Vizsgált készülékek

Öt azonos **Hisense Energy SE KA35XR0E** készülék található a ConnectLife-fiókban:

- Háló
- Kristófék
- Rita
- Veronika
- Dolgozó

Mindegyik készüléknél:

| Tulajdonság | Érték |
|---|---|
| `deviceTypeCode` | `009` |
| `deviceFeatureCode` | `104` |
| profil | `009-104` |
| `property_version` | `v2` |

A profil kínai neve `104冷暖节能无功率`; ennek hozzávetőleges jelentése: **hűtő-fűtő, energiatakarékos, teljesítményadat nélkül**.

A stabil emberi azonosításhoz a `deviceNickName` használható. A `roomName` nem megbízható erre, mert egyes készülékeknél `default_room` lehet. A tényleges property-írás a `ConnectLifeAppliance.puid` használatával történik; ezt és a többi egyedi azonosítót megosztás előtt mindig ki kell takarni.

## Sikeres `connectlife.dump` lekérdezések

### Készülékek és állapotok

Az alapértelmezett `appliances` lekérdezés sikeresen bejelentkezett, és öt fájlt írt:

```bash
python -m connectlife.dump --username '<ConnectLife-felhasználó>'
```

```text
009-104.json
009-104_2.json
009-104_3.json
009-104_4.json
009-104_5.json
```

Ez igazolja, hogy az X260 látja mind az öt klímát, és mindegyik ugyanazt a profilt használja.

### Statikus adatok

A `static` lekérdezés mind az öt készüléknél sikeresen létrehozta a fájlokat:

```bash
python -m connectlife.dump \
  --username '<ConnectLife-felhasználó>' \
  --query static
```

A szerkezet:

```json
{
  "deviceTypeCode": "009",
  "deviceFeatureCode": "104",
  "query_static_data": {
    "resultCode": 0,
    "data": null
  }
}
```

A `resultCode: 0` sikeres lekérdezést jelez. A `data: null` azt mutatja, hogy ez a profil nem adott további statikus adatot; ez nem akadály, mert az állapot és a tulajdonságdefiníció más lekérdezésekből rendelkezésre áll.

### Tulajdonságlista

A profildefiníció lekérése szintén sikeres volt:

```bash
python -m connectlife.dump \
  --username '<ConnectLife-felhasználó>' \
  --query property-list \
  --device-type-code 009 \
  --device-feature-code 104
```

A létrejött `009-104-property-list.json` felső szintű szerkezete:

```json
{
  "deviceFeactureCode": "...",
  "deviceTypeCode": "...",
  "properties": [],
  "propertyVersion": "v2",
  "resultCode": 0
}
```

Megjegyzés: a válaszban a mező neve ténylegesen `deviceFeactureCode` alakban, elírással szerepel.

## Az `appliances` JSON szerkezete

A készülékfájl felső szintjén az alábbi mezők találhatók:

```text
bindTime, createTime, deviceExtendInfoList,
deviceFeatureCode, deviceFeatureName, deviceId,
deviceNickName, deviceTypeCode, deviceTypeName,
energyRole, isShow, offlineState, puid, role,
roomId, roomName, seq, statusList, useTime, wifiId
```

A legfontosabb részek:

| JSON-rész | Szerep |
|---|---|
| `deviceNickName` | ember által felismerhető készüléknév |
| `deviceId` | ConnectLife-belső készülékazonosító |
| `puid` | az `update_appliance()` property-írás címzési azonosítója |
| `deviceTypeCode` + `deviceFeatureCode` | a `009-104` profil azonosítása |
| `offlineState` | a készülék elérhetőségi állapota |
| `statusList` | mért értékek, beállítások és hibajelzők |
| `deviceExtendInfoList.property_version` | a tulajdonságséma verziója (`v2`) |

Az öt JSON diffje alapján a szerkezet azonos. Főként az egyedi azonosítók, a készülék- és szobanevek, a párosítás ideje és a pillanatnyi mért hőmérséklet tér el.

## Fontos állapotmezők

| Mező | Jelentés | Megfigyelt / ismert értékek | Megjegyzés |
|---|---|---|---|
| `t_power` | be-/kikapcsolás | `0`, `1` | `0` = kikapcsolva, `1` = bekapcsolva |
| `t_work_mode` | kiválasztott üzemmód | `0,1,2,3,4` | a teljes mapping telefonos teszttel megerősítve |
| `t_temp` | célhőmérséklet | például `26` | Celsius esetén 16–32 °C között írható |
| `f_temp_in` | beltéri egység által mért hőmérséklet | például `26`, `27`, `30` | olvasható, a gyakorlatban Celsius |
| `t_fan_speed` | ventilátorsebesség | `0,1,5,6,7,8,9` | a fokozatok csak bekapcsolt állapotban értelmezhetők; Quiet esetén `1` |
| `offlineState` | elérhetőségi állapot | a mintákban `1` | a működő lekérdezések mellett `1` az online/elérhető állapot |

Példa egy kikapcsolt készülék állapotára:

```json
{
  "offlineState": 1,
  "statusList": {
    "t_power": "0",
    "t_work_mode": "2",
    "t_temp": "26",
    "f_temp_in": "26",
    "t_fan_speed": "0",
    "t_up_down": "1"
  }
}
```

Fontos felismerés, hogy a bekapcsolás és az üzemmód külön állapot: kikapcsolt készüléknél is megmarad az utoljára kiválasztott `t_work_mode` és `t_temp`. A `t_fan_speed` ettől eltérően kikapcsolás után `0`-ra áll vissza a felhőállapotban, ezért a ventilátorfokozatot csak működő készüléken lehet megbízhatóan azonosítani.

További megfigyelések:

- a vizsgált mintában minden `f_e_...` hibatétel `0` volt;
- `f_humidity: 128` nem 128% páratartalmat jelent, hanem nagy valószínűséggel nem támogatott / nem elérhető érték;
- a beltéri egység magasan elhelyezett érzékelőjének `f_temp_in` értéke nem feltétlenül reprezentálja jól a tartózkodási zóna hőmérsékletét;
- a `property-list` az `f_temp_in` mezőhöz furcsa, átfedő `0~37，32~99` tartományt közöl; ez feltehetően Celsius/Fahrenheit metadata vagy pontatlan felhős definíció. A tényleges értékek Celsiusként értelmezhetők.

## A `property-list` eredményei

Az `RW` jelölés azt jelenti, hogy a ConnectLife profil a mezőt olvashatóként és írhatóként hirdeti. Az első vezérlési PoC szempontjából ez a döntő eredmény.

### Fő vezérlőmezők

| Mező | Hozzáférés | Érvényes érték / tartomány | Értelmezés |
|---|---:|---|---|
| `t_power` | `RW` | `0,1` | ki / be |
| `t_work_mode` | `RW` | `0,1,2,3,4` | öt üzemmód; a teljes mapping igazolt |
| `t_temp` | `RW` | `16~32,61~90` | célhőmérséklet Celsius/Fahrenheit tartományban |
| `t_temp_type` | `RW` | `0,1` | hőmérsékleti mértékegység váltása |
| `t_fan_speed` | `RW` | `0,5,6,7,8,9` | automata és öt normál fokozat; Quiet alatt `1` is megfigyelhető |
| `t_fan_speed_s` | `RW` | `0,5,6,7,8,9` | hangvezérléshez jelölt ventilátorsebesség |
| `t_up_down` | `RW` | `0,1` | függőleges légterelés / swing |
| `t_beep` | `RW` | `0,1` | visszajelző hang |
| `t_eco` | `RW` | `0,1` | energiatakarékos mód |
| `t_fan_mute` | `RW` | `0,1` | halk ventilátorüzem |
| `t_super` | `RW` | `0,1` | intenzív / turbo mód |
| `t_sleep` | `RW` | `0,1,2,3,4` | alvó mód változatai |
| `t_device_info` | `RW` | `0,1` | kézi adatfrissítésként leírt mező |

### Csak olvasható fontos mező

| Mező | Hozzáférés | Metadata | Értelmezés |
|---|---:|---|---|
| `f_temp_in` | `R` | `0~37，32~99` | mért beltéri hőmérséklet; a metadata tisztázandó |

## Confirmed property mappings (megerősített property-mappingek)

Az alábbi értékeket a ConnectLife telefonos alkalmazásban végzett kontrollált állítások és az ezeket követő állapot-snapshotok erősítették meg.

### Üzemmódok

| ConnectLife mód | Property | Érték |
|---|---|---:|
| Fan | `t_work_mode` | `0` |
| Heat | `t_work_mode` | `1` |
| Cool | `t_work_mode` | `2` |
| Dry | `t_work_mode` | `3` |
| Auto | `t_work_mode` | `4` |

### Ventilátorfokozatok működés közben

| ConnectLife beállítás | `t_fan_speed` | További állapot |
|---|---:|---|
| Auto | `0` | `t_fan_mute = 0` |
| Quiet | `1` | `t_fan_mute = 1` |
| Low | `5` | `t_fan_mute = 0` |
| Mid-low | `6` | `t_fan_mute = 0` |
| Mid | `7` | `t_fan_mute = 0` |
| Mid-high | `8` | `t_fan_mute = 0` |
| High | `9` | `t_fan_mute = 0` |

A Quiet beállítást célszerű külön funkcióként kezelni, nem pusztán `t_fan_speed = 1` fokozatként, mert vele együtt a `t_fan_mute` is `1` lesz. A profil `property-list` válasza a normál `t_fan_speed` értékkészletben csak a `0,5,6,7,8,9` értékeket hirdeti; a Quiet során megfigyelt `1` tehát speciális állapot.

**Fontos:** a ventilátorértékek csak bekapcsolt készüléknél hordozzák a kiválasztott fokozatot. Kikapcsolás után a felhőben a `t_fan_speed` `0`-ra áll vissza, ezért kikapcsolt állapotból nem lehet visszakövetkeztetni a korábban használt ventilátorfokozatra.

### Fast Cool

| Funkció | Megfigyelt property-k |
|---|---|
| Fast Cool | `t_super = 1`, `t_temp = 16`, `t_fan_speed = 9` |

A Fast Cool tehát összetett művelet: bekapcsolja az intenzív módot, 16 °C-ra állítja a célhőmérsékletet és maximális ventilátorfokozatot választ.

### Alvóprofilok

| ConnectLife profil | Property | Érték |
|---|---|---:|
| Off | `t_sleep` | `0` |
| General | `t_sleep` | `1` |
| Elder | `t_sleep` | `2` |
| Young | `t_sleep` | `3` |
| Kid | `t_sleep` | `4` |

A property-list pontosan a `0,1,2,3,4` értékeket engedélyezi, így a `t_sleep` mapping teljes. A Sleep-tesztek a Fast Cool után megmaradt 16 °C-os célhőmérséklettel futottak; ezért ezekből a mérésekből önmagában nem állapítható meg, hogy az egyes alvóprofilok idővel hogyan módosítják a hőmérsékletet vagy a ventilátort.

## Test methodology (tesztelési módszer)

A mappingeket a **Dolgozó** klímán, a telefonos ConnectLife alkalmazás és az X260-on futó snapshot-script együttes használatával mértük fel:

1. A klímát a telefonos alkalmazásban bekapcsoltuk, majd egyetlen vizsgált beállítást választottunk ki.
2. Minden állítás után lefutott a `./snapshot-dolgozo.sh <beszédes-címke>` parancs.
3. A script friss ConnectLife-dumpot készített mind az öt készülékről, kiválasztotta a Dolgozó klímát, és időbélyeges JSON-snapshotként mentette az állapotot.
4. A rövid összefoglalóban ellenőriztük többek között a `t_power`, `t_work_mode`, `t_temp`, `t_fan_speed`, `t_fan_mute`, `t_super` és `t_sleep` mezőket.
5. A speciális funkcióknál egymást követő teljes snapshotokat is össze kell hasonlítani, mert egyetlen alkalmazásgomb több property-t módosíthat egyszerre.

A ventilátorteszteket először kikapcsolt készüléken próbáltuk, de ekkor minden normál fokozatnál `t_fan_speed = 0` jelent meg. A bekapcsolt állapotban megismételt mérés tette láthatóvá az egyes fokozatok tényleges értékeit. Ez a negatív eredmény is fontos része a módszertani következtetésnek.

## First successful API write

### Az írási metódus azonosítása

A telepített `connectlife` csomag forrásának átvizsgálása során az `api.py` fájlban megtaláltuk a közvetlen property-írást végző publikus metódust:

```python
async def update_appliance(
    self,
    puid: str,
    properties: dict[str, str],
) -> None:
```

A metódus a készülék `puid` azonosítóját és az írandó property-k szótárát várja. A célhőmérséklet 25 °C-ra állításához szükséges hívás ezért:

```python
await api.update_appliance(
    appliance.puid,
    {"t_temp": "25"},
)
```

A `ConnectLifeAppliance` osztály vizsgálata megerősítette, hogy az API által visszaadott objektum közvetlenül biztosítja a szükséges attribútumokat:

```python
appliance.device_nickname
appliance.puid
appliance.device_type_code
appliance.device_feature_code
```

Így a célkészülék a `device_nickname == "Dolgozó"` feltétellel választható ki, az íráshoz szükséges érzékeny `puid` pedig közvetlenül az objektumból használható. Nem kell fájlba írni vagy kézzel beilleszteni; a megosztható dumpokban továbbra is redaktálható.

### Minimális `set-dolgozo-temp.py` proof-of-concept

Az első próbához szándékosan szűk hatókörű program készült. Csak a **Dolgozó** nevű készüléket választja ki, kizárólag a `t_temp` mezőt írja, és csak a profil által engedélyezett 16–32 °C közötti értéket fogad el.

```python
#!/usr/bin/env python3

import argparse
import asyncio
from getpass import getpass

from connectlife.api import ConnectLifeApi, LifeConnectError


async def main(username: str, temperature: int) -> None:
    password = getpass("Password: ")
    api = ConnectLifeApi(username, password)

    try:
        appliances = await api.get_appliances()
        dolgozo = next(
            (
                appliance
                for appliance in appliances
                if appliance.device_nickname == "Dolgozó"
            ),
            None,
        )

        if dolgozo is None:
            raise RuntimeError("A Dolgozó nevű klíma nem található.")

        print(
            f"Eszköz: {dolgozo.device_nickname} "
            f"({dolgozo.device_type_code}-{dolgozo.device_feature_code})"
        )

        await api.update_appliance(
            dolgozo.puid,
            {"t_temp": str(temperature)},
        )
        print(f"Parancs elküldve: t_temp={temperature}")

    except LifeConnectError as exc:
        print(f"ConnectLife API-hiba: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A Dolgozó Hisense klíma célhőmérsékletének módosítása."
    )
    parser.add_argument(
        "temperature",
        type=int,
        choices=range(16, 33),
        metavar="16-32",
    )
    parser.add_argument(
        "--username",
        default="<ConnectLife-felhasználó>",
    )
    args = parser.parse_args()

    asyncio.run(main(args.username, args.temperature))
```

A jelszó interaktívan került bekérésre. A program nem kapcsolja be a klímát, és nem módosít üzemmódot, ventilátort vagy más property-t.

### Sikeres végponttól végpontig tartó teszt

A teszt 2026. augusztus 1-jén, a Fedora X260-ról futott. A **Dolgozó** klíma a teljes folyamat alatt kikapcsolva maradt.

1. A kiinduló állapotot a `20260801-163349-before-api-write.json` snapshot rögzítette:

   ```json
   {
     "nickname": "Dolgozó",
     "power": "0",
     "target_temperature": "16"
   }
   ```

2. A PoC elküldte az új célhőmérsékletet:

   ```bash
   ./set-dolgozo-temp.py 25
   ```

   ```text
   Eszköz: Dolgozó (009-104)
   Parancs elküldve: t_temp=25
   ```

3. A közvetlenül ezután készített `20260801-163426-after-api-write-25.json` snapshot visszaigazolta a változást:

   ```json
   {
     "nickname": "Dolgozó",
     "power": "0",
     "target_temperature": "25"
   }
   ```

Az eredmény tömören:

```text
előtte: t_power = 0, t_temp = 16
írás:                t_temp = 25
utána:  t_power = 0, t_temp = 25
```

Ez teljes végponttól végpontig tartó bizonyíték: az X260 hitelesített a ConnectLife szolgáltatásban, név alapján megtalálta a megfelelő készüléket, a `puid` használatával elküldte a property-írást, a cloud elfogadta azt, majd egy új, független állapotlekérés ugyanazt az új értéket adta vissza. A klíma az írás közben nem kapcsolt be.

**Következtetés:** a Fedora X260 és a Python `connectlife` csomag használatával a ConnectLife cloud API-n keresztüli állapotolvasás és property-írás most már egyaránt gyakorlatban bizonyított.

## Következtetések

1. A ConnectLife API elérhető és használható a Fedora X260-ról.
2. A fiók mind az öt KA35XR0E klímája lekérdezhető.
3. Az öt készülék ugyanazt a `009-104`, `v2` profilt és állapotmodellt használja, ezért egy közös vezérlési implementáció elegendő.
4. Az állapotlekérés már működik, beleértve a ki-/bekapcsolást, módot, célhőmérsékletet, mért beltéri hőmérsékletet és ventilátorállapotot.
5. A `property-list` szerint a szükséges vezérlőmezők `RW` hozzáférésűek; a `t_temp` gyakorlati írása és visszaolvasása ezt ténylegesen is igazolta.
6. A `ConnectLifeApi.update_appliance(puid, properties)` metódussal a kikapcsolt Dolgozó klíma célhőmérséklete sikeresen módosítható volt Pythonból.
7. A ConnectLife cloud API-n keresztüli olvasási és írási útvonal egyaránt bizonyított; a legfontosabb technikai bizonytalanság megszűnt.
8. Az `f_temp_in` önmagában nem ideális szobahőmérséklet a szabályozáshoz; külön Shelly érzékelők használata indokolt.
9. Az `energy/static` jellegű adatok hiánya összhangban van a „teljesítményadat nélkül” profillal, és nem akadályozza az alapvezérlést.

## Tervezett következő lépések

### 1. Az első írás lezárása és visszaállítás

A sikeres `16 → 25` teszt után a Dolgozó klímát a szokásos 26 °C-os értékre kell visszaállítani, majd új snapshotban ellenőrizni:

```bash
./set-dolgozo-temp.py 26
./snapshot-dolgozo.sh after-api-write-26
```

Ez nem az írás bizonyításának feltétele — azt a `16 → 25` teszt már teljesítette —, hanem a készülék kívánt normál állapotának dokumentált helyreállítása.

### 2. Általános, biztonságos Python-vezérlő

A minimális, egyetlen készülékre és property-re korlátozott PoC következő változata név alapján több klímát kezelő parancssori eszköz legyen:

```bash
./climate-control.py Dolgozó status
./climate-control.py Dolgozó temperature 25
./climate-control.py Dolgozó mode cool
./climate-control.py Dolgozó fan auto
```

A program fordítsa emberi nevekre a megerősített kódokat, ellenőrizze az értéktartományokat, naplózza a parancsokat, és minden írás után friss lekérdezéssel ellenőrizze az eredményt. A `t_work_mode` és a ventilátor írása csak ilyen ellenőrzött lépésekben következzen. A `power on/off` külön, explicit parancs legyen, és csak az állapot-, hőmérséklet-, mód- és ventilátorműveletek stabil működése után kerüljön be.

### 3. Shelly H&T integráció

- kezdetben két Shelly H&T / Plus H&T Gen3 érzékelővel PoC;
- helyi HTTP- vagy MQTT-adatok lekérése az X260-ról;
- hőmérséklet- és páratartalom-adatok naplózása;
- a Shelly-mérés hozzárendelése az adott klímához;
- először csak „mit tenne a rendszer” szimuláció;
- később tényleges vezérlés hiszterézissel, minimális be-/kikapcsolási és futási idővel, valamint szenzor- és hálózati hibakezeléssel.

### 4. Computherm E400RF-EM hálózati vizsgálata

Az X260-on `tcpdump` segítségével meg kell figyelni:

- milyen címekkel kommunikál a Computherm;
- milyen protokollt és portokat használ;
- milyen gyakran küld adatot;
- van-e helyi LAN-kommunikáció vagy csak felhőkapcsolat;
- az alkalmazásban végzett változtatásokhoz köthető-e felismerhető hálózati forgalom.

Ha helyileg vagy megbízhatóan lekérdezhető, a Computherm kiegészítő adatforrás lehet. Ha nem, a szabályozás elsődleges érzékelői a Shelly eszközök lesznek.

## Biztonsági és adatkezelési megjegyzések

- A dumpok megosztása előtt ki kell takarni legalább a `deviceId`, `puid`, `wifiId`, sorozatszám-, MAC- és hitelesítési adatokat.
- A ConnectLife-jelszót ne tároljuk a forráskódban vagy shell historyban; interaktív bekérés vagy megfelelő secrets/config megoldás szükséges.
- Az első írási tesztek egyetlen, kikapcsolt készüléken történjenek.
- Az automatizálás csak sikeres visszaolvasás, naplózás és hibatűrés után kapjon tényleges vezérlési jogosultságot.
- A túl gyakori ki-/bekapcsolást szoftveresen meg kell akadályozni.

## Rövid mérföldkőlista

- [x] Python virtuális környezet és `connectlife` csomag működik
- [x] ConnectLife-bejelentkezés sikeres
- [x] Mind az öt klíma felismerve
- [x] `appliances` állapotdump elkészült
- [x] `static` lekérdezés lefutott
- [x] `009-104` property-list lekérve
- [x] A fő vezérlőmezők `RW` hozzáférése igazolva
- [x] Üzemmódok teljes mappingje telefonos teszttel igazolva
- [x] Ventilátorfokozatok mappingje működés közben igazolva
- [x] Quiet, Fast Cool és Sleep property-k feltérképezve
- [x] `ConnectLifeApi.update_appliance(puid, properties)` írási metódus azonosítva
- [x] Minimális `set-dolgozo-temp.py` PoC elkészült
- [x] Első biztonságos Python-írás és visszaolvasás (`t_temp: 16 → 25`, `t_power: 0`)
- [x] ConnectLife cloud API olvasási és írási útvonala bizonyítva
- [ ] A célhőmérséklet dokumentált visszaállítása 26 °C-ra
- [ ] Általános, visszaolvasással ellenőrző `climate-control.py`
- [ ] Kontrollált mód-, ventilátor- és később explicit power-írás
- [ ] Shelly H&T adatgyűjtési PoC
- [ ] Computherm-forgalom rögzítése és elemzése
- [ ] Megfigyelő / „mit tenne” vezérlési mód
- [ ] Biztonságos automatikus klímaszabályozás
