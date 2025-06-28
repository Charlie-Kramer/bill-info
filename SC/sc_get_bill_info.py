# get bill info: number, title, summary, sponsors, actions 
# will save as json given variable number of sponsors, actions
# bill pages have title and sponsors (with embedded member_codes)
# under class="bill-list-item"
# first span then get member_code from href and name from text

# NOTE: url calls use session number (e.g. 126), json uses session name ('2025-26')

# need to differentiate between:
#    sponsors and co-sponsors
#    House and Senate bills (different url structure?)
#    per legislative services: 
#       senate bills are 1-2999 (max)
#       House bills are 3000+
#    (true for every session, not just 126)


import requests
import seleniumbase as sb
from bs4 import BeautifulSoup
import json
import time
import logging
import re

def get_last_bill_numbers(session):
    """
    read the last .json file to get the last processed bill number for each chamber for the given session, return a dictionary
    with the last bill number for each chamber.
    
    """
    last_bills = {}

    #load the json file if it exists
    with open('SC/sc_bills_info.json', 'r') as f:
        all_bills_info = json.load(f)
    
    session_data = [value for key, value in all_bills_info.items() if value['session'] == session]
    
    for chamber in ['S', 'H']:
        chamber_bills = [x for x in session_data if x['chamber'] == chamber]
        last_bills[chamber] = max([int(bill['bill_number']) for bill in chamber_bills])

    return last_bills


last_bills = get_last_bill_numbers('2025-26')
stob = 1
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

session_dict = {
    126 : "2025-26",
    125 : "2023-24",
    124 : '2021-22',
    123 : "2019-20"  
}

all_bills_info = {}
chambers = ['S', 'H']

# set sessions here
sessions = [126, 125]
# set current session here for updating
current_session = session_dict[126]

## updating logic
update = False

if update:
    if len(sessions) != 1 and sessions[0] != current_session:
        error_msg = f"Set to update = True but Sessions list {sessions} does not match current session {current_session}. Please update the sessions list."
        print(error_msg)
        logging.error(error_msg)
        raise ValueError(error_msg)
    else:
        # get the last bill numbers for each chamber for the current session
        last_bills = get_last_bill_numbers(current_session)
        start_S = last_bills['S'] + 1
        start_H = last_bills['H'] + 1

        logging.info(f"Starting Senate bills from {start_S} and House bills from {start_H}")
        print(f"Starting Senate bills from {start_S} and House bills from {start_H}")
else: # not updating
    start_S = 1
    start_H = 3000
    logging.info(f"Not updating, sessions = {sessions}, starting Senate bills from 1 and House bills from 3000")

bill_numbers_by_chamber = {
    'S': [i for i in range(start_S, 3000)],
    'H': [i for i in range(start_H, 6000)]
}

driver = sb.get_driver(browser='chrome', headless=True)
driver.set_page_load_timeout(60)


for session in sessions:

    for chamber in chambers:

        if chamber == 'S':
            bill_numbers = bill_numbers_by_chamber['S']
        elif chamber == 'H':
            bill_numbers = bill_numbers_by_chamber['H']
        else:
            error_msg = f"Unknown chamber: {chamber}"
            print(error_msg)
            logging.error(error_msg)
            continue
        # Filter bill numbers for the current session and chamber

        logging.info(f"Processing session {session}, chamber {chamber} with {len(bill_numbers)} bills")
        print(f"Processing session {session}, chamber {chamber} with {len(bill_numbers)} bills")
        
        for bill_number in bill_numbers:

            url = f"https://www.scstatehouse.gov/billsearch.php?billnumbers={bill_number}&session={session}&summary=B&headerfooter=1"

            bill_info = {}

            r = requests.get(url)
            time.sleep(1)
            if "INVALID BILL NUMBER" in r.text:
                print("Invalid bill number:", bill_number)
                logging.error(f"Invalid bill number: {bill_number}")
                break
            if r.status_code !=200:
                print("fail",bill_number, r.status_code)
                logging.error(f"Failed to retrieve bill {bill_number}: {r.status_code}")    
                continue
            else:
                print('success', bill_number, r.status_code)
                driver.get(url)
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                bill_info['session'] = session_dict[session]
                bill_info['bill_number'] = bill_number
                
                try:
                    bill_list = soup.find_all('div', class_='bill-list-item')
                except Exception as e:
                    error_msg = f"Error finding bill list items in session {session} bill number {bill_number}: {e}"
                    print(error_msg)
                    logging.error(error_msg)

                # get the header text: has the basic bill info
                bill_header = bill_list[0].find('span')
                bill_header_text = bill_header.text.strip()

                bill_info['chamber'] = chamber
                bill_info['bill_header'] = bill_header_text
                
                # get the sponsor names (only last name available) and member_codes (these match what I have in the 
                # json file for w-nominate)

                bill_sponsors_list = bill_header.find_all('a')

                member_codes = [re.search(r'code=(\d+)' , a['href']).group(1) for a in bill_sponsors_list if 'code=' in a['href']]
                member_names = [a.text.strip() for a in bill_sponsors_list if 'code=' in a['href']]
                
                bill_info['sponsors'] = [{'member_code': code, 'name': name} for code, name in zip(member_codes, member_names)]
                

                # get the summary label and description text 
                
                summary_tag = bill_list[0].find('b', string=re.compile(r'Summary:'))
                summary_tag_siblings = [sib for sib in summary_tag.next_siblings]

                summary_title_text = summary_tag_siblings[0].text.strip() if summary_tag_siblings else None

                bill_info['title summary'] = summary_title_text

                bill_abstract = summary_tag_siblings[2].text.strip() if len(summary_tag_siblings) > 2 else None

                bill_info['abstract'] = bill_abstract

                # get the table of actions

                actions_table = soup.find('table')

                actions_table_rows = actions_table.find_all('tr')

                action_rows = []
                for row in actions_table_rows:
                    cols = [col.get_text(strip=True) for col in row.find_all(['td', 'th'])]
                    if cols:
                        action_rows.append(cols)

                bill_info['actions'] = action_rows

                all_bills_info[f"{session_dict[session]}-{bill_number}"] = bill_info

                stob = 1

driver.quit()


# Save the bill info to a JSON file
if update:
    try:
        with open('SC/sc_bills_info.json', 'r') as f:
            existing_bills_info = json.load(f)
        all_bills_info.update(existing_bills_info)
    except FileNotFoundError:
        logging.warning("No existing bill info found, creating new file.")
else:
    with open('sc_bills_info.json', 'w') as f:
        json.dump(all_bills_info, f, indent=4)

logging.info("Bill information saved to sc_bills_info.json")
logging.info(f"Processed {len(all_bills_info)} bills from sessions {sessions}")
print(f"Processed {len(all_bills_info)} bills from sessions {sessions}")
        

