# get bill info: number, title, summary, sponsors, actions 
# will save as json given variable number of sponsors, actions
# bill pages have title and sponsors (with embedded member_codes)
# under class="bill-list-item"
# first span then get member_code from href and name from text

# need to differentiate between:
#    sponsors and co-sponsors
#    House and Senate bills (different url structure?)
#    per legislative services: 
#       senate bills are 1-2999
#       House bills are 3000+
#    (true for every session, not just 126)



import requests
import seleniumbase as sb
from bs4 import BeautifulSoup
import json
import time
import logging
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

all_bills_info = {}
bill_numbers = [i for i in range(1, 6000)] 
sessions = [126, 125]
chambers = ['S', 'H']
bill_numbers_by_chamber = {
    'S': [i for i in range(1, 3000)],
    'H': [i for i in range(3000, 6000)]
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
                
                bill_info['session'] = session
                bill_info['bill_number'] = bill_number
                
                try:
                    bill_list = soup.find_all('div', class_='bill-list-item')
                except Exception as e:
                    error_msg = f"Error finding bill list items in session {session} bill number {bill_number}: {e}"
                    print(error_msg)
                    logging.error(error_msg)
                    #TODO continue #add this when looping

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

                all_bills_info[f"{session}-{bill_number}"] = bill_info

                stob = 1

driver.quit()


# Save the bill info to a JSON file
with open('va_bills_info.json', 'w') as f:
    json.dump(all_bills_info, f, indent=4)
logging.info("Bill information saved to va_bills_info.json")
logging.info(f"Processed {len(all_bills_info)} bills from sessions {sessions}")
print(f"Processed {len(all_bills_info)} bills from sessions {sessions}")
            

