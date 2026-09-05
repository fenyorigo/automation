# Zigbee végberendezés célzott újracsatlakoztatása routeren keresztül

Ez az útmutató akkor használható, ha egy távoli, elemes végberendezés — például
SONOFF hőmérő vagy Nous/Tuya nyitásérzékelő — bizonytalanul kommunikál, és a
közelében már működik egy állandó tápellátású Zigbee router (nálunk SONOFF Smart
Plug).

Fontos: a Zigbee2MQTT célzott `Permit join` funkciója segíti, de **nem
garantálja**, hogy az eszköz a kiválasztott routert választja szülőnek, vagy
később is annál marad. Az elemes végberendezésnek egyszerre egy szülője van; a
szülőválasztás és az esetleges későbbi váltás eszközfüggő.

## A jelenlegi rendszer

- Zigbee2MQTT: [http://think260x:8083/](http://think260x:8083/)
- koordinátor: Tasmotára állított SONOFF Zigbee Bridge;
- Zigbee-csatorna: `25`;
- routerek: a hálózatban regisztrált SONOFF Smart Plugok;
- az automation collector az eszközt elsősorban IEEE-cím alapján azonosítja.

A művelet alatt ne változtassuk meg a Zigbee-csatornát, a hálózati kulcsot vagy
a PAN ID-t, és ne áramtalanítsuk egyszerre az összes routert.

## Előfeltételek

- A kiválasztott router legyen bekapcsolva és a Zigbee2MQTT szerint elérhető.
- A végberendezés legyen a végleges helyén vagy közvetlenül annak közelében.
- Legyen fizikai hozzáférés a párosítógombhoz és szükség esetén az elemhez.
- Jegyezzük fel az eszköz jelenlegi `friendly_name` nevét és IEEE-címét.

## Javasolt eljárás törlés nélkül

### 1. Célzott csatlakozás engedélyezése

1. Nyissuk meg a Zigbee2MQTT webes felületét.
2. A jobb felső `Permit join (All)` gomb melletti nyíllal nyissuk meg a listát.
3. Válasszuk ki azt a Smart Plug routert, amely a szenzorhoz a legközelebb van.

A csatlakozási ablak korlátozott ideig él. A művelet végeztével kézzel is
zárjuk be, ne hagyjuk szükségtelenül nyitva a hálózatot.

### 2. A végberendezés újracsatlakoztatása

Az eszközt első próbálkozáskor **ne töröljük** a Zigbee2MQTT-ből. Ugyanabba a
hálózatba, azonos IEEE-címmel történő újracsatlakozáskor a neve és az automation
nyilvántartási kapcsolata így megmaradhat.

- SONOFF szenzornál kövessük az adott modell Zigbee2MQTT eszközoldalán leírt
  párosítási/reset eljárást. Sok modellnél körülbelül öt másodperces
  gombnyomás indítja a villogással jelzett csatlakozást, de ez nem minden
  modellnél azonos.
- Nous/Tuya nyitásérzékelőnél indítsuk el a villogással jelzett párosítási
  módot. Az interjú alatt rövid gombnyomással körülbelül három másodpercenként
  tartsuk ébren. A mágnes mozgatása küldhet állapotot, de nem minden modellnél
  helyettesíti a gombnyomást.

Siker esetén a Zigbee2MQTT naplója újracsatlakozást vagy sikeres interjút jelez.
Ezután zárjuk le a `Permit join` ablakot.

### 3. Működési ellenőrzés

Az elsődleges ellenőrzés ne kizárólag a hálózati térkép vagy egyetlen LQI-érték
legyen.

1. Hőmérőnél ébresszük fel az eszközt rövid gombnyomással, majd ellenőrizzük a
   `last_seen` frissülését és egy új mérési üzenetet.
2. Nyitásérzékelőnél hajtsunk végre egy csukás–nyitás állapotváltást, és
   ellenőrizzük mindkét változást a Zigbee2MQTT-ben.
3. Nézzük meg az automation UI-t is: az állapotnak és az utolsó Zigbee-jel
   időpontjának frissülnie kell.
4. Ismételjük meg az ellenőrzést a következő néhány órában is. A stabil
   üzenetküldés fontosabb, mint egyetlen jelerősségi szám.

## Hálózati térkép és LQI

A `Network map` → `Load map` hasznos kiegészítő diagnosztika, de nem tekinthető
biztos szülőkapcsolati bizonyítéknak:

- az elemes eszközök hosszú alvása miatt egy működő kapcsolat is hiányozhat;
- a térképfelmérés 10 másodperctől akár 2 percig tarthat, és közben a hálózat
  kevésbé válaszképes lehet, ezért csak kézzel indítsuk;
- az LQI gyártó- és Zigbee-stack-függő, útvonalanként változhat, ezért nincs
  minden eszközre érvényes „legalább 80” határérték;
- az LQI-t és — ahol elérhető — az RSSI-t az elveszett üzenetekkel, a
  `last_seen` frissességével és több mérés trendjével együtt értékeljük.

## Hibaelhárítási sorrend

### 1. Nincs újracsatlakozás vagy az interjú megszakad

1. Ellenőrizzük, hogy a célrouter valóban elérhető.
2. Tegyünk be friss elemet, vagy vegyük ki az elemet körülbelül tíz
   másodpercre, majd próbáljuk újra.
3. Indítsuk újra a célzott `Permit join` ablakot, és az interjú alatt tartsuk
   ébren az eszközt.
4. Szükség esetén ismételjük meg a párosítást két-három alkalommal.

### 2. A router vagy a végberendezés egy áramszünet után nem kommunikál

Először várjunk néhány percet a mesh rendeződésére, majd idézzünk elő valódi
állapotváltozást. Ha a router nem tért vissza, csak az érintett routert
áramtalanítsuk néhány másodpercre. A Zigbee2MQTT vagy a bridge újraindítása nem
általános első lépés; azt naplóellenőrzés előzze meg.

### 3. Eltávolítás és új párosítás

Csak akkor távolítsuk el az eszközt, ha a törlés nélküli próbák nem működnek.

1. Mentsük el a `friendly_name` nevet, az IEEE-címet és a helyiség-
   hozzárendelést.
2. Először normál eltávolítást kérjünk. Ha újra felvesszük az eszközt, a
   konfiguráció megőrzéséhez használható a `keep_config` lehetőség.
3. Az alvó eszközt a kérés idején tartsuk ébren; normál eltávolításnál a
   koordinátor csak megkérheti az eszközt a hálózat elhagyására.
4. A `Force remove` kizárólag végső megoldás. Ez csak a Zigbee2MQTT
   adatbázisából töröl: az eszköznél továbbra is megmaradhat a hálózati kulcs,
   ezért utána gyári reset szükséges.
5. Újrapárosítás után ellenőrizzük a nevet, az IEEE-címet, az automation
   eszközrekordját és a helyiség-hozzárendelést. Azonos IEEE-cím esetén az
   automation a meglévő eszközt tudja folytatni; eltérő IEEE-cím új fizikai
   eszközt jelent.

A Zigbee2MQTT újraindítása nem szükséges minden újrapárosításhoz. Egyes
modellekhez lehet külön gyártó-/modellfüggő hibaelhárítás — például az
SNZB-02D eszközoldala hibásan beragadt jelentésnél külön eljárást ír le —,
ezért ilyen esetben mindig az adott modell aktuális oldalát kövessük.

## Stabilitási megjegyzések

- A routereket előbb telepítsük és párosítsuk, mint a végleges helyükre kerülő
  elemes végberendezéseket.
- Egy router tartós áthelyezése vagy kiesése után adjunk időt a meshnek, majd
  ellenőrizzük az érintett végberendezéseket valódi állapotváltozással.
- Egyes végberendezések nem vagy csak lassan választanak új szülőt. Emiatt a
  célzott újracsatlakoztatás hasznos lehet, de nem minden eszköz viselkedik
  azonosan.
- A Wi-Fi/Zigbee interferenciát csatornakiosztással és fizikai távolsággal
  együtt vizsgáljuk. A jelenlegi Zigbee-csatorna `25`; ezt egyedi szenzorhiba
  elhárításakor ne módosítsuk.
- Az availability-figyelés az aktív eszközöknél 10 perces, az alvó, elemes
  végberendezéseknél 2880 perces (48 órás) határt használ. Az utóbbiaknál ez
  nem aktív ping: az `offline` állapot az elmaradt Zigbee-jelentésekből
  következik. A Nous/Tuya nyitásérzékelők `max rep interval=65000` másodperces
  beállításához képest a 48 óra több mint két jelentési ciklusnyi tartalék.

## Források

- [Zigbee2MQTT – Allowing devices to join](https://www.zigbee2mqtt.io/guide/usage/pairing_devices.html)
- [Zigbee2MQTT – Zigbee network](https://www.zigbee2mqtt.io/advanced/zigbee/01_zigbee_network.html)
- [Zigbee2MQTT – FAQ](https://www.zigbee2mqtt.io/guide/faq/)
- [Zigbee2MQTT – MQTT topics and messages](https://www.zigbee2mqtt.io/guide/usage/mqtt_topics_and_messages.html)
