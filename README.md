# Robotail for Home Assistant

An unofficial Home Assistant integration for Robotail/AIROBO smart
litter boxes, initially developed against the UCAT C32.

## Features

- Guided setup using a normal Robotail email or phone account
- Automatic discovery of litter boxes attached to the account
- Last confirmed litter-box visit time, weight, and duration
- Usage count and waste-drawer fullness when reported by the device
- Cloud connectivity state
- A `robotail_cat_visit` Home Assistant event for new visits
- Last visiting cat, when Robotail associates the visit with a cat profile
- Adjustable automatic-clean delay (1–60 minutes)
- Automatic cleaning enable/disable switch

This integration uses Robotail's cloud API. The litter box must first be paired using the official Robotail app.

## Test installation

1. Copy `custom_components/robotail` into the `custom_components` directory in
   your Home Assistant configuration directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Robotail**.
5. Enter the same login details used by the Robotail app.

For a US phone account, enter the ten-digit national phone number, select
**Phone number**, use `+1` as the calling code, and `US` as the country code.
The integration automatically constructs the full account number exactly as
the official app does.

For a genuinely fresh test, do not copy any database or token files. The setup
flow performs its own login and device discovery.

Before signing in, pair/sync the box with your main Robotail account. Create a
secondary account in the official app, share the box from the main account,
then sign into the app as the secondary account and accept the invitation.
Use that secondary account for Home Assistant. The setup wizard shows these
instructions before requesting login details. Keep the phone app on the main
account to avoid competing sessions with the integration account.

Connectivity indicates the device's cloud-reported online status from its
messaging profile, not Home Assistant's internet connection. If Robotail does
not supply that status, the value remains unknown.

The supplied Robotail logo is bundled locally for Home Assistant 2026.3 and newer.

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
  cat_id: "..."
  cat_name: "..."
```

Robotail is polled once per minute. Existing history does not fire events when
Home Assistant starts.

## Status and limitations

Version 0.1.5 adds a pre-login account-sharing guide, bundled Robotail branding,
the device messaging-profile online-status lookup, and automatic re-login after
an authentication rejection during reads. Re-login is attempted once per failed
read; settings commands are never automatically replayed. This is password
re-login, not a verified refresh-token API. Usage count and drawer fullness still
depend on values supplied by Robotail and their missing values remain under
investigation. The integration does not yet use the device's local IP address.

Version 0.1.4 adds cat identity and automatic-clean settings. Cat identity is
unknown when Robotail has not assigned a profile; it is not guessed from weight.
Setting changes are checked against the cloud configuration after writing.
Manual cleaning, live cat-inside state, and live cleaning status are not yet exposed.

Version 0.1.3 uses a Robotail client header accepted by the cloud service;
the previous `HomeAssistant-Robotail` header caused HTTP 403 before credentials
were checked. Version 0.1.2 corrects the login HTTP method to `PUT` and the account-type
values to phone `0` and email `1`. Setup errors now show the failing step and
API code, including structured errors returned with HTTP 400. After updating
through HACS, restart Home Assistant before retrying setup.

- Unofficial and not affiliated with Robotail or AIROBO.
- Manual cleaning commands are not exposed.
- Cloud API changes may break the integration.
- Email/phone login and regional behavior need broader real-world testing.
- Credentials remain in the Home Assistant config entry so the integration can
  sign in again when its short-lived token expires. Tokens are kept in memory
  and are never written to logs.

Please redact email addresses, phone numbers, device serial numbers, tokens,
and event records when sharing diagnostics.
