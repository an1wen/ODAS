from instagrapi import Client
import requests
import datetime
from bs4 import BeautifulSoup
import json
import time
import random
from pathlib import Path
from collections import deque

from selenium import webdriver
from selenium.webdriver.common.by import By  
from selenium.webdriver.support.wait import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from fake_useragent import UserAgent

# Create Chromeoptions instance 
options = webdriver.ChromeOptions() 
ua = UserAgent()
# Adding argument to disable the AutomationControlled flag 
options.add_argument("--disable-blink-features")
options.add_argument("--disable-blink-features=AutomationControlled") 
options.add_argument("--incognito")
# Exclude the collection of enable-automation switches 
options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
# Turn-off userAutomationExtension 
options.add_experimental_option("useAutomationExtension", False) 
options.add_argument("start-maximized")
# Setting the driver path and requesting a page 
# driver = webdriver.Chrome(options=options) 
# # Changing the property of the navigator value for webdriver to undefined 
# driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") 

print('All modules loaded')
print()

# /-----------------------------------------------------------
# Logging in
# \-----------------------------------------------------------

# Define your account ID and password from a separate file
try:
    from my_id import ACCOUNT_USERNAME,ACCOUNT_PASSWORD
    print(f"Successfully loaded credentials of {ACCOUNT_USERNAME}")
except:
    print("Warning: could not load credentials from module.")
    print("Do you want to input them manually? If yes, type your username, if not, leave blanck.")
    print("Enter your username:")
    ACCOUNT_USERNAME = input()
    print("Enter your password:")
    ACCOUNT_PASSWORD = input()
    print()

if ACCOUNT_PASSWORD == None:
    print("No username provided, exiting.")
    exit()

# Login to your account and let the fun begin
cl = Client()
cl.login(ACCOUNT_USERNAME, ACCOUNT_PASSWORD)
print("Successfully logged-in.")
print()



# /-----------------------------------------------------------
# Configuration. Should be moved to separate file, eventually.
# \-----------------------------------------------------------

my_info = {}
my_info["username"] = ACCOUNT_USERNAME

REDO_WHITELIST = True
USE_CHECKLIST = True

REDO_PROCESSED = False


FNAME_WHITELIST = Path('data/whitelist.txt')
FNAME_PROCESSED = Path('data/processed.jsonl')
FNAME_CHECKLIST = Path('data/checklist.txt')

# suspect_zero_name = 'waifumiiaa'
suspect_zero_name = 'sarameikasai' # huge account, following a bunch of creators, good starting point
num_processed_max = 5000

# List of keywords to look for in biography
keywords_bio   = ['exclusive','content','shop','vip']
# List of keywords to look for in the links in the bio
keywords_url = ['getallmylinks','beacons','linktr.ee','onlylinks',
                'snipfeed','msha.ke','link.me','allmylinks','moxylink','superlink',
                'browseallmylinks']
# List of keywords to look for on the web pages of links
# keywords_web  = ['onlyfans','fansly','ko-fi','exclusive','shop','patreon','snapchat',
#                  'vip','msha.ke','cash.app','wishlist']
keywords_web  = ['onlyfans','fansly','porn','nude','🌶️']

# List of keywords to avoid when checking links
skip_url = ['youtu.be','youtube','spotify','instagram','twitter',
            'facebook','tiktok','twitch','soundcloud','amazon',
            'gmail.com','https://t.me','x.com','apple.com','cameo.com',
            'gofund.me']

keywords_all = list(set(keywords_bio) | set(keywords_url) | set(keywords_web))

# Makes a whitelist 
# The whitelist contains all people I am following and people following me
# People in the whitelist will not be blocked, no matter what
def make_whitelist(my_info,fname_whitelist=FNAME_WHITELIST):
    my_user_name = my_info["username"]
    my_user_id = cl.user_id_from_username(my_user_name)
    my_info["user_id"] = my_user_id
    my_followers_full = cl.user_followers(user_id = my_user_id, amount = 0)
    my_following_full = cl.user_following(user_id = my_user_id, amount = 0)
    my_followers_ids = set(map(int, my_followers_full.keys()))
    my_following_ids = set(map(int, my_following_full.keys()))
    # This is your circle, i.e. your whitelist
    whitelist_ids = my_followers_ids | my_following_ids
    # Export whitelist to a file for future use
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    with open(fname_whitelist, 'w') as file:
        file.write(f"Last update: {timestamp}" + "\n")
        for user_id in whitelist_ids:
            file.write(f"{user_id}" + "\n")
    print(f"Whitelist saved to {fname_whitelist}")
    return whitelist_ids

# If whitelist already exists, just read it from file
def read_whitelist(fname_whitelist=FNAME_WHITELIST):
    # Read the file into a list of strings
    with open(fname_whitelist, 'r') as file:
        next(file)
        whitelist_ids = {int(line.strip()) for line in file}
    return whitelist_ids


