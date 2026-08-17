from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any


def _stamp(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") + "Z" if value else None


def build_evidence(cursor, started_at: datetime, ended_at: datetime, observation: str | None) -> dict[str, Any]:
    cursor.execute(
        """SELECT d.id,d.name,d.source_system,r.name,z.name,sr.observed_at,sr.value
           FROM sensor_readings sr JOIN sensors s ON s.id=sr.sensor_id
           JOIN devices d ON d.id=s.device_id LEFT JOIN rooms r ON r.id=d.room_id
           LEFT JOIN zones z ON z.id=COALESCE(r.zone_id,d.zone_id)
           WHERE s.sensor_type='temperature' AND sr.value IS NOT NULL
             AND sr.quality IN ('good','valid') AND sr.observed_at BETWEEN ? AND ?
           ORDER BY d.id,sr.observed_at""", (started_at, ended_at)
    )
    series: dict[int, dict[str, Any]] = {}
    for device_id,name,source,room,zone,moment,value in cursor.fetchall():
        item=series.setdefault(int(device_id),{"device":name,"source":source,"room":room,"zone":zone,"points":[]})
        item["points"].append((moment,float(value)))
    sensors=[]; esp_drop_buckets: dict[datetime,list[dict[str,Any]]] = defaultdict(list)
    for item in series.values():
        points=item.pop("points"); values=[value for _,value in points]
        drops=[(points[i][1]-points[i-1][1],points[i-1][0],points[i][0]) for i in range(1,len(points))]
        sharpest=min(drops,key=lambda row:row[0]) if drops else None
        if item["source"] == "esp32":
            for change,from_at,to_at in drops:
                if change <= -0.1:
                    esp_drop_buckets[to_at.replace(second=0,microsecond=0)].append(
                        {"device":item["device"],"change_c":round(change,4),"from":_stamp(from_at),"to":_stamp(to_at)})
        sensors.append({**item,"sample_count":len(values),"first_c":round(values[0],4),"last_c":round(values[-1],4),
          "minimum_c":round(min(values),4),"maximum_c":round(max(values),4),"average_c":round(mean(values),4),
          "net_change_c":round(values[-1]-values[0],4),
          "sharpest_drop":None if sharpest is None else {"change_c":round(sharpest[0],4),"from":_stamp(sharpest[1]),"to":_stamp(sharpest[2])}})

    cursor.execute("""SELECT r.name,v.started_at,v.ended_at,v.started_outdoor_temperature_c,
      v.ended_outdoor_temperature_c FROM ventilation_events v JOIN rooms r ON r.id=v.room_id
      WHERE COALESCE(v.ended_at,'9999-12-31')>=? AND v.started_at<=? ORDER BY v.started_at,r.name""",(started_at,ended_at))
    ventilation=[{"room":r,"started_at":_stamp(s),"ended_at":_stamp(e),"start_outdoor_c":float(st) if st is not None else None,"end_outdoor_c":float(et) if et is not None else None} for r,s,e,st,et in cursor.fetchall()]
    cursor.execute("""SELECT d.name,e.started_at,e.ended_at,e.started_target_temperature_c,
      e.ended_target_temperature_c,e.started_fan_speed,e.ended_fan_speed,e.event_origin
      FROM climate_operation_events e JOIN devices d ON d.id=e.device_id
      WHERE COALESCE(e.ended_at,'9999-12-31')>=? AND e.started_at<=? ORDER BY e.started_at""",(started_at,ended_at))
    climate=[{"device":d,"started_at":_stamp(s),"ended_at":_stamp(e),
      "start_target_c":float(st) if st is not None else None,
      "end_target_c":float(et) if et is not None else None,
      "start_fan_speed":sf,"end_fan_speed":ef,"origin":origin}
      for d,s,e,st,et,sf,ef,origin in cursor.fetchall()]
    cursor.execute("""SELECT o.observed_at,o.temperature_c,s.display_name FROM outdoor_temperature_observations o
      JOIN outdoor_temperature_sources s ON s.id=o.source_id WHERE o.observed_at BETWEEN ? AND ? ORDER BY o.observed_at""",(started_at,ended_at))
    outdoor=[{"at":_stamp(at),"temperature_c":float(temp),"source":source} for at,temp,source in cursor.fetchall()]
    common_events=[{"minute_utc":_stamp(moment),"device_count":len(changes),"changes":changes,
      "mean_change_c":round(mean(x["change_c"] for x in changes),4)}
      for moment,changes in sorted(esp_drop_buckets.items()) if len(changes)>=3]
    outdoor_summary=None
    if outdoor:
        outdoor_summary={"sample_count":len(outdoor),"first_c":outdoor[0]["temperature_c"],
          "last_c":outdoor[-1]["temperature_c"],"minimum_c":min(x["temperature_c"] for x in outdoor),
          "maximum_c":max(x["temperature_c"] for x in outdoor),"source":outdoor[-1]["source"]}
    findings=[]
    for index,event in enumerate(common_events):
        findings.append({"statement":f"{event['device_count']} ESP32 egyazon mérési időpontban csökkent; az átlagos változás {event['mean_change_c']} °C.",
          "evidence":[f"common_esp32_drop_events[{index}]"]})
    active_vent=[x for x in ventilation if x["ended_at"] is None]
    if active_vent: findings.append({"statement":f"Az időablakban {len(active_vent)} helyiség szellőztetése aktív és lezáratlan volt.","evidence":["ventilation_events"]})
    findings.append({"statement":f"Az időablakkal átfedő naplózott klímaesemények száma {len(climate)}.","evidence":["climate_events"]})
    if outdoor_summary: findings.append({"statement":f"A szolgáltatói külső hőmérséklet {outdoor_summary['minimum_c']} és {outdoor_summary['maximum_c']} °C között volt.","evidence":["outdoor_summary"]})
    return {"schema_version":1,"timezone":"UTC","operator_observation_timezone":"Europe/Budapest",
      "window":{"started_at":_stamp(started_at),"ended_at":_stamp(ended_at)},
      "deterministic_findings":findings,
      "temperature_series":sensors,"ventilation_events":ventilation,"climate_events":climate,
      "outdoor_summary":outdoor_summary,"outdoor_observations":outdoor,
      "common_esp32_drop_events":common_events,
      "operator_observation":observation or None,
      "constraints":{"database_access":False,"device_control":False,"raw_measurements_preserved":True}}
