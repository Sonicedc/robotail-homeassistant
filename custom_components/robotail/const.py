"""Constants for the Robotail integration."""

from datetime import timedelta

DOMAIN = "robotail"
PLATFORMS = ["binary_sensor", "sensor"]

API_HOST = "https://apis.airrobo-home.com"
# Robotail Android app's shared production client identity. This is not a
# user's credential; it is required to obtain the regional configuration and
# sign the same requests made by the official client.
APP_ID = "970010094"
APP_KEY = "xzy321gvms7mqq32idf8yb9nxbdc9gs5"

CONF_ACCOUNT_TYPE = "account_type"
CONF_AREA_CODE = "area_code"
CONF_COUNTRY_CODE = "country_code"
CONF_DEVICE_ID = "device_id"
ACCOUNT_TYPE_EMAIL = "email"
ACCOUNT_TYPE_PHONE = "phone"
# The server accepts 0 and 1, and rejects 2. PHONE precedes EMAIL in the SDK.
ACCOUNT_TYPE_VALUES = {ACCOUNT_TYPE_PHONE: 0, ACCOUNT_TYPE_EMAIL: 1}

DEFAULT_AREA_CODE = "+1"
DEFAULT_COUNTRY_CODE = "US"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=1)

ATTR_RECORD_ID = "record_id"
ATTR_EVENT_TYPE = "event_type"
ATTR_CONFIRMED = "confirmed"
ATTR_CAT_ID = "cat_id"
ATTR_CAT_NAME = "cat_name"

EVENT_CAT_VISIT = f"{DOMAIN}_cat_visit"