# Read processed database
def read_processed(fname_processed=FNAME_PROCESSED):
    processed_data = {}
    processed_ids = set()
    # Create empty file if it does not exist
    fname_processed.parent.mkdir(parents=True, exist_ok=True)
    fname_processed.touch(exist_ok=True)
    with open(fname_processed, "r") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            user_id = int(entry["user_id"])
            processed_data[user_id] = entry
            processed_ids.add(user_id)
    return processed_data, processed_ids


# Append a newly processed account
def append_processed(entry, fname_processed=FNAME_PROCESSED):
    # Make sure user_id is stored as int
    entry["user_id"] = int(entry["user_id"])
    with open(fname_processed, "a") as file:
        json.dump(entry, file)
        file.write("\n")

def read_checklist(fname_checklist=FNAME_CHECKLIST):
    # Read the file into a list of strings
    with open(fname_checklist, 'r') as file:
        checklist_ids = {int(line.strip()) for line in file.readlines()}
    return checklist_ids

def write_checklist(checklist_ids,fname_checklist=FNAME_CHECKLIST):
    print(f"Writing new checklist to {fname_checklist}")
    with open(fname_checklist, 'w') as file:
        for user_id in checklist_ids:
            file.write(f"{user_id}" + "\n")





def inspect_url(url,suspect_name):
    print(f'{suspect_name}: trying opening {url}')
    if url == '' or url == ' ' or url == None:
        print(f'Could not open {url}, abort')
        return []
    for keyword in skip_url:
        if keyword in url:
            print(f'Link {url} is whitelisted, skipping')
            return []
    try:
        # Fetch the website content
        user_agent = ua.random
        options.add_argument(f'--user-agent={user_agent}')
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") 
        driver.get(url)
        sleep_time = random.randint(25, 45)/10
        time.sleep(sleep_time) 
        html = driver.page_source
        # Parse the website content with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        # Extract all the text from the website
        website_text = soup.get_text().lower()
        website_links = soup.find_all('a', href=True)
        link_text = ''
        for link in website_links:
            link_text+=link['href']
        # Check website text for keywords
        trigger_web = []
        for keyword in keywords_web:
            if keyword.lower() in website_text or keyword.lower() in link_text:
                trigger_web.append(keyword)
                print(f"{suspect_name}: found '{keyword}' in web")
                #return True
        # print(f"No keywords found in {url}")
        #return False
        return trigger_web
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch {url} for {suspect_name}")
        #return False
        return []


def suspect_inspect(suspect_info):
    # Get all suspect information
    suspect_id = suspect_info["user_id"]
    suspect_name = suspect_info["username"]
    try:
        suspect_info_full = cl.user_info(user_id = suspect_id).dict()
    except:
        print(f"Failed to get user info for {suspect_name}")
        suspect_info["error"] = True
        suspect_info["status"] = "Could not get info"
        return
    suspect_info["follower_count"] = suspect_info_full["follower_count"]
    suspect_info["following_count"] = suspect_info_full["following_count"]
    # First, check bio for keywords
    suspect_bio = suspect_info_full['biography']
    suspect_bio_lower = suspect_bio.lower()
    trigger_bio = []
    for keyword in keywords_all:
        if keyword.lower() in suspect_bio_lower:
            trigger_bio.append(keyword)
            print(f"{suspect_name}: found '{keyword}' in bio")
    suspect_bio_links_full = suspect_info_full['bio_links']
    trigger_url = []
    trigger_web = []
    bio_links = []
    # Loop on all links available
    for bio_dict in suspect_bio_links_full:
        bio_link_url = bio_dict['url']
        bio_links.append(bio_link_url)
        # Second, check links for keywords
        for keyword in keywords_all:
            if keyword.lower() in bio_link_url:
                trigger_url.append(keyword)
                print(f"{suspect_name}: found '{keyword}' in url")
        # Third, check url for keywords
        try:
            trigger_web = inspect_url(bio_link_url,suspect_name)
        except:
            print(f"Failed to fetch {bio_link_url} for {suspect_name}")
            trigger_web = []
    triggers = [trigger_bio,trigger_url,trigger_web]
    return triggers,bio_links

# Append suspect info to the blacklist
def suspect_write(filename_processed, suspect_info, urls, matched_keywords):
    # Get the current date
    current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Create a dictionary for the current entry
    if suspect_info["error"]:
        entry = {
            "user_id": suspect_info["user_id"],
            "error": suspect_info["error"],
            "status": suspect_info["status"],
        }
    else:
        entry = {
            "user_id": suspect_info["user_id"],
            "username": suspect_info["username"],
            "error": suspect_info["error"],
            "followers_count": suspect_info["follower_count"],
            "following_count": suspect_info["following_count"],
            "num_added_checklist": suspect_info["num_added_checklist"],
            "date_checked": current_date,
            "links": urls,
            "matched_keywords": matched_keywords
        }
    # Append the entry to the file
    with open(filename_processed, 'a') as file:
        file.write(json.dumps(entry) + "\n")
    print(f"Wrote {suspect_info["user_id"]} to list of processed.")

