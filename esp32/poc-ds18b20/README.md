# ESP32 DS18B20 gateway

## Build and upload

```sh
~/.platformio/penv/bin/pio run
~/.platformio/penv/bin/pio run --target upload --upload-port /dev/cu.usbserial-0001
~/.platformio/penv/bin/pio device monitor --port /dev/cu.usbserial-0001 --baud 115200
```

## USB Wi-Fi configuration

The firmware prints the station MAC address and starts the setup wizard when no
saved configuration exists. The wizard always asks for the SSID and password,
then offers three IP modes:

1. DHCP
2. DHCP with a server-side reservation
3. Static IP configuration

For a DHCP reservation, the firmware shows the MAC address and the entered
network values and waits until the user confirms that the reservation has been
configured on the DHCP server. The ESP32 itself still operates as a DHCP client
in this mode and checks the assigned address against the expected address.

Available commands outside the wizard:

- `status`: show the MAC address, connection state, masked configuration and
  current network details.
- `configure`: start the wizard while keeping the saved configuration until a
  new configuration is confirmed.
- `forget`: erase the saved Wi-Fi configuration and start the wizard.
- `cancel`: leave the active wizard.

The password is never printed back by the firmware. Configuration is stored in
the ESP32 NVS partition. If a connection attempt times out, retry delays are
1, 1, 2, 3 and then 5 minutes. Sensor measurements continue during setup and
connection retries.
