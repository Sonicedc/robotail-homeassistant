# Robotail for Home Assistant

An unofficial, read-only Home Assistant integration for Robotail/AIROBO smart
litter boxes, initially developed against the UCAT C32.

## Features

- Guided setup using a normal Robotail email or phone account
- Automatic discovery of litter boxes attached to the account
- Last confirmed litter-box visit time, weight, and duration
- Usage count and waste-drawer fullness when reported by the device
- Cloud connectivity state
- A `robotail_cat_visit` Home Assistant event for new visits

This integration uses Robotail's cloud API. It does not require a jailbroken
phone, an extracted app database, a device IP address, or an energy-monitoring
plug. The litter box must first be paired using the official Robotail app.

## Test installation

1. Copy `custom_components/robotail` into the `custom_components` directory in
   your Home Assistant configuration directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Robotail**.
5. Enter the same login details used by the Robotail app.

For a genuinely fresh test, do not copy any database or token files. The setup
flow performs its own login and device discovery.

## HACS development installation

Add `https://github.com/Sonicedc/robotail-homeassistant` to HACS as a custom
repository of type **Integration**. The repository includes the required
`hacs.json`, manifest version, and `custom_components` layout.

## Automation event

When polling finds a new confirmed visit, the integration fires:

```yaml
event_type: robotail_cat_visit
event_data:
  serial_number: "..."
  record_id: "..."
  weight: 4.1
  duration: 34
  event_time: "..."
```

Robotail is polled once per minute. Existing history does not fire events when
Home Assistant starts.

## Status and limitations

- Unofficial and not affiliated with Robotail or AIROBO.
- Read-only by design; cleaning commands are not exposed.
- Cloud API changes may break the integration.
- Email/phone login and regional behavior need broader real-world testing.
- Credentials remain in the Home Assistant config entry so the integration can
  sign in again when its short-lived token expires. Tokens are kept in memory
  and are never written to logs.

Please redact email addresses, phone numbers, device serial numbers, tokens,
and event records when sharing diagnostics.
