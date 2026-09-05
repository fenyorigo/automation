# Teendők

## Zigbee újraindítási megbízhatóság

- [ ] Kontrollált Sonoff/Tasmota Zigbee bridge-áramtalanítási próba. A teszt előtt
  a Zigbee2MQTT szabályosan leállítandó, a bridge visszatérése és a 8888/TCP
  port elérhetősége után indítandó újra. Ezután ellenőrizni kell, hogy a két
  dolgozói Nous/Tuya nyitásérzékelő párosítás nélkül küld-e új állapotot.
- [ ] Kivizsgálni, miért éri el a Zigbee2MQTT leállítása a systemd 90 másodperces
  időkorlátját.
- [ ] A klímavezérlés bevezetése előtt a túl régi nyitásérzékelő-állapotot
  ismeretlennek és automatikus vezérlést blokkoló állapotnak kell tekinteni.
