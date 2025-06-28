# Pulling bill info (summary, sponsors, etc)

## SC

The code is in sc_get_bill_info.py; it writes to sc_bills_info.json. 

### NOTE: url calls use session number (e.g. 126), json uses session name ('2025-26')

Set these parameters:

### set sessions here
sessions = [126, 125]
#### set current session here for updating
current_session = 126

## updating logic
update = True

It has an optional update mode; to use this when you have a live session and want to update for the latest, set update to True.
