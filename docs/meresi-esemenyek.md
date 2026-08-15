# Mérési események

Az idősorok értelmezéséhez szükséges, kézzel megfigyelt környezeti események.
Ezek nem műszeres tények, hanem az elemzéshez felhasználható kezelői
megfigyelések.

## 2026. augusztus 14.

- **17:55–18:05 helyi idő, Dolgozó:** porszívózás történt a helyiségben. A
  hatása az ESP32 hőmérsékleti mérésein is látható. Az UI ezt 15:55–16:05
  időtartományként jelezte, vagyis ezen a kijelzésen kétórás UTC–helyi idő
  eltéréssel kell számolni. A tényleges 17:55–18:05 közötti tartományt a
  klímafutás és a szenzorok dinamikájának kiértékelésekor külső zavaró
  eseményként kell kezelni.

## 2026. augusztus 15.

- **09:27 helyi idő, esp32-kisnappali:** érzékelőkísérlet kezdődött. Az idősor
  ekkor jelentkező induló ugrását a kézi beavatkozás okozta; nem a helyiség
  tényleges hőmérséklet-változásaként és nem szenzorhibaként kell értelmezni. A
  DS18B20 ettől az időponttól egy szellőzőnyílásokkal ellátott műanyag
  dobozban van. A kísérlet utáni sorozatot az érzékelő megváltozott fizikai
  környezetének válaszreakciójaként kell elemezni.

- **Esti kontrollmérés, esp32-kisnappali:** a dobozolt DS18B20-szal a korábbi,
  50 perces dolgozószobai klímafutással azonos beállítású tesztet kell
  megismételni. Az indítás és leállítás pontos idejét a klímavezérlési napló
  rögzíti. Az elemzésben a kisnappali szenzor reakcióidejét, letörését,
  minimumát és visszamelegedését kell összevetni a változatlanul hagyott
  kontrollszenzorokkal és az előző napi futással. A pontos kezdési időt a teszt
  programozásakor kell rögzíteni.