# Read blacklist data
def suspect_read(filename_processed = FNAME_PROCESSED):
    data = []
    with open(filename_processed, 'r') as file:
        for line in file:
            entry = json.loads(line.strip())
            data.append(entry)
    return data

def process_account(suspect_info):
    suspect_id = suspect_info["user_id"]
    try:
        suspect_name = cl.username_from_user_id(suspect_id)
    except:
        print(f'Couldnt get user name of {suspect_id}, trying again')
        try:
            suspect_name = cl.username_from_user_id(suspect_id)
        except:
            print('Failed get name again, skip')
            suspect_info["error"] = True
            suspect_info["status"] = "Could not get username"
            return None, None, None
    suspect_info["username"] = suspect_name
    print(f"-"*60)
    print(f"Begin checking {suspect_name}")
    suspect_triggers, suspect_links = suspect_inspect(suspect_info)
    print("Inspection finished")
    print()
    if suspect_triggers == [[],[],[]]:
        suspect_following_ids = {}
    elif suspect_info["following_count"] > 200:
        suspect_following_ids = {}
    else:
        try:
            suspect_following_full = cl.user_following(user_id = suspect_id, amount = 0)
            suspect_following_ids = suspect_following_full.keys()
        except:
            print(f'Failed getting followings of {suspect_name}')
            suspect_following_ids = {}
    suspect_info["num_added_checklist"] = len(suspect_following_ids)
    suspect_write(FNAME_PROCESSED,suspect_info, suspect_links,suspect_triggers)
    return suspect_name, suspect_triggers, suspect_following_ids

# Where the fun begins!!!

# Initialize whitelist
if REDO_WHITELIST:
    whitelist_ids = make_whitelist(my_info)
    print('Whitelist IDs rebuilt from profile')
else:
    whitelist_ids = read_whitelist(FNAME_WHITELIST)
    print('Whitelist IDs imported')

# Load previously processed
if True:
    data = suspect_read(FNAME_PROCESSED)
    processed_ids = set()
    for user in data:
        processed_ids.add(user["user_id"])
    print('Processed IDs imported')

# Initialize checklist
# First, get followers of suspect zero
try:
    suspect_zero_id = int(cl.user_id_from_username(username = suspect_zero_name))
    suspect_zero_set = {suspect_zero_id}
except:
    print("Could get the ID of suspect zero.")

if USE_CHECKLIST == True:
    checklist_from_file = read_checklist(FNAME_CHECKLIST)

if not checklist_from_file and not suspect_zero_set:
    print("Checklist ID is empty, exiting.")
    exit()

checklist_ids = checklist_from_file | suspect_zero_set

# Queue
queue_ids = deque(checklist_ids)

# Fast lookup to avoid duplicates in queue
queued_ids = set(checklist_ids)

# Main loop
num_processed = 0
while queue_ids:

    # Get next suspect
    user_id = queue_ids.popleft()
    queued_ids.remove(user_id)

    print("=" * 60)
    print(f"Checking user_id = {user_id}")

    # Skip whitelist
    if user_id in whitelist_ids:

        print("SKIP : whitelist")
        continue

    # Skip already processed
    if not REDO_PROCESSED and (user_id in processed_ids):

        print("SKIP : already processed")
        continue

    # --------------------------------------------------
    # PROCESS ACCOUNT
    # --------------------------------------------------

    user_info = {}
    user_info["user_id"] = user_id
    user_info["error"] = False

    print("Fetching account info...")
    user_name, user_triggers, new_ids = process_account(user_info)
    error = user_info["error"]
    if error:
        print(f"User finished with error, status: {user_info["status"]}.")
        print(f"QUEUE SIZE : {len(queue_ids)}")
        num_processed += 1
        if num_processed==num_processed_max:
            break
        sleep_time = random.randint(2, 8)/10
        print(f'~~~sleeping for {sleep_time} seconds~~~')
        time.sleep(sleep_time)
        continue
    else:
        print("User finished processing without errors.")

    new_ids = set(map(int, new_ids))

    # --------------------------------------------------
    # ADD NEW DISCOVERED ACCOUNTS
    # --------------------------------------------------

    n_added = 0
    for new_id in new_ids:
        # Normalize
        new_id = int(new_id)
        # All filters in ONE place
        if new_id in whitelist_ids:
            continue
        if new_id in processed_ids:
            continue
        if new_id in queued_ids:
            continue
        # Add to queue
        queue_ids.append(new_id)
        queued_ids.add(new_id)
        n_added += 1

    print(f"DISCOVERED : {len(new_ids)}")
    print(f"ADDED      : {n_added}")
    print(f"QUEUE SIZE : {len(queue_ids)}")

    num_processed += 1
    if num_processed==num_processed_max:
        break

    sleep_time = random.randint(2, 8)/10
    print(f'~~~sleeping for {sleep_time} seconds~~~')
    time.sleep(sleep_time)


print(f'Finished checking {num_checks} suspects.')

write_checklist(queue_ids)