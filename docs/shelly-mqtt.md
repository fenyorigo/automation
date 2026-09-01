# Shelly H&T Gen3 helyi MQTT-integráció

## Adatút

```text
Shelly H&T Gen3 --Wi-Fi/MQTT--> Mosquitto --> automation-shelly-mqtt.service
                                                   |
                                                   +--> devices
                                                   +--> sensors
                                                   +--> sensor_readings
```

A Shelly Cloud ki van kapcsolva. Az eszközök közvetlenül a think260x helyi
Mosquitto brokerére publikálnak; az automation a `127.0.0.1:1883` címen
kapcsolódik hozzá.

## Topicok és szűrés

A collector az alábbi szabályos MQTT wildcardokra iratkozik fel:

```text
+/status/temperature:0
+/status/humidity:0
+/status/devicepower:0
+/online
```

A `+` teljes topicszintet helyettesít. A feliratkozás ezért más eszközök
üzeneteit is elérheti, de a collector kizárólag a
`shellyhtg3-<12 hexadecimális karakter>` alakú első topicszintet dolgozza fel.

Egy eszköz példaprefixe:

```text
shellyhtg3-48f6eebb92d4
```

## Mérési csatornák

Az egyes MQTT-üzeneteket nem várjuk össze. Minden érték önálló idősoros mérés:

| Payload mező | `sensor_type` | Egység |
|---|---|---|
| `tC` | `temperature` | `celsius` |
| `rh` | `humidity` | `percent` |
| `battery.percent` | `battery` | `percent` |
| `battery.V` | `battery_voltage` | `volt` |

A payload nem tartalmaz mérési időt, ezért az `observed_at` a brokerüzenet
automation általi fogadásának UTC-időpontja. A topic és az eredeti payload a
`sensor_readings.raw_payload` mezőben is megmarad.

Retained üzenetnél a topic és payload stabil SHA-256-alapú
`source_event_id`-t kap, így egy szolgáltatás-újraindítás nem hoz létre újabb
azonos sort. Élő üzenetnél az érkezési idő része az eseményazonosítónak, ezért
egy későbbi, változatlan értékű mérés is új idősoros pont lesz.

## Deep sleep és frissesség

A H&T Gen3 felébred, mér, szükség esetén publikál, majd visszaalszik. Emiatt az
`/online=false` normális állapot: nem hoz létre hibát és nem jelenti az eszköz
kiesését. A dashboard a legutóbbi tényleges mérés időpontját használja, és a
normál 7200 másodperces `wakeup_period` köré négylépcsős jelzést ad:

| Mérési kor | Szín | Bélyeg |
|---|---|---|
| 0–1:00 | zöld | Friss mérés |
| 1:01–2:00 | sárga | Alvó |
| 2:01–4:00 | narancs | Jelentés késik |
| 4:01 fölött | piros | Nincs friss mérés |

Az utolsó ismert érték mind a négy állapotban látható marad. A sárga a normál
deep-sleep ciklus része; a narancs legalább egy kimaradt jelentésre hívja fel a
figyelmet, és csak két kimaradt ciklus után lesz piros a kártya. A hőmérséklet
száma és mértékegysége is követi az állapot színét; friss, zöld állapotban az
alapértelmezett fekete szövegszín marad.

## Automatikus regisztráció és kézi előd

Az első felismert üzenet létrehozza a `devices` rekordot és az érintett
`sensors` csatornákat. Az eszközazonosság:

```text
source_system    = shelly_mqtt
source_device_id = teljes MQTT-prefix
source_puid      = a prefixben levő 12 hexadecimális karakter
```

A `shellyhtg3-48f6eebb92d4` a korábbi kézi `shelly-dolgozo` fizikai utódja.
Az első párosításkor átveszi annak nevét és helyiségét, új
`device_room_history` bejegyzést kap, a kézi device és szenzorai pedig
inaktívvá válnak. A régi méréseket nem mozgatjuk és nem töröljük.

A `shellyhtg3-48f6eebb5c50` ugyanilyen módon a kézi `shelly-nappali` fizikai
utódja, és annak nevét, valamint Nappali helyiség-hozzárendelését örökli.

## Fedora szolgáltatás

```bash
sudo install -o automation -g automation -m 0755 \
  app/shelly_mqtt_service.py /var/www/automation/app/shelly_mqtt_service.py
sudo install -o root -g root -m 0644 \
  deploy/systemd/automation-shelly-mqtt.service \
  /etc/systemd/system/automation-shelly-mqtt.service
sudo restorecon -R /var/www/automation/app
sudo restorecon /etc/systemd/system/automation-shelly-mqtt.service
sudo systemctl daemon-reload
sudo systemctl enable --now automation-shelly-mqtt.service
```

Ellenőrzés:

```bash
systemctl status automation-shelly-mqtt.service --no-pager -l
journalctl -u automation-shelly-mqtt.service -f
mosquitto_sub -h 127.0.0.1 -v \
  -t 'shellyhtg3-48f6eebb92d4/status/#' \
  -t 'shellyhtg3-48f6eebb92d4/online'
```

Adatbázis-ellenőrzés:

```sql
SELECT d.name,s.sensor_type,s.unit,sr.value,sr.observed_at,sr.source_event_id
FROM sensor_readings sr
JOIN sensors s ON s.id=sr.sensor_id
JOIN devices d ON d.id=s.device_id
WHERE d.source_system='shelly_mqtt'
  AND d.source_device_id='shellyhtg3-48f6eebb92d4'
ORDER BY sr.observed_at DESC,s.sensor_type
LIMIT 20;
```

Az új Shelly szolgáltatást a Fedora teljes mentőscriptje is állapotmegőrzéssel
kezeli: ha a mentés előtt futott, a MariaDB visszaindítása után ismét elindul.
